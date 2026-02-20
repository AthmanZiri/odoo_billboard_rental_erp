from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    lease_start_date = fields.Date(string='Lease Start Date')
    lease_end_date = fields.Date(string='Lease End Date')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    media_face_id = fields.Many2one('media.face', string='Media Face')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    artwork_file = fields.Image(string='Artwork/Graphic', max_width=1920, max_height=1920)
    artwork_filename = fields.Char(string='Artwork Filename')
    move_payment_state = fields.Selection(related='move_id.payment_state', string='Payment Status')

class MediaFace(models.Model):
    _inherit = 'media.face'

    invoice_line_ids = fields.One2many('account.move.line', 'media_face_id', string='Invoice Lines')
