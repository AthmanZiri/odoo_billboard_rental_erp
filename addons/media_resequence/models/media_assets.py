from odoo import models, fields

class MediaSite(models.Model):
    _inherit = 'media.site'

    sequence = fields.Integer(string='Sequence', default=10, help="Gives the sequence order when displaying a list of assets.")

    _order = 'sequence, name, id'
