from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import html_escape


class MediaBookingTransfer(models.TransientModel):
    _name = 'media.booking.transfer'
    _description = 'Transfer Billboard Face Booking'
    _inherit = ['media.booking.inventory.mixin']

    transfer_type = fields.Selection([
        ('sale_order', 'Via Sale Order (Existing Contract)'),
        ('no_sale_order', 'Without Sale Order (Face-to-Face Commitment)'),
    ], string='Transfer Type', required=True, default='sale_order')

    # ── Mode A: Via Sale Order ────────────────────────────────────────────────
    source_line_id = fields.Many2one(
        'sale.order.line',
        string='Existing Booking (Sale Order Line)',
        domain="[('media_face_id', '!=', False), ('state', 'in', ['sale', 'done'])]",
        help="Select the confirmed sale order line that references the face being vacated.",
    )
    source_face_info = fields.Char(
        string='Current Face / Dates',
        compute='_compute_source_face_info',
    )
    target_face_id = fields.Many2one(
        'media.face',
        string='Transfer To Face',
        help="The billboard face the client is moving to.",
    )

    # ── Mode B: Without Sale Order ────────────────────────────────────────────
    source_face_id = fields.Many2one(
        'media.face',
        string='Face Being Vacated',
        help="The face the client is leaving.",
    )
    client_id = fields.Many2one('res.partner', string='Client', help="Client making the face-to-face commitment.")
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    notes = fields.Text(string='Notes / Reason for Move')

    # ── Shared ────────────────────────────────────────────────────────────────
    target_face_id_b = fields.Many2one(
        'media.face',
        string='Transfer To Face',
        help="The billboard face the client is moving to (no sale order mode).",
    )
    transfer_window_preview = fields.Html(
        string='Transfer Window',
        compute='_compute_transfer_window_preview',
        sanitize=False,
    )

    @api.depends('source_line_id', 'source_line_id.start_date', 'source_line_id.end_date')
    def _compute_source_face_info(self):
        for rec in self:
            if rec.source_line_id:
                sol = rec.source_line_id
                face = sol.media_face_id
                win_s, win_e = rec._get_lease_window_for_sale_line(sol)
                if win_s and win_e:
                    date_part = "%s → %s" % (win_s, win_e)
                    if not (sol.start_date and sol.end_date):
                        date_part += _(" (dates from linked booking / artwork log; line dates were empty)")
                else:
                    date_part = _(
                        "No lease period — set Start and End on the line or on the booking log for this line"
                    )
                rec.source_face_info = (
                    "%s  |  %s  |  SO: %s  |  Client: %s"
                ) % (
                    face.display_name,
                    date_part,
                    sol.order_id.name,
                    sol.order_id.partner_id.name,
                )
            else:
                rec.source_face_info = ''

    @api.onchange('source_face_id')
    def _onchange_source_face_id(self):
        """Auto-populate client and dates based on the current active booking of the face."""
        if self.source_face_id:
            today = fields.Date.today()
            face = self.source_face_id

            # Priority 1: Find active confirmed Sale Order Line
            active_sol = self.env['sale.order.line'].search([
                ('media_face_id', '=', face.id),
                ('state', 'in', ['sale', 'done']),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
                ('id', 'not in', face.transferred_out_sol_ids.ids)
            ], limit=1)
            
            if active_sol:
                self.client_id = active_sol.order_id.partner_id
                self.start_date = active_sol.start_date
                self.end_date = active_sol.end_date
                return

            # Priority 2: Find active manual Artwork History booking
            active_history = self.env['media.artwork.history'].search([
                ('face_id', '=', face.id),
                ('lease_start_date', '<=', today),
                ('lease_end_date', '>=', today),
                ('id', 'not in', face.transferred_out_history_ids.ids)
            ], limit=1)

            if active_history:
                self.client_id = active_history.partner_id
                self.start_date = active_history.lease_start_date
                self.end_date = active_history.lease_end_date
                return
            
            # Priority 3: Use the face's latest known lease dates if no active booking today
            if face.latest_lease_start_date and face.latest_lease_end_date:
                self.start_date = face.latest_lease_start_date
                self.end_date = face.latest_lease_end_date
                # We still need to find the client for the latest booking if possible
                latest_sol = self.env['sale.order.line'].search([
                    ('media_face_id', '=', face.id),
                    ('state', 'in', ['sale', 'done']),
                    ('start_date', '=', face.latest_lease_start_date),
                    ('end_date', '=', face.latest_lease_end_date),
                    ('id', 'not in', face.transferred_out_sol_ids.ids)
                ], limit=1)
                if latest_sol:
                    self.client_id = latest_sol.order_id.partner_id
                else:
                    latest_history = self.env['media.artwork.history'].search([
                        ('face_id', '=', face.id),
                        ('lease_start_date', '=', face.latest_lease_start_date),
                        ('lease_end_date', '=', face.latest_lease_end_date),
                        ('id', 'not in', face.transferred_out_history_ids.ids)
                    ], limit=1)
                    if latest_history:
                        self.client_id = latest_history.partner_id

    @api.depends(
        'transfer_type', 'source_line_id', 'source_line_id.start_date', 'source_line_id.end_date',
        'target_face_id', 'source_face_id',
        'target_face_id_b', 'start_date', 'end_date',
    )
    def _compute_transfer_window_preview(self):
        for rec in self:
            info = rec._get_transfer_window_preview_text()
            if not info:
                rec.transfer_window_preview = ''
                continue
            if info.get('error'):
                rec.transfer_window_preview = (
                    '<div class="alert alert-danger" role="alert">%s</div>' % (info['error'],)
                )
            elif info.get('partial'):
                msg = info.get('message', '')
                rec.transfer_window_preview = (
                    '<div class="alert alert-warning" role="alert"><p>%s</p></div>' % (msg,)
                )
            else:
                msg = info.get('message', '')
                rec.transfer_window_preview = (
                    '<div class="alert alert-info" role="alert"><p>%s</p></div>' % (msg,)
                )

    def _get_lease_window_for_sale_line(self, line):
        """Return (start, end) for a sale order line, using line fields or linked booking log rows."""
        if not line:
            return False, False
        if line.start_date and line.end_date:
            return line.start_date, line.end_date
        ArtworkHistory = self.env['media.artwork.history']
        domain = [
            ('sale_order_line_id', '=', line.id),
            ('lease_start_date', '!=', False),
            ('lease_end_date', '!=', False),
        ]
        if line.media_face_id:
            hists = ArtworkHistory.search(
                domain + [('face_id', '=', line.media_face_id.id)]
            )
        else:
            hists = ArtworkHistory.search(domain)
        if not hists and line.media_face_id:
            hists = ArtworkHistory.search(domain)
        if hists:
            return (
                min(hists.mapped('lease_start_date')),
                max(hists.mapped('lease_end_date')),
            )
        return False, False

    def _get_requested_transfer_range(self):
        self.ensure_one()
        if self.transfer_type == 'sale_order':
            if not self.source_line_id:
                return False, False
            return self._get_lease_window_for_sale_line(self.source_line_id)
        if not self.start_date or not self.end_date:
            return False, False
        return self.start_date, self.end_date

    @staticmethod
    def _merge_inclusive_date_intervals(intervals):
        """Merge list of (start, end) inclusive date pairs; adjacent days merge into one block."""
        if not intervals:
            return []
        sort = sorted(intervals, key=lambda x: (x[0], x[1]))
        merged = [sort[0]]
        for s, e in sort[1:]:
            ls, le = merged[-1]
            if s <= le + timedelta(days=1):
                merged[-1] = (ls, max(le, e))
            else:
                merged.append((s, e))
        return merged

    @staticmethod
    def _complement_in_range(request_start, request_end, merged_blocks):
        """Return list of free inclusive (s, e) segments inside [request_start, request_end]."""
        if not request_start or not request_end or request_start > request_end:
            return []
        if not merged_blocks:
            return [(request_start, request_end)]
        relevant = []
        for bs, be in merged_blocks:
            if be < request_start or bs > request_end:
                continue
            relevant.append((max(bs, request_start), min(be, request_end)))
        if not relevant:
            return [(request_start, request_end)]
        m = MediaBookingTransfer._merge_inclusive_date_intervals(relevant)
        out = []
        cur = request_start
        for bs, be in m:
            if cur < bs:
                out.append((cur, bs - timedelta(days=1)))
            cur = be + timedelta(days=1)
            if cur > request_end:
                break
        if cur <= request_end:
            out.append((cur, request_end))
        return out

    def _iter_target_conflicting_intervals(
        self,
        target_face,
        req_start,
        req_end,
        exclude_line=None,
        extra_transferred_sol_ids=None,
        extra_transferred_history_ids=None,
    ):
        """Yield (start, end) inclusive for bookings on the target face that overlap [req_start, req_end]."""
        extra_transferred_sol_ids = set(extra_transferred_sol_ids or [])
        extra_transferred_history_ids = set(extra_transferred_history_ids or [])
        to_sol = set(target_face.transferred_out_sol_ids.ids) | extra_transferred_sol_ids
        to_hist = set(target_face.transferred_out_history_ids.ids) | extra_transferred_history_ids
        on_target_sol_ids = set()
        for line in target_face.lease_line_ids.filtered(
            lambda l: l.state in ('sale', 'done') and l.id not in to_sol
        ):
            if exclude_line and line.id == exclude_line.id:
                continue
            s, e = line.get_media_lease_effective_dates()
            if s and e and s < req_end and e > req_start:
                on_target_sol_ids.add(line.id)
                yield (s, e)
        for hist in target_face.artwork_history_ids.filtered(
            lambda h: h.id not in to_hist
            and h.lease_start_date and h.lease_end_date
            and h.lease_start_date < req_end and h.lease_end_date > req_start
        ):
            if (
                hist.sale_order_line_id
                and hist.sale_order_line_id.id in on_target_sol_ids
            ):
                continue
            yield (hist.lease_start_date, hist.lease_end_date)

    def _effective_transfer_segments(
        self,
        target_face,
        req_start,
        req_end,
        exclude_line=None,
        extra_transferred_sol_ids=None,
        extra_transferred_history_ids=None,
    ):
        """
        Return list of (start, end) inclusive segments of the request period that are not
        already covered by a confirmed sale order or artwork history on the target face.
        """
        if not target_face or not req_start or not req_end or req_start > req_end:
            return []
        all_iv = list(
            self._iter_target_conflicting_intervals(
                target_face,
                req_start,
                req_end,
                exclude_line=exclude_line,
                extra_transferred_sol_ids=extra_transferred_sol_ids,
                extra_transferred_history_ids=extra_transferred_history_ids,
            )
        )
        if not all_iv:
            return [(req_start, req_end)]
        merged = self._merge_inclusive_date_intervals(all_iv)
        return self._complement_in_range(req_start, req_end, merged)

    def _get_transfer_window_preview_text(self):
        """Return dict with keys: message, partial (bool), error (str or None)."""
        self.ensure_one()
        if self.transfer_type == 'sale_order':
            if not (self.source_line_id and self.target_face_id):
                return None
            target = self.target_face_id
        else:
            if not (self.start_date and self.end_date and self.target_face_id_b):
                return None
            target = self.target_face_id_b
        req_s, req_e = self._get_requested_transfer_range()
        if not req_s or not req_e or req_s > req_e:
            if self.transfer_type == 'sale_order' and self.source_line_id and self.target_face_id:
                return {
                    'error': _(
                        "This sale order line has no <b>Start / End</b> dates, and we could not find a "
                        "booking or artwork log with lease dates for that line. Set the dates on the "
                        "order line, or on the related booking / artwork log, then try again."
                    ),
                    'partial': False,
                }
            return None
        excl = self.source_line_id if self.transfer_type == 'sale_order' else None
        segments = self._effective_transfer_segments(target, req_s, req_e, exclude_line=excl)
        if not segments:
            return {
                'error': _(
                    "No part of the period %(req_start)s → %(req_end)s is free on the target face <b>%(face)s</b>. "
                    "Resolve or move existing commitments first."
                ) % {
                    'req_start': req_s,
                    'req_end': req_e,
                    'face': html_escape(target.display_name),
                },
                'partial': False,
            }
        full = len(segments) == 1 and segments[0][0] == req_s and segments[0][1] == req_e
        seg_text = " · ".join(
            "%s → %s" % (a, b) for a, b in segments
        )
        if full:
            return {
                'message': _(
                    "The full requested window <b>%(req_start)s</b> → <b>%(req_end)s</b> is available on <b>%(face)s</b>."
                ) % {
                    'req_start': req_s,
                    'req_end': req_e,
                    'face': html_escape(target.display_name),
                },
                'partial': False,
            }
        return {
            'message': _(
                "You asked for <b>%(req_start)s</b> → <b>%(req_end)s</b> on <b>%(face)s</b>, "
                "but part of that window is already covered by an existing commitment. "
                "The transfer will only be recorded for: <b>%(segments)s</b> (remaining free time within your requested period)."
            ) % {
                'req_start': req_s,
                'req_end': req_e,
                'face': html_escape(target.display_name),
                'segments': html_escape(seg_text),
            },
            'partial': True,
        }

    def _build_transfer_done_action(self, is_partial, req_start, req_end, segments, target_face):
        """Success notification when the wizard closes; include partial-period explanation."""
        self.ensure_one()
        seg_plain = " · ".join(
            "%s → %s" % (a, b) for a, b in segments
        )
        if is_partial:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'sticky': True,
                    'message': _(
                        "Transfer recorded (partial). You requested %(req_start)s → %(req_end)s. "
                        "The commitment on “%(face)s” was stored only for: %(segments)s. "
                        "The rest of that window is already covered on the target face."
                    ) % {
                        'req_start': req_start,
                        'req_end': req_end,
                        'face': target_face.display_name,
                        'segments': seg_plain,
                    },
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _(
                    "Transfer recorded. Booking on “%(face)s”: %(segments)s."
                ) % {
                    'face': target_face.display_name,
                    'segments': seg_plain,
                },
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _face_transfer_chatter_subtype(self):
        return self.env.ref(
            'media_finance.mt_media_face_booking_transfer', raise_if_not_found=False
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_transfer(self):
        self.ensure_one()
        if self.transfer_type == 'sale_order':
            return self._transfer_via_sale_order()
        return self._transfer_no_sale_order()

    def _transfer_via_sale_order(self):
        if not self.source_line_id:
            raise ValidationError(_("Please select the existing sale order line to transfer."))
        if not self.target_face_id:
            raise ValidationError(_("Please select the target face to transfer the booking to."))

        source_sol = self.source_line_id
        source_face = source_sol.media_face_id
        target_face = self.target_face_id
        start_date, end_date = self._get_lease_window_for_sale_line(source_sol)
        if not start_date or not end_date:
            raise ValidationError(_(
                "The sale order line has no lease start and end dates, and we could not infer them "
                "from a linked booking or artwork log. Open order %s, set Start and End on the line, "
                "or set lease dates on the booking log for that line, then try the transfer again."
            ) % (source_sol.order_id.display_name,))

        if target_face == source_face:
            raise ValidationError(_("Source and target faces must be different."))

        segments = self._effective_transfer_segments(
            target_face, start_date, end_date, exclude_line=source_sol
        )
        if not segments:
            raise ValidationError(_(
                "No part of the period %(s)s → %(e)s is free on the target face “%(face)s”."
            ) % {
                's': start_date,
                'e': end_date,
                'face': target_face.display_name,
            })
        is_partial = not (
            len(segments) == 1
            and segments[0][0] == start_date
            and segments[0][1] == end_date
        )

        # 1. Vacate source for the full contract window (SOL + any overlapping log rows).
        self._vacate_face_for_period(
            source_face, start_date, end_date, extra_sol_ids=[source_sol.id]
        )

        # 2. 'Book' the target face: one history row per free segment within the request window.
        for seg_start, seg_end in segments:
            base_desc = _(
                "TRANSFER: From %s (linked to Sale Order %s)"
            ) % (source_face.display_name, source_sol.order_id.name)
            if is_partial:
                base_desc += _(
                    " — Requested period %s → %s; this segment: %s → %s"
                ) % (start_date, end_date, seg_start, seg_end)
            self._create_inventory_history_segments(
                target_face,
                source_sol.order_id.partner_id,
                [(seg_start, seg_end)],
                base_desc,
                sale_order_line=source_sol,
            )

        # 3. Log chatter messages on both faces for full audit trail.
        seg_chatter = " · ".join(
            "%s → %s" % (a, b) for a, b in segments
        )
        period_line = _(
            "Requested (contract) period: %s → %s"
        ) % (start_date, end_date)
        if is_partial:
            period_line += _(
                "<br/>Recorded on target face: <b>%s</b> (only the free part of the requested window)"
            ) % seg_chatter
        else:
            period_line += _("<br/>Recorded on target face: <b>%s</b>") % seg_chatter
        msg_template = _(
            "<b>Booking Transfer</b><br/>"
            "Client: <b>%s</b><br/>"
            "%s<br/>"
            "Sale Order: %s"
        ) % (
            source_sol.order_id.partner_id.name,
            period_line,
            source_sol.order_id.name,
        )
        st = self._face_transfer_chatter_subtype()
        mp_kw = {}
        if st:
            mp_kw['subtype_id'] = st.id
        source_face.message_post(
            body=_(
                "Booking <b>moved away</b> from this face.<br/>%s<br/>"
                "Now transferred to: <b>%s</b>. "
                "Original SOL preserved for invoice continuity."
            ) % (msg_template, target_face.display_name),
            **mp_kw,
        )
        target_face.message_post(
            body=_(
                "Booking <b>transferred to</b> this face.<br/>%s<br/>"
                "Transferred from: <b>%s</b>."
            ) % (msg_template, source_face.display_name),
            **mp_kw,
        )

        self._recompute_face_booking_state(source_face | target_face)
        return self._build_transfer_done_action(
            is_partial, start_date, end_date, segments, target_face
        )

    def _transfer_no_sale_order(self):
        if not self.source_face_id:
            raise ValidationError(_("Please select the face being vacated."))
        if not self.target_face_id_b:
            raise ValidationError(_("Please select the target face."))
        if not self.start_date or not self.end_date:
            raise ValidationError(_("Please provide the start and end dates for the commitment."))
        if self.start_date > self.end_date:
            raise ValidationError(_("Start date must be before end date."))

        source_face = self.source_face_id
        target_face = self.target_face_id_b
        client = self.client_id

        if target_face == source_face:
            raise ValidationError(_("Source and target faces must be different."))

        segments = self._effective_transfer_segments(
            target_face, self.start_date, self.end_date, exclude_line=None
        )
        if not segments:
            raise ValidationError(_(
                "No part of the period %(s)s → %(e)s is free on the target face “%(face)s”."
            ) % {
                's': self.start_date,
                'e': self.end_date,
                'face': target_face.display_name,
            })
        is_partial = not (
            len(segments) == 1
            and segments[0][0] == self.start_date
            and segments[0][1] == self.end_date
        )

        self._vacate_face_for_period(source_face, self.start_date, self.end_date)

        for seg_start, seg_end in segments:
            desc = _("Face-to-face booking commitment")
            if client:
                desc += _(" — Client: %s") % client.name
            if self.notes:
                desc += "\n" + self.notes
            if is_partial:
                desc += _(
                    "\n(Partial transfer) Requested on target: %s → %s; this log segment: %s → %s"
                ) % (self.start_date, self.end_date, seg_start, seg_end)
            self._create_inventory_history_segments(
                target_face,
                client,
                [(seg_start, seg_end)],
                desc,
            )

        seg_chatter = " · ".join(
            "%s → %s" % (a, b) for a, b in segments
        )
        period_line = _(
            "Requested move period: %s → %s"
        ) % (self.start_date, self.end_date)
        if is_partial:
            period_line += _(
                "<br/>Recorded on target: <b>%s</b> (only the free part of the requested window on that face)"
            ) % seg_chatter
        else:
            period_line += _("<br/>Recorded on target: <b>%s</b>") % seg_chatter
        # Log chatter messages on both faces.
        msg = _(
            "<b>Face-to-Face Commitment Transfer</b><br/>"
            "Client: <b>%s</b><br/>"
            "%s<br/>"
            "Notes: %s"
        ) % (
            client.name if client else _("Unknown"),
            period_line,
            self.notes or _("N/A"),
        )
        st = self._face_transfer_chatter_subtype()
        mp_kw = {}
        if st:
            mp_kw['subtype_id'] = st.id
        source_face.message_post(
            body=_("Client commitment <b>moved away</b> from this face.<br/>%s<br/>Now on: <b>%s</b>.") % (
                msg, target_face.display_name),
            **mp_kw,
        )
        target_face.message_post(
            body=_("New face-to-face client commitment <b>recorded</b>.<br/>%s<br/>Moved from: <b>%s</b>.") % (
                msg, source_face.display_name),
            **mp_kw,
        )

        self._recompute_face_booking_state(source_face | target_face)
        return self._build_transfer_done_action(
            is_partial, self.start_date, self.end_date, segments, target_face
        )
