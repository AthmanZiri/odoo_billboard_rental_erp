from odoo import models, fields

class MediaWatchman(models.Model):
    _name = 'media.watchman'
    _description = 'Media Watchman'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Watchman Name', required=True, tracking=True)
    identity_number = fields.Char(string='Identity Number')
    phone_number = fields.Char(string='Phone Number')
    employment_type = fields.Selection([
        ('direct', 'Direct'),
        ('third_party', 'Third-Party Agency')
    ], string='Employment Type', default='direct')
    agency_name = fields.Char(string='Agency Name')
    
    # Financials
    salary = fields.Float(string='Monthly Salary', help="For direct employees")
    agency_cost = fields.Float(string='Monthly Agency Cost', help="For third-party contracts")
    
    site_ids = fields.One2many('media.site', 'watchman_id', string='Assigned Sites')
    
    active = fields.Boolean(default=True)
