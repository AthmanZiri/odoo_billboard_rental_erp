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
        ('canopy', 'Canopy')
    ], string='Site Category', store=True)
    
    sale_order_line_id = fields.Many2one('sale.order.line', string='Contract Line', ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Client', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('site_id') and not vals.get('face_id'):
                site = self.env['media.site'].browse(vals['site_id'])
                if site.site_category == 'canopy':
                    faces = self.env['media.face'].search([('site_id', '=', site.id)], limit=1)
                    if faces:
                        vals['face_id'] = faces[0].id
        return super(MediaArtworkHistory, self).create(vals_list)

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
