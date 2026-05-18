# -*- coding: utf-8 -*-
from odoo import api, models


class ReportMediaAsset(models.AbstractModel):
    _name = 'report.media_inventory.report_media_asset_template'
    _description = 'Billboard asset report'

    @api.model
    def _get_report_values(self, docids, data=None):
        faces = self.env['media.face'].browse(docids).exists()
        faces = faces.sorted(
            key=lambda f: (
                (f.site_id.county_id.name or '').lower(),
                (f.site_id.sub_county_id.name or '').lower(),
                (f.code or f.name or '').lower(),
            )
        )
        return {
            'doc_ids': faces.ids,
            'doc_model': 'media.face',
            'docs': faces,
            'data': data,
        }
