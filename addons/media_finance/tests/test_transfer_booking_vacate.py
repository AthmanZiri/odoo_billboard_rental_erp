from odoo.tests.common import TransactionCase
from odoo import fields
from dateutil.relativedelta import relativedelta
import base64

class TestTransferBookingVacate(TransactionCase):

    def setUp(self):
        super(TestTransferBookingVacate, self).setUp()
        self.Partner = self.env['res.partner']
        self.Face = self.env['media.face']
        self.Site = self.env['media.site']
        self.SO = self.env['sale.order']
        self.ArtworkHistory = self.env['media.artwork.history']
        self.TransferWizard = self.env['media.booking.transfer']

        self.partner = self.Partner.create({'name': 'Test Client'})
        self.site = self.Site.create({'name': 'Test Site', 'code': 'TS'})
        
        # Ensure products are synced/created
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

    def test_transfer_vacate_artwork_history(self):
        """ Test that transferring an Artwork History booking vacates the source face """
        today = fields.Date.today()
        start = today
        end = today + relativedelta(days=10)

        # 1. Create Artwork History on Face A
        TRANSPARENT_1PX = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        placeholder = base64.b64encode(TRANSPARENT_1PX)

        history = self.ArtworkHistory.create({
            'face_id': self.face_a.id,
            'partner_id': self.partner.id,
            'lease_start_date': start,
            'lease_end_date': end,
            'artwork_file': placeholder,
            'description': 'Manual Booking on A',
        })
        self.face_a._compute_occupancy_status()
        self.assertEqual(self.face_a.occupancy_status, 'booked')

        # 2. Transfer from A to B (no sale order)
        wizard = self.TransferWizard.create({
            'transfer_type': 'no_sale_order',
            'source_face_id': self.face_a.id,
            'target_face_id_b': self.face_b.id,
            'client_id': self.partner.id,
            'start_date': start,
            'end_date': end,
        })
        wizard.action_transfer()

        # 3. Verify occupancy
        self.face_a._compute_occupancy_status()
        self.face_b._compute_occupancy_status()
        
        self.assertEqual(self.face_a.occupancy_status, 'available', "Source face should be available after transfer")
        self.assertEqual(self.face_b.occupancy_status, 'booked', "Target face should be booked after transfer")
        self.assertIn(history.id, self.face_a.transferred_out_history_ids.ids, "History record should be in transferred_out list")

    def test_transfer_vacate_sale_order(self):
        """ Test that transferring a Sale Order booking (inventory-only) vacates the source face """
        today = fields.Date.today()
        start = today
        end = today + relativedelta(days=10)

        # 1. Create Sale Order on Face A
        order = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face_a.product_id.id,
                'media_face_id': self.face_a.id,
                'start_date': start,
                'end_date': end,
                'price_unit': 1000,
            })]
        })
        order.action_confirm()
        
        self.face_a._compute_occupancy_status()
        self.assertEqual(self.face_a.occupancy_status, 'booked')

        # 2. Transfer from A to B (no sale order - inventory transfer)
        wizard = self.TransferWizard.create({
            'transfer_type': 'no_sale_order',
            'source_face_id': self.face_a.id,
            'target_face_id_b': self.face_b.id,
            'client_id': self.partner.id,
            'start_date': start,
            'end_date': end,
        })
        wizard.action_transfer()

        # 3. Verify occupancy
        self.face_a._compute_occupancy_status()
        self.face_b._compute_occupancy_status()
        
        self.assertEqual(self.face_a.occupancy_status, 'available', "Source face should be available after transfer")
        self.assertEqual(self.face_b.occupancy_status, 'booked', "Target face should be booked after transfer")
        self.assertIn(order.order_line[0].id, self.face_a.transferred_out_sol_ids.ids, "SOL should be in transferred_out list")
