from odoo.tests.common import TransactionCase
from odoo import fields
from dateutil.relativedelta import relativedelta
import base64


class TestFaceSwap(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Face = self.env['media.face']
        self.Site = self.env['media.site']
        self.SO = self.env['sale.order']
        self.ArtworkHistory = self.env['media.artwork.history']
        self.SwapWizard = self.env['media.face.swap']

        self.partner = self.Partner.create({'name': 'Swap Client'})
        self.site = self.Site.create({'name': 'Swap Site', 'code': 'SS'})
        self.face_a = self.Face.create({
            'name': 'Face A',
            'site_id': self.site.id,
            'face_type': 'inbound',
            'price_per_month': 1000,
        })
        self.face_b = self.Face.create({
            'name': 'Face B',
            'site_id': self.site.id,
            'face_type': 'outbound',
            'price_per_month': 1000,
        })

    def _placeholder(self):
        raw = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return base64.b64encode(raw)

    def test_swap_overlapping_bookings_on_both_faces(self):
        """Swapping should vacate each face's booking in the window before placing on the other."""
        today = fields.Date.today()
        swap_start = today
        swap_end = today + relativedelta(days=4)

        order_a = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face_a.product_id.id,
                'media_face_id': self.face_a.id,
                'start_date': swap_start,
                'end_date': swap_end,
                'price_unit': 1000,
            })],
        })
        order_a.action_confirm()

        block_start = today - relativedelta(days=10)
        block_end = today + relativedelta(days=15)
        order_b = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face_b.product_id.id,
                'media_face_id': self.face_b.id,
                'start_date': block_start,
                'end_date': block_end,
                'price_unit': 1000,
            })],
        })
        order_b.action_confirm()

        wizard = self.SwapWizard.create({
            'face_a_id': self.face_a.id,
            'face_b_id': self.face_b.id,
            'start_date': swap_start,
            'end_date': swap_end,
        })
        wizard.action_swap()

        on_b = self.ArtworkHistory.search([
            ('face_id', '=', self.face_b.id),
            ('lease_start_date', '=', swap_start),
            ('lease_end_date', '=', swap_end),
        ])
        on_a = self.ArtworkHistory.search([
            ('face_id', '=', self.face_a.id),
            ('lease_start_date', '<=', swap_end),
            ('lease_end_date', '>=', swap_start),
        ])
        self.assertTrue(on_b, "Face A booking should appear on Face B after swap")
        self.assertTrue(on_a, "Face B booking should appear on Face A after swap")
