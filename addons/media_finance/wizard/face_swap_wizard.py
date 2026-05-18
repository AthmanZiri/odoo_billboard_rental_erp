# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MediaFaceSwap(models.TransientModel):
    _name = 'media.face.swap'
    _description = 'Swap billboard face bookings (inventory only)'
    _inherit = ['media.booking.inventory.mixin']

    face_a_id = fields.Many2one('media.face', string='Face A', required=True)
    face_b_id = fields.Many2one('media.face', string='Face B', required=True)
    start_date = fields.Date(string='Swap Period Start', required=True)
    end_date = fields.Date(string='Swap Period End', required=True)
    notes = fields.Text(string='Notes')
    preview = fields.Html(string='Preview', compute='_compute_preview', sanitize=False)

    @api.depends('face_a_id', 'face_b_id', 'start_date', 'end_date')
    def _compute_preview(self):
        transfer_tool = self.env['media.booking.transfer'].new({})
        for rec in self:
            if not (rec.face_a_id and rec.face_b_id and rec.start_date and rec.end_date):
                rec.preview = ''
                continue
            if rec.start_date > rec.end_date:
                rec.preview = '<div class="alert alert-danger">Start must be before end.</div>'
                continue
            segs_a_on_b = transfer_tool._effective_transfer_segments(
                rec.face_b_id, rec.start_date, rec.end_date
            )
            segs_b_on_a = transfer_tool._effective_transfer_segments(
                rec.face_a_id, rec.start_date, rec.end_date
            )
            rec.preview = _(
                "<p>Inventory-only swap for <b>%(s)s</b> → <b>%(e)s</b>.</p>"
                "<p>Commitments on <b>%(a)s</b> move to <b>%(b)s</b> (%(na)s segment(s)); "
                "commitments on <b>%(bname)s</b> move to <b>%(aname)s</b> (%(nb)s segment(s)).</p>"
                "<p>Sale order lines stay on original orders for invoicing.</p>"
            ) % {
                's': rec.start_date,
                'e': rec.end_date,
                'a': rec.face_a_id.display_name,
                'b': rec.face_b_id.display_name,
                'aname': rec.face_a_id.display_name,
                'bname': rec.face_b_id.display_name,
                'na': len(segs_a_on_b),
                'nb': len(segs_b_on_a),
            }

    def _booking_commitments_on_face(self, face, period_start, period_end):
        """Return list of dicts describing overlapping inventory commitments."""
        commitments = []
        for line in self._face_confirmed_lines_overlapping(face, period_start, period_end):
            s, e = line.get_media_lease_effective_dates()
            seg_start = max(s, period_start)
            seg_end = min(e, period_end)
            commitments.append({
                'partner': line.order_id.partner_id,
                'segments': [(seg_start, seg_end)],
                'description': _("SWAP from %s (Sale Order %s)") % (
                    face.display_name, line.order_id.name,
                ),
                'sale_order_line': line,
            })
        for hist in self._face_history_overlapping(face, period_start, period_end):
            seg_start = max(hist.lease_start_date, period_start)
            seg_end = min(hist.lease_end_date, period_end)
            commitments.append({
                'partner': hist.partner_id,
                'segments': [(seg_start, seg_end)],
                'description': _("SWAP from %s (manual booking)") % face.display_name,
                'sale_order_line': hist.sale_order_line_id or False,
            })
        return commitments

    def action_swap(self):
        self.ensure_one()
        face_a = self.face_a_id
        face_b = self.face_b_id
        if face_a == face_b:
            raise ValidationError(_("Select two different faces."))
        if self.start_date > self.end_date:
            raise ValidationError(_("Start date must be before end date."))

        transfer_tool = self.env['media.booking.transfer'].new({})
        commitments_a = self._booking_commitments_on_face(face_a, self.start_date, self.end_date)
        commitments_b = self._booking_commitments_on_face(face_b, self.start_date, self.end_date)

        if not commitments_a and not commitments_b:
            raise ValidationError(_("No bookings overlap the selected period on either face."))

        # Vacate both faces for the swap window.
        self._vacate_face_for_period(face_a, self.start_date, self.end_date)
        self._vacate_face_for_period(face_b, self.start_date, self.end_date)

        def place_on_target(target_face, source_face, commitments):
            for item in commitments:
                for seg_start, seg_end in item['segments']:
                    free = transfer_tool._effective_transfer_segments(
                        target_face, seg_start, seg_end
                    )
                    if not free:
                        raise ValidationError(_(
                            "Cannot place booking from “%(src)s” on “%(tgt)s” for %(s)s → %(e)s: "
                            "target is not free."
                        ) % {
                            'src': source_face.display_name,
                            'tgt': target_face.display_name,
                            's': seg_start,
                            'e': seg_end,
                        })
                    desc = item['description']
                    if self.notes:
                        desc += "\n" + self.notes
                    sol = item.get('sale_order_line')
                    self._create_inventory_history_segments(
                        target_face,
                        item['partner'],
                        free,
                        desc,
                        sale_order_line=sol if sol and sol._name == 'sale.order.line' else None,
                    )

        place_on_target(face_b, face_a, commitments_a)
        place_on_target(face_a, face_b, commitments_b)

        st = self.env.ref(
            'media_finance.mt_media_face_booking_transfer', raise_if_not_found=False
        )
        mp_kw = {'subtype_id': st.id} if st else {}
        msg = _(
            "<b>Face swap</b> (%(s)s → %(e)s)<br/>"
            "Inventory commitments exchanged between %(a)s and %(b)s."
        ) % {
            's': self.start_date,
            'e': self.end_date,
            'a': face_a.display_name,
            'b': face_b.display_name,
        }
        face_a.message_post(body=msg, **mp_kw)
        face_b.message_post(body=msg, **mp_kw)

        self._recompute_face_booking_state(face_a | face_b)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Face swap recorded (inventory only)."),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
