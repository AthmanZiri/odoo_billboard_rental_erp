from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MediaArtworkHistory(models.Model):
    _name = 'media.artwork.history'
    _description = 'Artwork History'
    _order = 'upload_date desc'

    face_id = fields.Many2one('media.face', string='Face', required=True, ondelete='cascade')
    site_id = fields.Many2one('media.site', string='Site', store=True)
    site_category = fields.Selection([
        ('billboard', 'Billboard'),
        ('canopy', 'Canopy'),
        ('digital', 'Digital Screen')
    ], string='Site Category', store=True)
    
    sale_order_line_id = fields.Many2one('sale.order.line', string='Contract Line', ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Client', store=True, required=True)
    
    lease_start_date = fields.Date(string='Lease Start Date')
    lease_end_date = fields.Date(string='Lease End Date')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('site_id') and not vals.get('face_id'):
                site = self.env['media.site'].browse(vals['site_id'])
                if site.site_category == 'canopy':
                    faces = self.env['media.face'].search([('site_id', '=', site.id)], limit=1)
                    if faces:
                        vals['face_id'] = faces[0].id
            
            # Ensure partner_id is set from sale_order_line_id if not explicitly provided
            if vals.get('sale_order_line_id') and not vals.get('partner_id'):
                sol = self.env['sale.order.line'].browse(vals['sale_order_line_id'])
                vals['partner_id'] = sol.order_id.partner_id.id
        
        records = super(MediaArtworkHistory, self).create(vals_list)
        
        # Force recompute of occupancy status on linked faces using Odoo's trigger
        for face in records.mapped('face_id'):
             face.modified(['occupancy_status', 'current_booking_start', 'current_booking_end', 'next_available_date'])
        
        # Sync to face if not already coming from face update
        if not self.env.context.get('skip_face_sync'):
            for record in records:
                if record.face_id and record.artwork_file:
                    record.face_id.with_context(skip_history_creation=True).write({
                        'default_artwork': record.artwork_file,
                        'face_image': record.artwork_file,
                    })
        return records

    def write(self, vals):
        res = super(MediaArtworkHistory, self).write(vals)
        if any(f in vals for f in ['lease_start_date', 'lease_end_date', 'face_id']):
            for face in self.mapped('face_id'):
                face.modified(['occupancy_status', 'current_booking_start', 'current_booking_end', 'next_available_date'])
        return res

    @api.onchange('site_id')
    def _onchange_site_id(self):
        if self.site_id:
            self.site_category = self.site_id.site_category
            # For canopies, automatically pick the face (usually there's only one)
            if self.site_category == 'canopy':
                faces = self.env['media.face'].search([('site_id', '=', self.site_id.id)], limit=1)
                if faces:
                    self.face_id = faces[0].id

    @api.onchange('face_id')
    def _onchange_face_id(self):
        if self.face_id:
            if not self.site_id:
                self.site_id = self.face_id.site_id
            self.site_category = self.face_id.site_id.site_category

    @api.onchange('sale_order_line_id')
    def _onchange_sale_order_line_id(self):
        if self.sale_order_line_id:
            self.partner_id = self.sale_order_line_id.order_id.partner_id
            self.lease_start_date = self.sale_order_line_id.start_date
            self.lease_end_date = self.sale_order_line_id.end_date
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and self.sale_order_line_id:
            if self.sale_order_line_id.order_id.partner_id != self.partner_id:
                # Clear sale order line if it doesn't match the selected partner
                self.sale_order_line_id = False
    
    artwork_file = fields.Image(string='Artwork', required=True)
    artwork_filename = fields.Char(string='Filename')
    
    upload_date = fields.Datetime(string='Upload Date', default=fields.Datetime.now, readonly=True)
    description = fields.Text(string='Description')
    uploaded_by = fields.Many2one('res.users', string='Uploaded By', default=lambda self: self.env.user, readonly=True)

    @api.constrains('sale_order_line_id')
    def _check_contract_validity(self):
        today = fields.Date.today()
        for record in self:
            if record.sale_order_line_id:
                if record.sale_order_line_id.end_date and record.sale_order_line_id.end_date < today:
                    raise ValidationError(_("You cannot update artwork for an expired contract (%s).") % record.sale_order_line_id.order_id.name)

    def name_get(self):
        result = []
        for record in self:
            name = f"Artwork on {record.upload_date.strftime('%Y-%m-%d %H:%M')}"
            result.append((record.id, name))
        return result
