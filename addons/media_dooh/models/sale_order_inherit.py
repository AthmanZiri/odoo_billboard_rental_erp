from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    media_slot_id = fields.Many2one('media.dooh.slot', string='Digital Slot', domain="[('digital_screen_id', '=', media_digital_screen_id)]")
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Customer', store=True)

    @api.constrains('media_slot_id', 'start_date', 'end_date', 'state')
    def _check_digital_slot_availability(self):
        for line in self:
            if not line.media_slot_id or not line.start_date or not line.end_date:
                continue
            
            domain = [
                ('id', '!=', line.id),
                ('media_slot_id', '=', line.media_slot_id.id),
                ('state', 'in', ['sale', 'done']),
                ('start_date', '<=', line.end_date),
                ('end_date', '>=', line.start_date),
            ]
            overlapping = self.search_count(domain)
            if overlapping:
                raise ValidationError(_('The digital slot %s is already booked for the selected period.') % line.media_slot_id.name)

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.media_slot_id:
            res['media_slot_id'] = self.media_slot_id.id
        return res
