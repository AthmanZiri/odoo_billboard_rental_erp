# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MediaExecutiveSnapshot(models.Model):
    _name = 'media.executive.snapshot'
    _description = 'Daily media executive KPI snapshot'
    _order = 'snapshot_date desc'

    snapshot_date = fields.Date(string='Date', required=True, index=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    faces_total = fields.Integer(string='Total Faces')
    faces_sellable = fields.Integer(string='Sellable Faces')
    faces_booked = fields.Integer(string='Booked')
    faces_available = fields.Integer(string='Available')
    faces_reserved = fields.Integer(string='Reserved')
    faces_maintenance = fields.Integer(string='Maintenance')
    utilization_pct = fields.Float(string='Utilization %', digits=(16, 2))

    revenue_mtd = fields.Monetary(string='Revenue MTD', currency_field='currency_id')
    pipeline_value = fields.Monetary(string='Pipeline Value', currency_field='currency_id')
    ar_outstanding = fields.Monetary(string='AR Outstanding', currency_field='currency_id')

    available_7_days = fields.Integer(string='Free in 7 Days')
    available_14_days = fields.Integer(string='Free in 14 Days')
    available_30_days = fields.Integer(string='Free in 30 Days')
    leases_ending_30_days = fields.Integer(string='Leases Ending 30 Days')

    reserved_quotation_count = fields.Integer(string='Reserved Quotations')
    open_quotation_count = fields.Integer(string='Open Quotations')
    canopy_active_count = fields.Integer(string='Active Canopies')

    _sql_constraints = [
        (
            'snapshot_date_uniq',
            'unique(snapshot_date)',
            'Only one executive snapshot is allowed per day.',
        ),
    ]

    @api.model
    def cron_capture_daily_snapshot(self):
        today = fields.Date.today()
        if self.search([('snapshot_date', '=', today)], limit=1):
            return
        Dashboard = self.env['media.executive.dashboard']
        vals = Dashboard._collect_kpi_values()
        allowed = set(self._fields) - {
            'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
        }
        snapshot_vals = {k: v for k, v in vals.items() if k in allowed}
        snapshot_vals['snapshot_date'] = today
        self.create(snapshot_vals)
