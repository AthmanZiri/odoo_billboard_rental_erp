from odoo import models, api, fields

class MediaExpiryMixin(models.AbstractModel):
    _name = 'media.expiry.mixin'
    _description = 'Media Expiry Notification Mixin'

    def _get_notification_days(self):
        return self.env.company.expiry_notification_days if self.env.company.expiry_notification_days else 5

    def _trigger_expiry_notification(self, asset_type, asset_name, end_date, user_id, asset_record):
        # Create Mail Activity for Push Notification
        if user_id:
            summary = "Asset Expiring Soon: %s" % asset_name
            note = "The %s %s is set to expire on %s." % (asset_type, asset_name, end_date)
            asset_record.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today(),
                summary=summary,
                note=note,
                user_id=user_id.id
            )
        
        # Send Email via Template
        template_id = self.env.ref('media_expiry_notifications.asset_expiry_notification_template', raise_if_not_found=False)
        if template_id and user_id and user_id.email:
            ctx = {
                'ctx_asset_type': asset_type,
                'ctx_asset_name': asset_name,
                'ctx_end_date': end_date,
            }
            # send_mail on user_id Instead of asset_record
            template_id.with_context(**ctx).send_mail(user_id.id, force_send=False)
