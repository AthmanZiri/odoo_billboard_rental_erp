from odoo import models, fields

class MediaMaintenanceTeam(models.Model):
    _name = 'media.maintenance.team'
    _description = 'Maintenance Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Team Name', required=True, tracking=True)
    leader_id = fields.Many2one('res.users', string='Team Leader', tracking=True)
    member_ids = fields.Many2many('res.partner', string='Team Members', 
                                 help="Partners/Employees who are part of this team.")
    active = fields.Boolean(default=True)
    
    notes = fields.Text(string='Notes')
