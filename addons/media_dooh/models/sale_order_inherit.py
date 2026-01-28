from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    media_slot_id = fields.Many2one('media.dooh.slot', string='Digital Slot')
