from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    media_slot_id = fields.Many2one('media.dooh.slot', string='Digital Slot')

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.media_slot_id:
            res['media_slot_id'] = self.media_slot_id.id
        return res
