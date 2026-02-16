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
        # Find the canopy record linked to this site
        canopy = self.env['media.canopy'].search([('site_id', '=', self.site_id.id)], limit=1)
        if canopy:
            canopy.write({
                'status': self.new_status,
                'status_reason': self.reason
            })
            # Post a message to chatter on the canopy record (which will bubble up to site if followed)
            canopy.message_post(body=f"Status updated to {dict(self._fields['new_status'].selection).get(self.new_status)}: {self.reason}")
        else:
            # Fallback if no canopy found (should not happen if filtered correctly)
            self.site_id.message_post(body=f"Failed to update status: Linked Canopy record not found.")
