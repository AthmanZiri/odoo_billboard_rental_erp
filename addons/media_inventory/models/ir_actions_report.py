# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import fields, models

# wkhtmltopdf segfaults (-11) on large multi-face HTML; render in small batches.
_BILLBOARD_PDF_BATCH_SIZE = 8
_CHUNKED_PDF_REPORTS = frozenset({
    'media_inventory.report_media_asset_template',
})


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _sorted_billboard_face_ids(self, res_ids):
        """Match Billboard Asset Report print order (county, then serial 001+)."""
        faces = self.env['media.face'].browse(res_ids).exists()
        report_model = self.env['report.media_inventory.report_media_asset_template']
        return report_model._sorted_faces(faces).ids

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)
        if report.report_name in _CHUNKED_PDF_REPORTS and res_ids:
            # PDF streams are merged in res_ids order; sort before batching so
            # pages start at serial 001 and ascend (not UI/selection order).
            res_ids = self._sorted_billboard_face_ids(res_ids)
            if len(res_ids) > _BILLBOARD_PDF_BATCH_SIZE:
                collected_streams = OrderedDict()
                for batch_start in range(0, len(res_ids), _BILLBOARD_PDF_BATCH_SIZE):
                    batch_ids = res_ids[batch_start:batch_start + _BILLBOARD_PDF_BATCH_SIZE]
                    batch_streams = super()._render_qweb_pdf_prepare_streams(
                        report_ref, data, res_ids=batch_ids,
                    )
                    for res_id, stream_data in batch_streams.items():
                        if res_id:
                            collected_streams[res_id] = stream_data
                return collected_streams
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

    report_type = fields.Selection(
        selection_add=[('docx', 'Word')],
        ondelete={'docx': 'cascade'},
    )

    def _render_docx(self, report_ref, docids, data=None):
        report = self._get_report(report_ref)
        Model = self.env[report.model]
        records = Model.browse(docids).exists()
        if report.report_name == 'media_inventory.report_canopy_asset_docx':
            from odoo.addons.media_inventory.report.docx_builder import build_canopy_asset_docx
            records = records.filtered(lambda c: c.status == 'active')
            records = records.sorted(
                key=lambda c: (
                    (c.county_id.name or '').lower(),
                    (c.sub_county_id.name or '').lower(),
                    (c.shop_name or c.name or '').lower(),
                )
            )
            content = build_canopy_asset_docx(records)
            return content, 'docx'
        raise ValueError('Unsupported DOCX report: %s' % report.report_name)

    def _render(self, report_ref, res_ids, data=None):
        report = self._get_report(report_ref)
        if report.report_type == 'docx':
            return self._render_docx(report_ref, res_ids, data=data)
        return super()._render(report_ref, res_ids, data=data)

    def _get_report_filename(self, report, docids, data=None):
        if report.report_type == 'docx' and report.model == 'media.canopy':
            record = self.env['media.canopy'].browse(docids[:1])
            name = record.shop_name or record.name or 'canopy'
            return '%s - Canopy Report.docx' % name
        return super()._get_report_filename(report, docids, data=data)
