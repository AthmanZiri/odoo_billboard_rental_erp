from odoo import models, fields

class MediaSite(models.Model):
    _inherit = 'media.site'

    watchman_id = fields.Many2one('media.watchman', string='Assigned Watchman')
    watchman_phone = fields.Char(related='watchman_id.phone_number', string='Watchman Phone', readonly=True)
