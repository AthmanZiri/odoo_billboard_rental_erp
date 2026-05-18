# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class MediaExecutiveCountyLine(models.TransientModel):
    _name = 'media.executive.county.line'
    _description = 'County metric row on executive dashboard'
    _order = 'occupancy_pct desc, county_name'

    dashboard_id = fields.Many2one('media.executive.dashboard', ondelete='cascade')
    county_id = fields.Many2one('media.county', string='County')
    county_name = fields.Char(string='County')
    face_count = fields.Integer(string='Faces')
    booked_count = fields.Integer(string='Booked')
    available_count = fields.Integer(string='Available')
    reserved_count = fields.Integer(string='Reserved')
    occupancy_pct = fields.Float(string='Utilization %', digits=(16, 2))
    list_revenue_mtd = fields.Monetary(string='List Rate Total', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')


class MediaExecutiveDashboard(models.TransientModel):
    _name = 'media.executive.dashboard'
    _description = 'Media executive dashboard'

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    as_of_date = fields.Date(
        string='As of',
        default=fields.Date.today,
        readonly=True,
    )

    # Inventory
    faces_total = fields.Integer(readonly=True)
    faces_sellable = fields.Integer(readonly=True)
    faces_booked = fields.Integer(readonly=True)
    faces_available = fields.Integer(readonly=True)
    faces_reserved = fields.Integer(readonly=True)
    faces_maintenance = fields.Integer(readonly=True)
    utilization_pct = fields.Float(string='Utilization %', digits=(16, 2), readonly=True)

    # Financial
    revenue_mtd = fields.Monetary(currency_field='currency_id', readonly=True)
    pipeline_value = fields.Monetary(currency_field='currency_id', readonly=True)
    ar_outstanding = fields.Monetary(currency_field='currency_id', readonly=True)
    revenue_ytd = fields.Monetary(currency_field='currency_id', readonly=True)

    # Sales pipeline
    open_quotation_count = fields.Integer(readonly=True)
    reserved_quotation_count = fields.Integer(readonly=True)
    confirmed_order_mtd = fields.Integer(readonly=True)

    # Availability & expiries
    available_2_days = fields.Integer(readonly=True)
    available_7_days = fields.Integer(readonly=True)
    available_14_days = fields.Integer(readonly=True)
    available_30_days = fields.Integer(readonly=True)
    leases_ending_7_days = fields.Integer(readonly=True)
    leases_ending_30_days = fields.Integer(readonly=True)
    expired_lease_count = fields.Integer(readonly=True)

    # Other assets
    canopy_active_count = fields.Integer(readonly=True)
    canopy_inactive_count = fields.Integer(readonly=True)
    transfers_mtd = fields.Integer(readonly=True)
    open_job_card_count = fields.Integer(readonly=True)

    county_line_ids = fields.One2many(
        'media.executive.county.line',
        'dashboard_id',
        string='By County',
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # KPI collection (shared with daily snapshot cron)
    # -------------------------------------------------------------------------

    @api.model
    def _media_line_domain(self):
        return [
            '|', '|', '|',
            ('media_face_id', '!=', False),
            ('canopy_id', '!=', False),
            ('media_digital_screen_id', '!=', False),
            ('media_slot_id', '!=', False),
        ]

    @api.model
    def _billboard_faces(self):
        return self.env['media.face'].search([
            ('active', '=', True),
            ('site_id.site_category', '=', 'billboard'),
        ])

    @api.model
    def _occupancy_counts(self, faces):
        """Count faces by occupancy_status (single pass)."""
        counts = {
            'booked': 0,
            'available': 0,
            'reserved': 0,
            'maintenance': 0,
            'other': 0,
        }
        for face in faces:
            status = face.occupancy_status or 'other'
            if status in counts:
                counts[status] += 1
            else:
                counts['other'] += 1
        return counts

    @api.model
    def _collect_kpi_values(self):
        """Return a dict of KPI values for snapshots and dashboards."""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        billboard_faces = self._billboard_faces()
        occ = self._occupancy_counts(billboard_faces)
        maintenance = occ['maintenance']
        sellable_count = len(billboard_faces) - maintenance
        booked_count = occ['booked']
        utilization = (
            100.0 * booked_count / sellable_count if sellable_count else 0.0
        )

        SOL = self.env['sale.order.line']
        media_domain = self._media_line_domain()
        revenue_mtd_lines = SOL.search(
            media_domain + [
                ('state', 'in', ('sale', 'done')),
                ('order_id.date_order', '>=', month_start),
                ('order_id.date_order', '<=', today),
            ]
        )
        revenue_ytd_lines = SOL.search(
            media_domain + [
                ('state', 'in', ('sale', 'done')),
                ('order_id.date_order', '>=', year_start),
                ('order_id.date_order', '<=', today),
            ]
        )
        pipeline_orders = self.env['sale.order'].search([
            ('state', 'in', ('draft', 'sent')),
            ('order_line.media_face_id', '!=', False),
        ])
        pipeline_value = sum(pipeline_orders.mapped('amount_untaxed'))

        reserved_orders = self.env['sale.order'].search([
            ('state', 'in', ('draft', 'sent')),
            ('media_reserve_inventory', '=', True),
            ('order_line.media_face_id', '!=', False),
        ])
        open_quotations = self.env['sale.order'].search([
            ('state', 'in', ('draft', 'sent')),
            '|',
            ('order_line.media_face_id', '!=', False),
            ('order_line.canopy_id', '!=', False),
        ])
        confirmed_mtd = self.env['sale.order'].search_count([
            ('state', 'in', ('sale', 'done')),
            ('date_order', '>=', month_start),
            ('date_order', '<=', today),
            '|',
            ('order_line.media_face_id', '!=', False),
            ('order_line.canopy_id', '!=', False),
        ])

        ar_moves = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])
        ar_lines = ar_moves.mapped('invoice_line_ids').filtered(
            lambda l: l.media_face_id or l.canopy_id or l.media_digital_screen_id
        )
        ar_outstanding = sum(ar_lines.mapped('move_id').mapped('amount_residual'))

        end_7 = today + relativedelta(days=7)
        end_30 = today + relativedelta(days=30)
        leases_ending_7 = billboard_faces.filtered(
            lambda f: f.current_booking_end
            and today <= f.current_booking_end <= end_7
        )
        leases_ending_30 = billboard_faces.filtered(
            lambda f: f.current_booking_end
            and today <= f.current_booking_end <= end_30
        )

        transfer_subtype = self.env.ref(
            'media_finance.mt_media_face_booking_transfer',
            raise_if_not_found=False,
        )
        transfers_mtd = 0
        if transfer_subtype:
            transfers_mtd = self.env['mail.message'].search_count([
                ('model', '=', 'media.face'),
                ('subtype_id', '=', transfer_subtype.id),
                ('date', '>=', fields.Datetime.to_datetime(month_start)),
            ])

        canopies = self.env['media.canopy'].search([])
        job_cards_open = 0
        if 'media.job.card' in self.env:
            job_cards_open = self.env['media.job.card'].search_count([
                ('state', 'in', ('draft', 'assigned', 'in_progress')),
            ])

        return {
            'currency_id': self.env.company.currency_id.id,
            'faces_total': len(billboard_faces),
            'faces_sellable': sellable_count,
            'faces_booked': booked_count,
            'faces_available': occ['available'],
            'faces_reserved': occ['reserved'],
            'faces_maintenance': maintenance,
            'utilization_pct': round(utilization, 2),
            'revenue_mtd': sum(revenue_mtd_lines.mapped('price_subtotal')),
            'revenue_ytd': sum(revenue_ytd_lines.mapped('price_subtotal')),
            'pipeline_value': pipeline_value,
            'ar_outstanding': ar_outstanding,
            'open_quotation_count': len(open_quotations),
            'reserved_quotation_count': len(reserved_orders),
            'confirmed_order_mtd': confirmed_mtd,
            'available_2_days': len(billboard_faces.filtered('is_available_in_2_days')),
            'available_7_days': len(billboard_faces.filtered('is_available_in_7_days')),
            'available_14_days': len(billboard_faces.filtered('is_available_in_14_days')),
            'available_30_days': len(billboard_faces.filtered('is_soon_available')),
            'leases_ending_7_days': len(leases_ending_7),
            'leases_ending_30_days': len(leases_ending_30),
            'expired_lease_count': len(billboard_faces.filtered('is_expired')),
            'canopy_active_count': len(canopies.filtered(lambda c: c.status == 'active')),
            'canopy_inactive_count': len(canopies.filtered(
                lambda c: c.status in ('inactive', 'withdrawn')
            )),
            'transfers_mtd': transfers_mtd,
            'open_job_card_count': job_cards_open,
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._refresh_metrics()
        return records

    def _refresh_metrics(self):
        values = self._collect_kpi_values()
        CountyMetric = self.env['media.executive.county.metric']
        for record in self:
            write_vals = {
                k: v for k, v in values.items()
                if k in record._fields
            }
            dashboard_currency = record.currency_id.id or values.get('currency_id')
            county_commands = [(5, 0, 0)]
            for row in CountyMetric.search([]):
                county_commands.append((0, 0, {
                    'county_id': row.county_id.id,
                    'county_name': row.county_name or _('No county'),
                    'face_count': row.face_count,
                    'booked_count': row.booked_count,
                    'available_count': row.available_count,
                    'reserved_count': row.reserved_count,
                    'occupancy_pct': row.occupancy_pct,
                    'list_revenue_mtd': row.list_revenue_mtd,
                    'currency_id': dashboard_currency or row.currency_id.id,
                }))
            write_vals['county_line_ids'] = county_commands
            record.write(write_vals)

    @api.model
    def action_open_dashboard(self):
        return {
            'name': _('Executive Dashboard'),
            'type': 'ir.actions.client',
            'tag': 'media_dashboard.executive_dashboard',
            'target': 'main',
        }

    @api.model
    def action_open_dashboard_form(self):
        """Classic form fallback (debug / exports)."""
        dashboard = self.create({})
        return {
            'name': _('Executive Dashboard (Form)'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.executive.dashboard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': dashboard.id,
            'target': 'main',
            'context': {'create': False},
        }

    @api.model
    def _format_currency_meta(self):
        currency = self.env.company.currency_id
        return {
            'id': currency.id,
            'symbol': currency.symbol or '',
            'position': currency.position,
            'decimal_places': currency.decimal_places,
        }

    @api.model
    def get_dashboard_data(self):
        """JSON payload for the OWL executive dashboard."""
        values = self._collect_kpi_values()
        today = fields.Date.today()
        Snapshot = self.env['media.executive.snapshot']

        snap_7 = Snapshot.search(
            [('snapshot_date', '<=', today - relativedelta(days=7))],
            order='snapshot_date desc',
            limit=1,
        )
        snap_30 = Snapshot.search(
            [('snapshot_date', '<=', today - relativedelta(days=30))],
            order='snapshot_date desc',
            limit=1,
        )
        util_delta = (
            round(values['utilization_pct'] - snap_7.utilization_pct, 2)
            if snap_7 else None
        )
        revenue_delta = (
            values['revenue_mtd'] - snap_30.revenue_mtd
            if snap_30 else None
        )

        counties = []
        for row in self.env['media.executive.county.metric'].search([]):
            counties.append({
                'county_id': row.county_id.id,
                'county_name': row.county_name or _('No county'),
                'face_count': row.face_count,
                'booked_count': row.booked_count,
                'available_count': row.available_count,
                'reserved_count': row.reserved_count,
                'occupancy_pct': row.occupancy_pct,
                'list_revenue_mtd': row.list_revenue_mtd,
            })

        trend_start = today - relativedelta(days=30)
        trend = [
            {
                'date': fields.Date.to_string(s.snapshot_date),
                'utilization_pct': s.utilization_pct,
                'revenue_mtd': s.revenue_mtd,
                'faces_booked': s.faces_booked,
            }
            for s in Snapshot.search(
                [('snapshot_date', '>=', trend_start)],
                order='snapshot_date asc',
            )
        ]

        sellable = values['faces_sellable']
        booked = values['faces_booked']
        pct = values['utilization_pct']
        insight = _(
            '%(sellable)s sellable faces — %(booked)s booked (%(pct)s%% utilization)'
        ) % {'sellable': sellable, 'booked': booked, 'pct': pct}

        inbox = [
            {
                'key': 'available_7_days',
                'label': _('Free in 7 days'),
                'count': values['available_7_days'],
                'level': 'success',
            },
            {
                'key': 'leases_ending_30',
                'label': _('Leases ending ≤30d'),
                'count': values['leases_ending_30_days'],
                'level': 'warning',
            },
            {
                'key': 'reserved_quotations',
                'label': _('Quotes holding inventory'),
                'count': values['reserved_quotation_count'],
                'level': 'info',
            },
            {
                'key': 'pipeline',
                'label': _('Open quotations'),
                'count': values['open_quotation_count'],
                'level': 'info',
            },
            {
                'key': 'ar_outstanding',
                'label': _('Overdue / unpaid AR'),
                'count': values['ar_outstanding'],
                'level': 'danger' if values['ar_outstanding'] else 'muted',
                'is_money': True,
            },
            {
                'key': 'expired_lease',
                'label': _('Expired leases'),
                'count': values['expired_lease_count'],
                'level': 'danger' if values['expired_lease_count'] else 'muted',
            },
        ]

        return {
            'as_of_date': fields.Date.to_string(today),
            'currency': self._format_currency_meta(),
            'insight': insight,
            'hero': {
                'utilization_pct': values['utilization_pct'],
                'utilization_delta': util_delta,
                'revenue_mtd': values['revenue_mtd'],
                'revenue_ytd': values['revenue_ytd'],
                'revenue_delta': revenue_delta,
                'pipeline_value': values['pipeline_value'],
                'ar_outstanding': values['ar_outstanding'],
            },
            'occupancy': {
                'available': values['faces_available'],
                'booked': values['faces_booked'],
                'reserved': values['faces_reserved'],
                'maintenance': values['faces_maintenance'],
                'total': values['faces_total'],
                'sellable': values['faces_sellable'],
            },
            'inventory': {
                'faces_total': values['faces_total'],
                'faces_sellable': values['faces_sellable'],
                'available_2_days': values['available_2_days'],
                'available_14_days': values['available_14_days'],
                'leases_ending_7_days': values['leases_ending_7_days'],
                'canopy_active_count': values['canopy_active_count'],
                'transfers_mtd': values['transfers_mtd'],
                'open_job_card_count': values['open_job_card_count'],
            },
            'counties': counties,
            'trend': trend,
            'inbox': inbox,
        }

    @api.model
    def action_drilldown(self, key):
        """Open a list view from dashboard tiles (no transient record required)."""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        end_30 = today + relativedelta(days=30)
        drilldowns = {
            'booked_faces': lambda: self._action_list(
                'media.face',
                _('Booked Faces'),
                [
                    ('active', '=', True),
                    ('site_id.site_category', '=', 'billboard'),
                    ('occupancy_status', '=', 'booked'),
                ],
            ),
            'available_faces': lambda: self._action_list(
                'media.face',
                _('Available Faces'),
                [
                    ('active', '=', True),
                    ('site_id.site_category', '=', 'billboard'),
                    ('occupancy_status', '=', 'available'),
                ],
            ),
            'available_7_days': lambda: self._action_list(
                'media.face',
                _('Available in 7 Days'),
                [('is_available_in_7_days', '=', True)],
                {'search_default_filter_available_7_days': 1},
            ),
            'leases_ending_30': lambda: self._action_list(
                'media.face',
                _('Leases Ending in 30 Days'),
                [
                    ('active', '=', True),
                    ('current_booking_end', '>=', today),
                    ('current_booking_end', '<=', end_30),
                ],
            ),
            'pipeline': lambda: self._action_list(
                'sale.order',
                _('Pipeline Quotations'),
                [
                    ('state', 'in', ('draft', 'sent')),
                    '|',
                    ('order_line.media_face_id', '!=', False),
                    ('order_line.canopy_id', '!=', False),
                ],
            ),
            'reserved_quotations': lambda: self._action_list(
                'sale.order',
                _('Quotations Reserving Inventory'),
                [
                    ('state', 'in', ('draft', 'sent')),
                    ('media_reserve_inventory', '=', True),
                    ('order_line.media_face_id', '!=', False),
                ],
            ),
            'revenue_mtd': lambda: self._action_list(
                'sale.order.line',
                _('Confirmed Media Revenue (MTD)'),
                self._media_line_domain() + [
                    ('state', 'in', ('sale', 'done')),
                    ('order_id.date_order', '>=', month_start),
                    ('order_id.date_order', '<=', today),
                ],
            ),
            'ar_outstanding': lambda: self._drilldown_ar_outstanding(),
            'expired_lease': lambda: self._action_list(
                'media.face',
                _('Expired Leases'),
                [
                    ('active', '=', True),
                    ('site_id.site_category', '=', 'billboard'),
                    ('is_expired', '=', True),
                ],
            ),
            'county_metrics': lambda: self._window_action(
                'media.executive.county.metric',
                _('County Utilization'),
                view_mode='list,graph,pivot',
            ),
            'snapshots': lambda: self._window_action(
                'media.executive.snapshot',
                _('Utilization History'),
                view_mode='graph,list',
            ),
        }
        if key not in drilldowns:
            return False
        return drilldowns[key]()

    @api.model
    def _window_action(self, res_model, name, domain=None, context=None, view_mode='list,form'):
        """Build an act_window dict compatible with the web client (requires views)."""
        modes = [m.strip() for m in view_mode.split(',') if m.strip()]
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'view_mode': ','.join(modes),
            'views': [(False, mode) for mode in modes],
            'domain': domain or [],
            'context': dict(context or {}, create=False),
            'target': 'current',
        }

    def _action_list(self, model, name, domain, context=None):
        return self._window_action(model, name, domain=domain, context=context)

    @api.model
    def _drilldown_ar_outstanding(self):
        moves = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])
        media_moves = moves.filtered(
            lambda m: m.invoice_line_ids.filtered(
                lambda l: l.media_face_id or l.canopy_id or l.media_digital_screen_id
            )
        )
        return self._window_action(
            'account.move',
            _('Outstanding Media Invoices'),
            domain=[('id', 'in', media_moves.ids)],
        )

    def action_view_booked_faces(self):
        return self._action_list(
            'media.face',
            _('Booked Faces'),
            [
                ('active', '=', True),
                ('site_id.site_category', '=', 'billboard'),
                ('occupancy_status', '=', 'booked'),
            ],
        )

    def action_view_available_faces(self):
        return self._action_list(
            'media.face',
            _('Available Faces'),
            [
                ('active', '=', True),
                ('site_id.site_category', '=', 'billboard'),
                ('occupancy_status', '=', 'available'),
            ],
        )

    def action_view_reserved_faces(self):
        return self._action_list(
            'media.face',
            _('Reserved Faces'),
            [
                ('active', '=', True),
                ('site_id.site_category', '=', 'billboard'),
                ('occupancy_status', '=', 'reserved'),
            ],
        )

    def action_view_available_7_days(self):
        return self._action_list(
            'media.face',
            _('Available in 7 Days'),
            [('is_available_in_7_days', '=', True)],
            {'search_default_filter_available_7_days': 1},
        )

    def action_view_available_30_days(self):
        return self._action_list(
            'media.face',
            _('Available in 30 Days'),
            [('is_soon_available', '=', True)],
            {'search_default_filter_soon_available': 1},
        )

    def action_view_leases_ending_30(self):
        today = fields.Date.today()
        end = today + relativedelta(days=30)
        return self._action_list(
            'media.face',
            _('Leases Ending in 30 Days'),
            [
                ('active', '=', True),
                ('current_booking_end', '>=', today),
                ('current_booking_end', '<=', end),
            ],
        )

    def action_view_pipeline(self):
        return self._action_list(
            'sale.order',
            _('Pipeline Quotations'),
            [
                ('state', 'in', ('draft', 'sent')),
                '|',
                ('order_line.media_face_id', '!=', False),
                ('order_line.canopy_id', '!=', False),
            ],
        )

    def action_view_reserved_quotations(self):
        return self._action_list(
            'sale.order',
            _('Quotations Reserving Inventory'),
            [
                ('state', 'in', ('draft', 'sent')),
                ('media_reserve_inventory', '=', True),
                ('order_line.media_face_id', '!=', False),
            ],
        )

    def action_view_revenue_mtd(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)
        return self._action_list(
            'sale.order.line',
            _('Confirmed Media Revenue (MTD)'),
            self._media_line_domain() + [
                ('state', 'in', ('sale', 'done')),
                ('order_id.date_order', '>=', month_start),
                ('order_id.date_order', '<=', today),
            ],
        )

    def action_view_ar_outstanding(self):
        return self._drilldown_ar_outstanding()

    def action_view_county_metrics(self):
        return self._window_action(
            'media.executive.county.metric',
            _('County Utilization'),
            view_mode='list,graph,pivot',
        )

    def action_view_snapshots(self):
        return self._window_action(
            'media.executive.snapshot',
            _('Utilization History'),
            view_mode='graph,list',
        )

    def action_refresh_dashboard(self):
        self.ensure_one()
        self._refresh_metrics()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'media.executive.dashboard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_id': self.id,
            'target': 'main',
        }
