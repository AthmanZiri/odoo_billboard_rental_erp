from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')
    media_digital_screen_id = fields.Many2one('media.digital.screen', string='Digital Screen')
    canopy_id = fields.Many2one('media.canopy', string='Canopy')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    artwork_file = fields.Image(string='Artwork/Graphic', max_width=1920, max_height=1920)
    artwork_filename = fields.Char(string='Artwork Filename')
    move_payment_state = fields.Selection(related='move_id.payment_state', string='Payment Status')

class MediaFace(models.Model):
    _inherit = 'media.face'

    invoice_line_ids = fields.One2many('account.move.line', 'media_face_id', string='Invoice Lines')
