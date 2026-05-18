from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    expiry_notification_days = fields.Integer(
        string='Expiry Notification Days',
        default=5,
        help="Number of days in advance to notify about asset lease/booking expiration."
    )
