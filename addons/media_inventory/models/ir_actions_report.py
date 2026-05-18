# -*- coding: utf-8 -*-
from odoo import fields, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

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
