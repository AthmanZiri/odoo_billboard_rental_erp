from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    media_slot_id = fields.Many2one('media.dooh.slot', string='Digital Slot')
