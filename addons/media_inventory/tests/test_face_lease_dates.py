from odoo.tests.common import TransactionCase
from odoo import fields
from dateutil.relativedelta import relativedelta

class TestFaceLeaseDates(TransactionCase):

    def setUp(self):
        super(TestFaceLeaseDates, self).setUp()
        self.Partner = self.env['res.partner']
        self.Face = self.env['media.face']
        self.Site = self.env['media.site']
        self.SO = self.env['sale.order']
        self.ArtworkHistory = self.env['media.artwork.history']

        self.partner = self.Partner.create({'name': 'Test Client'})
        self.site = self.Site.create({'name': 'Test Site', 'code': 'TS'})
        self.face = self.Face.create({
            'name': 'Face 1',
            'site_id': self.site.id,
            'face_type': 'inbound',
        })

    def test_lease_dates_computation(self):
        """ Test that latest_lease_start_date and latest_lease_end_date are correctly computed """
        today = fields.Date.today()
        
        # 1. No leases initially
        self.face._compute_latest_lease_dates()
        self.assertFalse(self.face.latest_lease_start_date)
        self.assertFalse(self.face.latest_lease_end_date)

        # 2. Add an artwork history (manual booking)
        start1 = today - relativedelta(months=1)
        end1 = today - relativedelta(days=1)
        self.ArtworkHistory.create({
            'face_id': self.face.id,
            'lease_start_date': start1,
            'lease_end_date': end1,
            'description': 'Past Manual Booking',
        })
        self.face._compute_latest_lease_dates()
        self.assertEqual(self.face.latest_lease_start_date, start1)
        self.assertEqual(self.face.latest_lease_end_date, end1)

        # 3. Add a more recent Sale Order lease
        start2 = today
        end2 = today + relativedelta(months=1)
        order = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': start2,
                'end_date': end2,
            })]
        })
        # Dates should not update yet because SO is draft
        self.face._compute_latest_lease_dates()
        self.assertEqual(self.face.latest_lease_start_date, start1)
        
        # Confirm SO
        order.action_confirm()
        self.face._compute_latest_lease_dates()
        self.assertEqual(self.face.latest_lease_start_date, start2)
        self.assertEqual(self.face.latest_lease_end_date, end2)

        # 4. Add a future lease
        start3 = today + relativedelta(months=2)
        end3 = today + relativedelta(months=3)
        order2 = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': start3,
                'end_date': end3,
            })]
        })
        order2.action_confirm()
        self.face._compute_latest_lease_dates()
        self.assertEqual(self.face.latest_lease_start_date, start3)
        self.assertEqual(self.face.latest_lease_end_date, end3)

    def test_face_booked_when_future_sale_order_exists(self):
        """Occupancy must be booked if a confirmed line covers a future period (not only 'today')."""
        today = fields.Date.today()
        start = today + relativedelta(months=1)
        end = today + relativedelta(months=2)
        order = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': start,
                'end_date': end,
                'price_unit': 1000,
            })],
        })
        order.action_confirm()
        self.face._compute_occupancy_status()
        self.assertEqual(self.face.occupancy_status, 'booked')

    def test_overlapping_sol_ignores_transferred_out_line(self):
        """A sale line marked transferred out must not block new bookings on that face."""
        today = fields.Date.today()
        start = today
        end = today + relativedelta(days=20)
        order = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': start,
                'end_date': end,
                'price_unit': 1000,
            })],
        })
        order.action_confirm()
        sol = order.order_line[0]
        self.face.sudo().write({
            'transferred_out_sol_ids': [(4, sol.id)],
        })
        order2 = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': start,
                'end_date': end,
                'price_unit': 1000,
            })],
        })
        # Should not raise: transferred line is excluded from overlap
        order2.action_confirm()
