# -*- coding: utf-8 -*-
from odoo import api, models

# Print order for billboard asset PDF: priority counties first, then alphabetical.
_COUNTY_PRINT_PRIORITY = {
    'mombasa': 0,
    'kilifi': 1,
    'lamu': 2,
    'nairobi': 3,
}


class ReportMediaAsset(models.AbstractModel):
    _name = 'report.media_inventory.report_media_asset_template'
    _description = 'Billboard asset report'

    @staticmethod
    def _county_print_sort_key(county_name):
        name = (county_name or '').lower().strip()
        return (_COUNTY_PRINT_PRIORITY.get(name, 100), name)

    @api.model
    def _get_report_values(self, docids, data=None):
        faces = self.env['media.face'].browse(docids).exists()
        faces = faces.sorted(
            key=lambda f: (
                self._county_print_sort_key(f.site_id.county_id.name),
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
