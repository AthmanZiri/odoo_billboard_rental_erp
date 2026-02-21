from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lease_start_date = fields.Date(string='Lease Start Date')
    lease_end_date = fields.Date(string='Lease End Date')

    @api.onchange('lease_start_date', 'lease_end_date')
    def _onchange_lease_dates(self):
        for order in self:
            for line in order.order_line:
                if order.lease_start_date:
                    line.start_date = order.lease_start_date
                if order.lease_end_date:
                    line.end_date = order.lease_end_date

    def _prepare_invoice(self):
        vals = super(SaleOrder, self)._prepare_invoice()
        vals.update({
            'lease_start_date': self.lease_start_date,
            'lease_end_date': self.lease_end_date,
        })
        return vals

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')
    media_digital_screen_id = fields.Many2one('media.digital.screen', string='Digital Screen')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    
    artwork_file = fields.Image(string='Artwork/Graphic', max_width=1920, max_height=1920)
    artwork_filename = fields.Char(string='Artwork Filename')
    
    @api.constrains('media_face_id', 'media_digital_screen_id', 'start_date', 'end_date', 'state')
    def _check_availability(self):
        for line in self:
            if not line.start_date or not line.end_date:
                continue
            
            # Check for overlapping bookings for static faces
            if line.media_face_id and line.media_face_id.face_type != 'digital':
                domain = [
                    ('id', '!=', line.id),
                    ('media_face_id', '=', line.media_face_id.id),
                    ('state', 'in', ['sale', 'done']),
                    ('start_date', '<=', line.end_date),
                    ('end_date', '>=', line.start_date),
                ]
                overlapping = self.search_count(domain)
                if overlapping:
                    raise ValidationError(_('The face %s is already booked for the selected period.') % line.media_face_id.name)

            # Check for overlapping bookings for digital screens is handled by the slot logic or SOV rules.
            # But the constraint signature must include media_digital_screen_id if we want logic for it in future.

    @api.onchange('media_face_id')
    def _onchange_media_face_id(self):
        if self.media_face_id:
            if self.media_face_id.product_id:
                self.product_id = self.media_face_id.product_id
            
            # Set price based on pricing type
            if self.media_face_id.pricing_type == 'fixed':
                self.price_unit = self.media_face_id.price_per_month
            elif self.media_face_id.pricing_type == 'daily':
                self.price_unit = self.media_face_id.price_per_day
            
            # Default dates from header
            if self.order_id.lease_start_date:
                self.start_date = self.order_id.lease_start_date
            if self.order_id.lease_end_date:
                self.end_date = self.order_id.lease_end_date

    @api.onchange('media_digital_screen_id')
    def _onchange_media_digital_screen_id(self):
        if self.media_digital_screen_id:
            screen = self.media_digital_screen_id
            if screen.product_id:
                self.product_id = screen.product_id
            
            # Set price based on pricing type
            # For digital screens, we usually sell per slot or fixed
            if screen.pricing_type == 'fixed':
                self.price_unit = screen.price_per_month
            elif screen.pricing_type == 'slot_monthly':
                self.price_unit = screen.price_slot_monthly
            
            # Default dates from header
            if self.order_id.lease_start_date:
                self.start_date = self.order_id.lease_start_date
            if self.order_id.lease_end_date:
                self.end_date = self.order_id.lease_end_date

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.media_face_id:
            res.update({
                'media_face_id': self.media_face_id.id,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'artwork_file': self.artwork_file,
                'artwork_filename': self.artwork_filename,
            })
        return res
    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        if 'artwork_file' in vals and vals['artwork_file']:
            for line in self:
                if line.media_face_id:
                    self.env['media.artwork.history'].create({
                        'face_id': line.media_face_id.id,
                        'sale_order_line_id': line.id,
                        'artwork_file': vals['artwork_file'],
                        'description': _('Updated artwork for contract %s') % line.order_id.name,
                    })
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        for line in lines:
            if line.artwork_file and line.media_face_id:
                self.env['media.artwork.history'].create({
                    'face_id': line.media_face_id.id,
                    'sale_order_line_id': line.id,
                    'artwork_file': line.artwork_file,
                    'description': _('Initial artwork for contract %s') % line.order_id.name,
                })
        return lines
