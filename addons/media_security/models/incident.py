from odoo import models, fields, api

class MediaIncident(models.Model):
    _name = 'media.incident'
    _description = 'Site Incident Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    site_id = fields.Many2one('media.site', string='Site', required=True)
    watchman_id = fields.Many2one('media.watchman', string='Reported By', related='site_id.watchman_id', store=True)
    
    incident_type = fields.Selection([
        ('vandalism', 'Vandalism'),
        ('lighting_failure', 'Lighting Failure'),
        ('storm_damage', 'Storm Damage'),
        ('other', 'Other')
    ], string='Incident Type', required=True)
    
    description = fields.Text(string='Description')
    date_reported = fields.Datetime(string='Date Reported', default=fields.Datetime.now)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('reported', 'Reported'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved')
    ], string='Status', default='draft', tracking=True)

    def action_report(self):
        self.state = 'reported'

    def action_resolve(self):
        self.state = 'resolved'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('media.incident') or 'New'
        return super(MediaIncident, self).create(vals_list)
