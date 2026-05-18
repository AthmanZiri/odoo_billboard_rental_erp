# -*- coding: utf-8 -*-
"""Shared inventory-only booking helpers (transfer, swap)."""
import base64

from odoo import fields, models

TRANSPARENT_1PX_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)
ARTWORK_PLACEHOLDER = base64.b64encode(TRANSPARENT_1PX_PNG)


class MediaBookingInventoryMixin(models.AbstractModel):
    _name = 'media.booking.inventory.mixin'
    _description = 'Media booking inventory helpers'

    def _sol_overlaps_period(self, line, period_start, period_end):
        s, e = line.get_media_lease_effective_dates()
        if not s or not e:
            return False
        return s < period_end and e > period_start

    def _history_overlaps_period(self, history, period_start, period_end):
        if not history.lease_start_date or not history.lease_end_date:
            return False
        return (
            history.lease_start_date < period_end
            and history.lease_end_date > period_start
        )

    def _face_confirmed_lines_overlapping(self, face, period_start, period_end, exclude_line=None):
        lines = face.lease_line_ids.filtered(
            lambda l: l.state in ('sale', 'done')
            and l.id not in face.transferred_out_sol_ids.ids
        )
        if exclude_line:
            lines = lines.filtered(lambda l: l.id != exclude_line.id)
        return lines.filtered(
            lambda l: self._sol_overlaps_period(l, period_start, period_end)
        )

    def _face_history_overlapping(self, face, period_start, period_end, exclude_history_ids=None):
        exclude_history_ids = exclude_history_ids or []
        histories = face.artwork_history_ids.filtered(
            lambda h: h.id not in face.transferred_out_history_ids.ids
            and h.id not in exclude_history_ids
        )
        return histories.filtered(
            lambda h: self._history_overlaps_period(h, period_start, period_end)
        )

    def _vacate_face_for_period(self, face, period_start, period_end, extra_sol_ids=None, extra_history_ids=None):
        """Mark overlapping confirmed bookings on *face* as transferred out."""
        extra_sol_ids = extra_sol_ids or []
        extra_history_ids = extra_history_ids or []
        sols = self._face_confirmed_lines_overlapping(face, period_start, period_end)
        sols |= face.lease_line_ids.filtered(lambda l: l.id in extra_sol_ids)
        histories = self._face_history_overlapping(face, period_start, period_end)
        histories |= face.artwork_history_ids.filtered(lambda h: h.id in extra_history_ids)
        vals = {}
        if sols:
            vals['transferred_out_sol_ids'] = [(4, sol.id) for sol in sols]
        if histories:
            vals['transferred_out_history_ids'] = [(4, h.id) for h in histories]
        if vals:
            face.sudo().write(vals)

    def _recompute_face_booking_state(self, faces):
        """Refresh stored occupancy / lease fields after inventory moves."""
        faces = faces.exists()
        if not faces:
            return
        faces.invalidate_recordset([
            'occupancy_status',
            'current_booking_start',
            'current_booking_end',
            'current_partner_id',
            'latest_lease_start_date',
            'latest_lease_end_date',
            'next_available_date',
            'is_soon_available',
            'is_available_in_7_days',
            'is_available_in_14_days',
            'is_available_in_2_days',
            'is_expired',
            'is_reserved',
            'lease_summary',
        ])
        faces._compute_occupancy_status()
        faces._compute_current_booking_dates()
        faces._compute_latest_lease_dates()
        faces._compute_next_available_date()
        faces._compute_status_flags()
        faces._compute_lease_summary()

    def _create_inventory_history_segments(
        self,
        target_face,
        partner,
        segments,
        description,
        sale_order_line=None,
    ):
        History = self.env['media.artwork.history'].with_context(skip_face_sync=True).sudo()
        for seg_start, seg_end in segments:
            vals = {
                'face_id': target_face.id,
                'partner_id': partner.id if partner else False,
                'lease_start_date': seg_start,
                'lease_end_date': seg_end,
                'artwork_file': ARTWORK_PLACEHOLDER,
                'description': description,
            }
            if sale_order_line:
                vals['sale_order_line_id'] = sale_order_line.id
            History.create(vals)
