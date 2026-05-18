# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class MediaExecutiveCountyMetric(models.Model):
    _name = 'media.executive.county.metric'
    _description = 'County-level face occupancy metrics'
    _auto = False
    _order = 'occupancy_pct desc, county_name'

    county_id = fields.Many2one('media.county', string='County', readonly=True)
    county_name = fields.Char(string='County', readonly=True)
    face_count = fields.Integer(string='Faces', readonly=True)
    booked_count = fields.Integer(string='Booked', readonly=True)
    available_count = fields.Integer(string='Available', readonly=True)
    reserved_count = fields.Integer(string='Reserved', readonly=True)
    maintenance_count = fields.Integer(string='Maintenance', readonly=True)
    occupancy_pct = fields.Float(string='Utilization %', readonly=True, digits=(16, 2))
    list_revenue_mtd = fields.Monetary(
        string='List Revenue MTD',
        readonly=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        company = self.env.company
        currency_id = int(company.currency_id.id) if company.currency_id else 1
        # Table name comes from the model only; avoid tools.AsIs (removed in recent Odoo).
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY c.name) AS id,
                    c.id AS county_id,
                    c.name AS county_name,
                    COUNT(f.id) AS face_count,
                    SUM(CASE WHEN f.occupancy_status = 'booked' THEN 1 ELSE 0 END) AS booked_count,
                    SUM(CASE WHEN f.occupancy_status = 'available' THEN 1 ELSE 0 END) AS available_count,
                    SUM(CASE WHEN f.occupancy_status = 'reserved' THEN 1 ELSE 0 END) AS reserved_count,
                    SUM(CASE WHEN f.occupancy_status = 'maintenance' THEN 1 ELSE 0 END) AS maintenance_count,
                    CASE
                        WHEN (
                            COUNT(f.id)
                            - SUM(CASE WHEN f.occupancy_status = 'maintenance' THEN 1 ELSE 0 END)
                        ) > 0
                        THEN ROUND(
                            100.0 * SUM(CASE WHEN f.occupancy_status = 'booked' THEN 1 ELSE 0 END)::numeric
                            / (
                                COUNT(f.id)
                                - SUM(CASE WHEN f.occupancy_status = 'maintenance' THEN 1 ELSE 0 END)
                            )::numeric,
                            2
                        )
                        ELSE 0
                    END AS occupancy_pct,
                    COALESCE(SUM(f.price_per_month), 0) AS list_revenue_mtd,
                    %s AS currency_id
                FROM media_face f
                JOIN media_site s ON s.id = f.site_id
                LEFT JOIN media_county c ON c.id = s.county_id
                WHERE f.active IS TRUE
                  AND s.site_category = 'billboard'
                GROUP BY c.id, c.name
                HAVING COUNT(f.id) > 0
            )
            """ % (self._table, currency_id),
        )
