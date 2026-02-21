from odoo import models, fields, api, _

class MediaJobCard(models.Model):
    _name = 'media.job.card'
    _description = 'Job Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Job Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    job_type_id = fields.Many2one('media.job.type', string='Job Type', required=True)
    
    maintenance_team_id = fields.Many2one('media.maintenance.team', string='Assigned Team', tracking=True)
    
    site_id = fields.Many2one('media.site', string='Site')
    canopy_id = fields.Many2one('media.canopy', string='Canopy')
    media_face_id = fields.Many2one('media.face', string='Face/Canopy', domain="[('site_id', '=', site_id)]")
    site_category = fields.Selection([
        ('billboard', 'Billboard'),
        ('canopy', 'Canopy'),
        ('digital', 'Digital Screen')
    ], string='Site Category')

    old_canopy_photo = fields.Image(string='Old Canopy Photo', readonly=True)
    new_canopy_photo = fields.Image(string='New Canopy Photo')
    
    old_measurement_image_1 = fields.Image(string='Old Measurement 1', readonly=True)
    new_measurement_image_1 = fields.Image(string='New Measurement 1')
    
    old_measurement_image_2 = fields.Image(string='Old Measurement 2', readonly=True)
    new_measurement_image_2 = fields.Image(string='New Measurement 2')
    
    old_measurement_image_3 = fields.Image(string='Old Measurement 3', readonly=True)
    new_measurement_image_3 = fields.Image(string='New Measurement 3')
    
    old_measurement_image_4 = fields.Image(string='Old Measurement 4', readonly=True)
    new_measurement_image_4 = fields.Image(string='New Measurement 4')
    
    damaged_photo = fields.Image(string='Damaged Canopy Photo')
    
    date = fields.Date(string='Date', default=fields.Date.today)
    
    notes = fields.Text(string='Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.onchange('canopy_id')
    def _onchange_canopy_id(self):
        if self.canopy_id:
            self.site_id = self.canopy_id.site_id
            self.site_category = 'canopy'
            
            # Auto-select the face for the underlying site record
            faces = self.env['media.face'].search([('site_id', '=', self.canopy_id.site_id.id)], limit=1)
            if faces:
                self.media_face_id = faces[0].id
                self.old_canopy_photo = faces[0].face_image
            
            # Snapshot all current measurements into 'old' fields
            self.old_measurement_image_1 = self.canopy_id.measurement_image_1
            self.old_measurement_image_2 = self.canopy_id.measurement_image_2
            self.old_measurement_image_3 = self.canopy_id.measurement_image_3
            self.old_measurement_image_4 = self.canopy_id.measurement_image_4

    @api.onchange('site_id')
    def _onchange_site_id_auto_face(self):
        if self.site_id and self.site_category != 'canopy':
            faces = self.env['media.face'].search([('site_id', '=', self.site_id.id)], limit=1)
            if faces:
                self.media_face_id = faces[0].id
                # Only snapshot if it's potentially a canopy but coming through site_id (rare)
                if self.site_id.site_category == 'canopy':
                    self.old_canopy_photo = faces[0].face_image

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('media.job.card') or _('New')
        return super(MediaJobCard, self).create(vals_list)

    def action_assign(self):
        self.write({'state': 'assigned'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.ensure_one()
        if self.site_category == 'canopy':
            ctx = dict(self.env.context, from_job_card=True)
            
            # 1. Update the Face record
            if self.new_canopy_photo and self.media_face_id:
                self.media_face_id.with_context(ctx).write({
                    'face_image': self.new_canopy_photo
                })
            
            # 2. Update the Canopy record
            canopy = self.canopy_id or self.env['media.canopy'].search([('site_id', '=', self.site_id.id)], limit=1)
            if canopy:
                vals = {}
                if self.new_canopy_photo:
                    vals['canopy_image'] = self.new_canopy_photo
                
                # Sync new measurement images to Canopy
                if self.new_measurement_image_1: vals['measurement_image_1'] = self.new_measurement_image_1
                if self.new_measurement_image_2: vals['measurement_image_2'] = self.new_measurement_image_2
                if self.new_measurement_image_3: vals['measurement_image_3'] = self.new_measurement_image_3
                if self.new_measurement_image_4: vals['measurement_image_4'] = self.new_measurement_image_4
                
                if vals:
                    canopy.with_context(ctx).write(vals)

        self.write({'state': 'completed'})
