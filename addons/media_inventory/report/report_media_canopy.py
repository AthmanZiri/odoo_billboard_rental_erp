# -*- coding: utf-8 -*-
from odoo import api, models


class ReportMediaCanopyPdf(models.AbstractModel):
    _name = 'report.media_inventory.report_canopy_asset_template'
    _description = 'Canopy asset PDF report'

    @api.model
    def _get_report_values(self, docids, data=None):
        canopies = self.env['media.canopy'].browse(docids).exists()
        canopies = canopies.filtered(lambda c: c.status == 'active')
        canopies = canopies.sorted(
            key=lambda c: (
                (c.county_id.name or '').lower(),
                (c.sub_county_id.name or '').lower(),
                (c.shop_name or c.name or '').lower(),
            )
        )
        return {
            'doc_ids': canopies.ids,
            'doc_model': 'media.canopy',
            'docs': canopies,
            'data': data,
        }
