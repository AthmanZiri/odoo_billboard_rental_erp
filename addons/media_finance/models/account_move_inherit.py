from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')
