from odoo import models, fields, api, _


class MediaFace(models.Model):
    _inherit = 'media.face'

    transfer_history_count = fields.Integer(
        string='Transfer events',
        compute='_compute_transfer_history_count',
    )

    @api.depends('message_ids', 'message_ids.subtype_id')
    def _compute_transfer_history_count(self):
        subtype = self.env.ref(
            'media_finance.mt_media_face_booking_transfer', raise_if_not_found=False
        )
        if not subtype:
            for rec in self:
                rec.transfer_history_count = 0
            return
        Message = self.env['mail.message']
        for rec in self:
            rec.transfer_history_count = Message.search_count([
                ('model', '=', 'media.face'),
                ('res_id', '=', rec.id),
                ('subtype_id', '=', subtype.id),
            ])

    def action_view_transfer_history(self):
        self.ensure_one()
        subtype = self.env.ref(
            'media_finance.mt_media_face_booking_transfer', raise_if_not_found=False
        )
        list_view = self.env.ref('media_finance.view_mail_message_face_transfer_list')
        dom = [
            ('model', '=', 'media.face'),
            ('res_id', '=', self.id),
        ]
        if subtype:
            dom.append(('subtype_id', '=', subtype.id))
        return {
            'name': _('Transfer history'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.message',
            'view_mode': 'list,form',
            'views': [(list_view.id, 'list'), (False, 'form')],
            'domain': dom,
        }
