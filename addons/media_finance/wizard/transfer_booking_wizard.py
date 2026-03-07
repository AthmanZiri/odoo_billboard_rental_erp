from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MediaBookingTransfer(models.TransientModel):
    _name = 'media.booking.transfer'
    _description = 'Transfer Billboard Face Booking'

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

    @api.depends('source_line_id')
    def _compute_source_face_info(self):
        for rec in self:
            if rec.source_line_id:
                sol = rec.source_line_id
                face = sol.media_face_id
                rec.source_face_info = (
                    f"{face.display_name}  |  "
                    f"{sol.start_date} → {sol.end_date}  |  "
                    f"SO: {sol.order_id.name}  |  "
                    f"Client: {sol.order_id.partner_id.name}"
                )
            else:
                rec.source_face_info = ''

    # ── Validation ────────────────────────────────────────────────────────────

    def _check_target_availability(self, target_face, start_date, end_date, exclude_line=None):
        """Raise ValidationError if target_face already has a confirmed booking overlapping the period."""
        domain = [
            ('media_face_id', '=', target_face.id),
            ('state', 'in', ['sale', 'done']),
            ('start_date', '<=', end_date),
            ('end_date', '>=', start_date),
        ]
        if exclude_line:
            domain += [('id', '!=', exclude_line.id)]
        count = self.env['sale.order.line'].search_count(domain)
        if count:
            raise ValidationError(_(
                "The face '%s' already has a confirmed booking for the period %s → %s."
            ) % (target_face.display_name, start_date, end_date))

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_transfer(self):
        self.ensure_one()
        if self.transfer_type == 'sale_order':
            self._transfer_via_sale_order()
        else:
            self._transfer_no_sale_order()
        return {'type': 'ir.actions.act_window_close'}

    def _transfer_via_sale_order(self):
        if not self.source_line_id:
            raise ValidationError(_("Please select the existing sale order line to transfer."))
        if not self.target_face_id:
            raise ValidationError(_("Please select the target face to transfer the booking to."))

        source_sol = self.source_line_id
        source_face = source_sol.media_face_id
        target_face = self.target_face_id
        start_date = source_sol.start_date
        end_date = source_sol.end_date

        if target_face == source_face:
            raise ValidationError(_("Source and target faces must be different."))

        self._check_target_availability(target_face, start_date, end_date, exclude_line=source_sol)

        # 1. 'Free up' the source face by adding this SOL to its exclusion list.
        #    This does NOT change the Sale Order (KRA compliance), but tells
        #    the inventory system to ignore this line for occupancy on this face.
        source_face.sudo().write({
            'transferred_out_sol_ids': [(4, source_sol.id)]
        })

        # 2. 'Book' the target face by creating an artwork history record.
        #    We use the same dates/client as the original booking.
        TRANSPARENT_1PX = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        import base64
        placeholder = base64.b64encode(TRANSPARENT_1PX)

        self.env['media.artwork.history'].with_context(skip_face_sync=True).sudo().create({
            'face_id': target_face.id,
            'partner_id': source_sol.order_id.partner_id.id,
            'lease_start_date': start_date,
            'lease_end_date': end_date,
            'artwork_file': placeholder,
            'description': _(
                "TRANSFER: From %s (linked to Sale Order %s)"
            ) % (source_face.display_name, source_sol.order_id.name),
            'sale_order_line_id': source_sol.id,
        })

        # 3. Log chatter messages on both faces for full audit trail.
        msg_template = _(
            "<b>Booking Transfer</b><br/>"
            "Client: <b>%s</b><br/>"
            "Period: %s → %s<br/>"
            "Sale Order: %s"
        ) % (
            source_sol.order_id.partner_id.name,
            start_date, end_date,
            source_sol.order_id.name,
        )
        source_face.message_post(
            body=_(
                "Booking <b>moved away</b> from this face.<br/>%s<br/>"
                "Now transferred to: <b>%s</b>. "
                "Original SOL preserved for invoice continuity."
            ) % (msg_template, target_face.display_name)
        )
        target_face.message_post(
            body=_(
                "Booking <b>transferred to</b> this face.<br/>%s<br/>"
                "Transferred from: <b>%s</b>."
            ) % (msg_template, source_face.display_name)
        )

        # 4. Recompute occupancy on both faces.
        (source_face | target_face)._compute_occupancy_status()

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

        self._check_target_availability(target_face, self.start_date, self.end_date)

        # 1. 'Free up' the source face by adding overlapping bookings to its exclusion lists.
        #    This handles both Sale Order bookings and manual Artwork History bookings.
        overlapping_sols = self.env['sale.order.line'].search([
            ('media_face_id', '=', source_face.id),
            ('state', 'in', ['sale', 'done']),
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
        ])
        if overlapping_sols:
            source_face.sudo().write({
                'transferred_out_sol_ids': [(4, sol.id) for sol in overlapping_sols]
            })

        overlapping_history = self.env['media.artwork.history'].search([
            ('face_id', '=', source_face.id),
            ('lease_start_date', '<=', self.end_date),
            ('lease_end_date', '>=', self.start_date),
        ])
        if overlapping_history:
            source_face.sudo().write({
                'transferred_out_history_ids': [(4, hist.id) for hist in overlapping_history]
            })

        # 2. Create an artwork history record as a face-to-face booking commitment log.
        # We use a small placeholder image (1px transparent PNG) if no artwork exists,
        # since artwork_history requires artwork_file.
        TRANSPARENT_1PX = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        import base64
        placeholder = base64.b64encode(TRANSPARENT_1PX)

        desc = _("Face-to-face booking commitment")
        if client:
            desc += _(" — Client: %s") % client.name
        if self.notes:
            desc += "\n" + self.notes

        self.env['media.artwork.history'].with_context(skip_face_sync=True).sudo().create({
            'face_id': target_face.id,
            'partner_id': client.id if client else False,
            'lease_start_date': self.start_date,
            'lease_end_date': self.end_date,
            'artwork_file': placeholder,
            'description': desc,
        })

        # Log chatter messages on both faces.
        msg = _(
            "<b>Face-to-Face Commitment Transfer</b><br/>"
            "Client: <b>%s</b><br/>"
            "Period: %s → %s<br/>"
            "Notes: %s"
        ) % (
            client.name if client else _("Unknown"),
            self.start_date, self.end_date,
            self.notes or _("N/A"),
        )
        source_face.message_post(
            body=_("Client commitment <b>moved away</b> from this face.<br/>%s<br/>Now on: <b>%s</b>.") % (
                msg, target_face.display_name)
        )
        target_face.message_post(
            body=_("New face-to-face client commitment <b>recorded</b>.<br/>%s<br/>Moved from: <b>%s</b>.") % (
                msg, source_face.display_name)
        )

        # Recompute occupancy on both faces.
        (source_face | target_face)._compute_occupancy_status()
