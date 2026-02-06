from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')

class MediaFace(models.Model):
    _inherit = 'media.face'

    invoice_line_ids = fields.One2many('account.move.line', 'media_face_id', string='Invoice Lines')
