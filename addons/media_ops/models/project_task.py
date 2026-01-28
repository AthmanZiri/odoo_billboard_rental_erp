from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    media_face_id = fields.Many2one('media.face', string='Media Face')
    site_id = fields.Many2one('media.site', related='media_face_id.site_id', store=True)
    
    # Artwork tracking
    artwork_status = fields.Selection([
        ('pending', 'Pending Receipt'),
        ('received', 'Received'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected')
    ], string='Artwork Status', default='pending')
    
    artwork_file = fields.Binary(string='Artwork File')
    artwork_filename = fields.Char(string='Artwork Filename')
    
    # Installation / Flighting
    installation_date = fields.Date(string='Installation Date')
    pop_photo = fields.Binary(string='PoP Photo (Proof of Performance)')
    pop_upload_date = fields.Datetime(string='PoP Upload Date')
    
    # Site Access
    watchman_id = fields.Many2one('media.watchman', related='site_id.watchman_id', string='Site Watchman')
    watchman_phone = fields.Char(related='site_id.watchman_id.phone_number', string='Watchman Phone')

    def action_mark_installed(self):
        self.installation_date = fields.Date.today()
        # Trigger notification to client could be added here
