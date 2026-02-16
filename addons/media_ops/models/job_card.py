from odoo import models, fields, api, _

class MediaJobCard(models.Model):
    _name = 'media.job.card'
    _description = 'Job Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Job Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    job_type_id = fields.Many2one('media.job.type', string='Job Type', required=True)
    
    maintenance_team_id = fields.Many2one('media.maintenance.team', string='Assigned Team', tracking=True)
    
    site_id = fields.Many2one('media.site', string='Site', required=True)
    media_face_id = fields.Many2one('media.face', string='Face', domain="[('site_id', '=', site_id)]")
    
    date = fields.Date(string='Date', default=fields.Date.today)
    
    notes = fields.Text(string='Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

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
        self.write({'state': 'completed'})
