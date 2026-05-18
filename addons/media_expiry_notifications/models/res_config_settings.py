from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expiry_notification_days = fields.Integer(
        related='company_id.expiry_notification_days',
        string='Expiry Notification Days',
        readonly=False,
    )
