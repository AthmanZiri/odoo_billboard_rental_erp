from odoo import models, fields, api

class MediaPermitHistory(models.Model):
    _name = 'media.permit.history'
    _description = 'Media Permit History'
    _order = 'expiry_date desc'

    site_id = fields.Many2one('media.site', string='Billboard', required=True, ondelete='cascade')
    permit_number = fields.Char(string='Permit Number', required=True)
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True)
    permit_file = fields.Binary(string='Permit Document')
    permit_filename = fields.Char(string='Filename')
    
    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='active', compute='_compute_status', store=True)

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.today()
        for record in self:
            if record.expiry_date and record.expiry_date < today:
                record.status = 'expired'
            else:
                record.status = 'active'
