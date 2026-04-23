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

    def test_transfer_via_sale_order_vacates_source_with_linked_artwork_history(self):
        """Artwork / booking log rows linked to the same SOL must be transferred out on the source, or occupancy stays booked."""
        today = fields.Date.today()
        start = today
        end = today + relativedelta(days=10)
        line = {
            'product_id': self.face_a.product_id.id,
            'media_face_id': self.face_a.id,
            'start_date': start,
            'end_date': end,
            'price_unit': 1000,
        }
        order = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, line)],
        })
        order.action_confirm()
        sol = order.order_line[0]
        TRANSPARENT_1PX = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        placeholder = base64.b64encode(TRANSPARENT_1PX)
        hist = self.ArtworkHistory.create({
            'face_id': self.face_a.id,
            'partner_id': self.partner.id,
            'lease_start_date': start,
            'lease_end_date': end,
            'sale_order_line_id': sol.id,
            'artwork_file': placeholder,
            'description': 'Contract log mirroring SO',
        })
        self.face_a._compute_occupancy_status()
        self.assertEqual(self.face_a.occupancy_status, 'booked')

        wizard = self.TransferWizard.create({
            'transfer_type': 'sale_order',
            'source_line_id': sol.id,
            'target_face_id': self.face_b.id,
        })
        wizard.action_transfer()

        self.face_a._compute_occupancy_status()
        self.face_b._compute_occupancy_status()
        self.assertEqual(self.face_a.occupancy_status, 'available')
        self.assertIn(sol.id, self.face_a.transferred_out_sol_ids.ids)
        self.assertIn(hist.id, self.face_a.transferred_out_history_ids.ids)

    def test_transfer_sale_order_uses_history_when_line_dates_empty(self):
        """If the SOL has no start/end, lease window comes from linked booking log rows."""
        today = fields.Date.today()
        start = today
        end = today + relativedelta(days=10)
        order = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face_a.product_id.id,
                'media_face_id': self.face_a.id,
                'price_unit': 1000,
            })],
        })
        order.action_confirm()
        sol = order.order_line[0]
        self.assertFalse(sol.start_date and sol.end_date, "line should have empty dates in this test")
        TRANSPARENT_1PX = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        placeholder = base64.b64encode(TRANSPARENT_1PX)
        self.ArtworkHistory.create({
            'face_id': self.face_a.id,
            'partner_id': self.partner.id,
            'lease_start_date': start,
            'lease_end_date': end,
            'sale_order_line_id': sol.id,
            'artwork_file': placeholder,
            'description': 'Dates only on log',
        })
        w = self.TransferWizard.create({
            'transfer_type': 'sale_order',
            'source_line_id': sol.id,
            'target_face_id': self.face_b.id,
        })
        win_s, win_e = w._get_lease_window_for_sale_line(sol)
        self.assertEqual((win_s, win_e), (start, end))
        w.action_transfer()
        on_b = self.env['media.artwork.history'].search([
            ('face_id', '=', self.face_b.id),
            ('sale_order_line_id', '=', sol.id),
            ('lease_start_date', '=', start),
            ('lease_end_date', '=', end),
        ])
        self.assertTrue(on_b, "Target should get a transfer log using inferred dates from booking log")

    def test_transfer_partial_target_overlap(self):
        """When the target is already booked for part of the window, use only the free remainder on the target."""
        today = fields.Date.today()
        # Target face (B) is fully booked for the first 21 days; source (A) wants a wider window
        # overlapping that commitment.
        block_start, block_end = today, today + relativedelta(days=20)
        req_start, req_end = today + relativedelta(days=5), today + relativedelta(days=30)
        # Expected free segment on B within [req_start, req_end]: the day after block_end through req_end
        expect_transfer_start = block_end + relativedelta(days=1)
        expect_transfer_end = req_end

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

        TRANSPARENT_1PX = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        placeholder = base64.b64encode(TRANSPARENT_1PX)
        self.ArtworkHistory.create({
            'face_id': self.face_a.id,
            'partner_id': self.partner.id,
            'lease_start_date': req_start,
            'lease_end_date': req_end,
            'artwork_file': placeholder,
            'description': 'Source booking on A',
        })

        wizard = self.TransferWizard.create({
            'transfer_type': 'no_sale_order',
            'source_face_id': self.face_a.id,
            'target_face_id_b': self.face_b.id,
            'client_id': self.partner.id,
            'start_date': req_start,
            'end_date': req_end,
        })
        segs = wizard._effective_transfer_segments(
            self.face_b, req_start, req_end, exclude_line=None
        )
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0], (expect_transfer_start, expect_transfer_end))

        wizard.action_transfer()
        on_b = self.ArtworkHistory.search([
            ('face_id', '=', self.face_b.id),
            ('lease_start_date', '=', expect_transfer_start),
            ('lease_end_date', '=', expect_transfer_end),
        ])
        self.assertEqual(
            len(on_b), 1,
            "Target face should have one artwork history for the free remainder of the period only.",
        )
