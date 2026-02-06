from odoo import models, fields, api

class CanopyStatusWizard(models.TransientModel):
    _name = 'canopy.status.wizard'
    _description = 'Update Canopy Status'

    site_id = fields.Many2one('media.site', string='Canopy', required=True, domain=[('site_category', '=', 'canopy')])
    new_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('damaged', 'Damaged'),
        ('withdrawn', 'Withdrawn')
    ], string='New Status', required=True)
    reason = fields.Text(string='Reason', required=True)

    def action_update_status(self):
        self.ensure_one()
        self.site_id.write({
            'canopy_status': self.new_status,
            'canopy_status_reason': self.reason
        })
        # Post a message to chatter
        self.site_id.message_post(body=f"Status updated to {dict(self._fields['new_status'].selection).get(self.new_status)}: {self.reason}")
