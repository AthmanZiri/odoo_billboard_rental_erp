# -*- coding: utf-8 -*-
import re

from odoo import api, models

# Print order for billboard asset PDF: priority counties first, then alphabetical.
_COUNTY_PRINT_PRIORITY = {
    'mombasa': 0,
    'kilifi': 1,
    'lamu': 2,
    'nairobi': 3,
}

# Face labels look like "001/I", "024/O (OUTBOUND FACE)", etc.
_FACE_SERIAL_RE = re.compile(r'^(\d+)')


class ReportMediaAsset(models.AbstractModel):
    _name = 'report.media_inventory.report_media_asset_template'
    _description = 'Billboard asset report'

    @staticmethod
    def _county_print_sort_key(county_name):
        name = (county_name or '').lower().strip()
        return (_COUNTY_PRINT_PRIORITY.get(name, 100), name)

    @classmethod
    def _face_print_sort_key(cls, face):
        """County priority, then numeric serial (001, 002, …), then face suffix (I/O)."""
        label = (face.code or face.name or '').strip()
        match = _FACE_SERIAL_RE.match(label)
        if match:
            serial = int(match.group(1))
            suffix = label[match.end():].lower()
        else:
            serial = 10 ** 9
            suffix = label.lower()
        return (
            cls._county_print_sort_key(face.site_id.county_id.name),
            serial,
            suffix,
            label.lower(),
            face.id,
        )

    @api.model
    def _sorted_faces(self, faces):
        return faces.sorted(key=self._face_print_sort_key)

    @api.model
    def _get_report_values(self, docids, data=None):
        faces = self._sorted_faces(self.env['media.face'].browse(docids).exists())
        return {
            'doc_ids': faces.ids,
            'doc_model': 'media.face',
            'docs': faces,
            'data': data,
        }
