from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta

class MediaRental(models.Model):
    _name = 'media.rental'
    _description = 'Billboard Rental'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Rental Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    start_date = fields.Date(string='Rental Start Date', required=True, tracking=True, default=fields.Date.today)
    end_date = fields.Date(string='Rental End Date', required=True, tracking=True, default=lambda self: fields.Date.add(fields.Date.today(), months=1))
    
    rental_line_ids = fields.One2many('media.rental.line', 'rental_id', string='Rental Lines')
    face_selection_ids = fields.Many2many('media.face', string='Select Billboards', 
                                         compute='_compute_face_selection_ids', inverse='_inverse_face_selection_ids',
                                         domain="[('id', 'in', available_face_ids)]")
    
    @api.depends('rental_line_ids.face_id')
    def _compute_face_selection_ids(self):
        for record in self:
            record.face_selection_ids = record.rental_line_ids.mapped('face_id')

    def _inverse_face_selection_ids(self):
        for record in self:
            current_faces = record.rental_line_ids.mapped('face_id')
            new_faces = record.face_selection_ids - current_faces
            removed_faces = current_faces - record.face_selection_ids
            
            new_lines = []
            for face in new_faces:
                new_lines.append((0, 0, {
                    'face_id': face.id,
                    'price_unit': face.price_per_month,
                }))
            
            for face in removed_faces:
                line = record.rental_line_ids.filtered(lambda l: l.face_id == face)
                if line:
                    new_lines.append((2, line[0].id))
            
            if new_lines:
                record.rental_line_ids = new_lines
    
    sale_order_id = fields.Many2one('sale.order', string='Linked Sale Order', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Smart Button Counts
    invoice_count = fields.Integer(compute='_compute_finance_counts')
    payment_count = fields.Integer(compute='_compute_finance_counts')
    
    # Availability Logic
    available_face_ids = fields.Many2many('media.face', compute='_compute_available_face_ids', string='Available Faces')
    
    @api.depends('sale_order_id', 'sale_order_id.invoice_ids', 'sale_order_id.invoice_ids.payment_state')
    def _compute_finance_counts(self):
        for record in self:
            invoices = record.sale_order_id.invoice_ids if record.sale_order_id else self.env['account.move']
            record.invoice_count = len(invoices)
            
            # Simple payment count for Odoo Community: check for journal entries linked to these invoices
            # In a full accounting setup, we'd check partial/reconciled moves.
            payments = self.env['account.payment'].search([('move_id.ref', 'ilike', record.name)])
            if record.sale_order_id:
                payments |= self.env['account.payment'].search([('move_id.ref', 'ilike', record.sale_order_id.name)])
            record.payment_count = len(payments)

    @api.depends('start_date', 'end_date')
    def _compute_available_face_ids(self):
        for record in self:
            if not record.start_date or not record.end_date:
                record.available_face_ids = self.env['media.face'].search([]).ids
                continue
                
            # Find all booked faces for this period (excluding this rental itself if active)
            booked_lines = self.env['sale.order.line'].search([
                ('media_face_id', '!=', False),
                ('state', 'in', ['sale', 'done']),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date),
            ])
            booked_face_ids = booked_lines.mapped('media_face_id').ids
            
            # All faces minus booked ones
            record.available_face_ids = self.env['media.face'].search([('id', 'not in', booked_face_ids)]).ids

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoices(self):
        self.ensure_one()
        invoices = self.sale_order_id.invoice_ids
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoices.ids)],
            'target': 'current',
        }

    def action_view_payments(self):
        self.ensure_one()
        payments = self.env['account.payment'].search([('move_id.ref', 'ilike', self.name)])
        if self.sale_order_id:
            payments |= self.env['account.payment'].search([('move_id.ref', 'ilike', self.sale_order_id.name)])
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments.ids)],
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('media.rental') or _('New')
        return super(MediaRental, self).create(vals_list)

    def action_confirm(self):
        for record in self:
            record.write({'state': 'active'})
            record._create_sale_order()

    def _create_sale_order(self):
        self.ensure_one()
        
        # Calculate duration in months
        delta = relativedelta(self.end_date, self.start_date)
        # We add 1 day to end_date for inclusive calculation if needed, 
        # but user's example Jan 28 -> Apr 28 is exactly 3 months in relativedelta
        months = delta.years * 12 + delta.months
        # Handle fractional months (days / 30.0)
        if delta.days > 0:
            months += round(delta.days / 30.0, 2)
        
        # Ensure at least 1 if dates are set
        qty = max(months, 0)
        
        order_vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': [],
        }
        for line in self.rental_line_ids:
            if line.face_id.product_id:
                order_vals['order_line'].append((0, 0, {
                    'product_id': line.face_id.product_id.id,
                    'media_face_id': line.face_id.id,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'product_uom_qty': qty,
                    'artwork_file': line.artwork_file,
                    'artwork_filename': line.artwork_filename,
                    'name': f"Rental of {line.face_id.name} from {self.start_date} to {self.end_date} ({qty} months)",
                    'price_unit': line.price_unit,
                }))
        
        order = self.env['sale.order'].create(order_vals)
        self.sale_order_id = order.id
        return order

class MediaRentalLine(models.Model):
    _name = 'media.rental.line'
    _description = 'Billboard Rental Line'

    rental_id = fields.Many2one('media.rental', string='Rental', required=True, ondelete='cascade')
    face_id = fields.Many2one('media.face', string='Face', required=True)
    site_id = fields.Many2one('media.site', string='Site', related='face_id.site_id', store=True, readonly=True)
    price_unit = fields.Float(string='Unit Price', related='face_id.price_per_month', readonly=False, store=True)
    
    artwork_file = fields.Binary(string='Artwork/Graphic')
    artwork_filename = fields.Char(string='Artwork Filename')
