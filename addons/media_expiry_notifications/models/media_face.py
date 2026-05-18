from odoo import models, api, fields
from dateutil.relativedelta import relativedelta

class MediaFace(models.Model):
    _name = 'media.face'
    _inherit = ['media.face', 'media.expiry.mixin']

    @api.model
    def _cron_notify_expiring_faces(self):
        days = self._get_notification_days()
        target_date = fields.Date.today() + relativedelta(days=days)
        today = fields.Date.today()

        # Check all faces that currently have 'booked' occupancy status
        faces = self.search([('occupancy_status', '=', 'booked')])
        for face in faces:
            # 1. Check sale order lines
            active_line = face.lease_line_ids.filtered(
                lambda l: l.state in ['sale', 'done'] 
                and l.start_date and l.end_date 
                and l.start_date <= today <= l.end_date
            ).sorted(key=lambda l: l.end_date, reverse=True)
            
            # 2. Check artwork history
            active_history = face.artwork_history_ids.filtered(
                lambda h: h.lease_start_date and h.lease_end_date 
                and h.lease_start_date <= today <= h.lease_end_date
            ).sorted(key=lambda h: h.lease_end_date, reverse=True)

            end_date = False
            user_id = False

            if active_line:
                end_date = active_line[0].end_date
                user_id = active_line[0].order_id.user_id
            elif active_history:
                end_date = active_history[0].lease_end_date
                user_id = active_history[0].create_uid

            if end_date == target_date:
                if not user_id:
                    user_id = self.env.user
                
                self._trigger_expiry_notification(
                    asset_type='Billboard Face',
                    asset_name=face.display_name,
                    end_date=end_date,
                    user_id=user_id,
                    asset_record=face
                )
