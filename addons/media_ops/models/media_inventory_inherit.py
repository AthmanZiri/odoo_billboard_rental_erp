from odoo import models, fields

class MediaSite(models.Model):
    _inherit = 'media.site'

    job_card_ids = fields.One2many('media.job.card', 'site_id', string='Job Cards')
    job_card_count = fields.Integer(compute='_compute_job_card_count')

    def _compute_job_card_count(self):
        for site in self:
            site.job_card_count = len(site.job_card_ids)

    def action_view_job_cards(self):
        self.ensure_one()
        return {
            'name': 'Job Cards',
            'type': 'ir.actions.act_window',
            'res_model': 'media.job.card',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id},
        }

class MediaFace(models.Model):
    _inherit = 'media.face'

    job_card_ids = fields.One2many('media.job.card', 'media_face_id', string='Job Cards')
    job_card_count = fields.Integer(compute='_compute_job_card_count')

    def _compute_job_card_count(self):
        for face in self:
            face.job_card_count = len(face.job_card_ids)

    def action_view_job_cards(self):
        self.ensure_one()
        return {
            'name': 'Job Cards',
            'type': 'ir.actions.act_window',
            'res_model': 'media.job.card',
            'view_mode': 'list,form',
            'domain': [('media_face_id', '=', self.id)],
            'context': {'default_media_face_id': self.id, 'default_site_id': self.site_id.id},
        }


class MediaCanopy(models.Model):
    _inherit = 'media.canopy'

    # Delegate to the site_id's job cards
    job_card_ids = fields.One2many(related='site_id.job_card_ids', string='Job Cards', readonly=True)
    job_card_count = fields.Integer(related='site_id.job_card_count', string='Job Card Count', readonly=True)

    def action_view_job_cards(self):
        self.ensure_one()
        return self.site_id.action_view_job_cards()
