from odoo import models, api, fields
from dateutil.relativedelta import relativedelta

class MediaDoohSlot(models.Model):
    _name = 'media.dooh.slot'
    _inherit = ['media.dooh.slot', 'media.expiry.mixin']

    @api.model
    def _cron_notify_expiring_slots(self):
        """ Override the placeholder existing cron or create a new robust one """
        days = self._get_notification_days()
        target_date = fields.Date.today() + relativedelta(days=days)
        today = fields.Date.today()

        slots = self.search([('state', '=', 'booked')])
        for slot in slots:
            active_line = slot.sale_line_ids.filtered(
                lambda l: l.state in ['sale', 'done'] 
                and l.start_date and l.end_date 
                and l.start_date <= today <= l.end_date
            ).sorted(key=lambda l: l.end_date, reverse=True)

            if active_line:
                end_date = active_line[0].end_date
                user_id = active_line[0].order_id.user_id

                if end_date == target_date:
                    if not user_id:
                        user_id = self.env.user
                    
                    self._trigger_expiry_notification(
                        asset_type='Digital Slot',
                        asset_name=slot.display_name,
                        end_date=end_date,
                        user_id=user_id,
                        asset_record=slot
                    )
