from odoo import models, fields

class MediaSite(models.Model):
    _inherit = 'media.site'

    job_card_ids = fields.One2many('media.job.card', 'site_id', string='Job Cards')

class MediaFace(models.Model):
    _inherit = 'media.face'

    job_card_ids = fields.One2many('media.job.card', 'media_face_id', string='Job Cards')
