from odoo import models, fields, api

class MediaDoohContentVersion(models.Model):
    _name = 'media.dooh.content.version'
    _description = 'DOOH Content Version'
    _order = 'create_date desc'

    slot_id = fields.Many2one('media.dooh.slot', string='Slot', required=True, ondelete='cascade')
    name = fields.Char(string='Version Name', required=True)
    content_file = fields.Binary(string='Creative File', required=True)
    content_filename = fields.Char(string='Creative Filename')
    content_type = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video')
    ], string='Content Type', default='image')
    
    is_active = fields.Boolean(string='Active', default=False)
    notes = fields.Text(string='Notes')
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super(MediaDoohContentVersion, self).create(vals_list)
        for record in records:
            if record.is_active:
                record._activate_version()
        return records

    def _activate_version(self):
        self.ensure_one()
        # Deactivate other versions for this slot
        self.slot_id.version_ids.filtered(lambda v: v.id != self.id).write({'is_active': False})
        # Sync to main slot fields
        self.slot_id.write({
            'content_file': self.content_file,
            'content_filename': self.content_filename,
            'content_type': self.content_type
        })

    def action_activate(self):
        self._activate_version()
        self.is_active = True
