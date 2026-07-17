# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestBillboardReportOrder(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Report = self.env['report.media_inventory.report_media_asset_template']
        County = self.env['media.county']
        self.mombasa = County.search([('name', '=', 'Mombasa')], limit=1) or County.create({'name': 'Mombasa'})
        self.nairobi = County.search([('name', '=', 'Nairobi')], limit=1) or County.create({'name': 'Nairobi'})

        self.site_msa = self.env['media.site'].create({
            'name': 'MSA Site',
            'code': 'MSA-T',
            'county_id': self.mombasa.id,
        })
        self.site_nbo = self.env['media.site'].create({
            'name': 'NBO Site',
            'code': 'NBO-T',
            'county_id': self.nairobi.id,
        })

    def _face(self, name, site):
        return self.env['media.face'].create({
            'name': name,
            'site_id': site.id,
            'face_type': 'inbound' if name.endswith('/I') else 'outbound',
        })

    def test_faces_sorted_by_numeric_serial_within_county(self):
        face_024 = self._face('024/I', self.site_msa)
        face_001_o = self._face('001/O', self.site_msa)
        face_001_i = self._face('001/I', self.site_msa)
        face_002 = self._face('002/O', self.site_msa)
        face_nbo = self._face('001/I', self.site_nbo)

        # Selection order deliberately wrong (024 first).
        faces = face_024 | face_nbo | face_002 | face_001_o | face_001_i
        ordered = self.Report._sorted_faces(faces)

        self.assertEqual(
            ordered.mapped('name'),
            ['001/I', '001/O', '002/O', '024/I', '001/I'],
        )
        self.assertEqual(ordered[0].site_id.county_id, self.mombasa)
        self.assertEqual(ordered[-1].site_id.county_id, self.nairobi)

    def test_pdf_res_ids_sorted_before_render(self):
        face_024 = self._face('024/I', self.site_msa)
        face_001 = self._face('001/I', self.site_msa)
        report = self.env['ir.actions.report']
        sorted_ids = report._sorted_billboard_face_ids([face_024.id, face_001.id])
        self.assertEqual(sorted_ids, [face_001.id, face_024.id])
