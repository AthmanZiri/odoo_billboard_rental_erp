from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields
from dateutil.relativedelta import relativedelta
import datetime

class TestDoohSlot(TransactionCase):

    def setUp(self):
        super(TestDoohSlot, self).setUp()
        self.Partner = self.env['res.partner']
        self.Screen = self.env['media.digital.screen']
        self.Slot = self.env['media.dooh.slot']
        self.Site = self.env['media.site']
        self.Product = self.env['product.product']

        # Setup basic data
        self.partner = self.Partner.create({'name': 'Test Client'})
        self.site = self.Site.create({'name': 'Test Site', 'code': 'TS'})
        
        self.product = self.Product.create({
            'name': 'Digital Screen Service',
            'type': 'service'
        })

        self.screen = self.Screen.create({
            'name': 'Digital Screen 1',
            'site_id': self.site.id,
            'price_per_month': 1000.0,
            'number_of_slots': 10,
            'product_id': self.product.id,
        })

    def test_slot_duration_constraint(self):
        """ Test that ad_duration must be 15s """
        with self.assertRaises(UserError):
            self.Slot.create({
                'digital_screen_id': self.screen.id,
                'ad_duration': 20,
                'partner_id': self.partner.id,
            })
        
        # Valid duration
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'ad_duration': 15,
            'partner_id': self.partner.id,
        })
        self.assertEqual(slot.ad_duration, 15)

    def test_billing_frequencies(self):
        """ Test sale order price calculation for different frequencies """
        # Monthly (default)
        slot_monthly = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'partner_id': self.partner.id,
            'billing_frequency': 'monthly',
        })
        action = slot_monthly.action_create_sale_order()
        order = self.env['sale.order'].browse(action['res_id'])
        # Price should be 1000 * (100/10) / 100 = 100
        self.assertEqual(order.order_line.price_unit, 100.0)

        # Weekly
        slot_weekly = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'partner_id': self.partner.id,
            'billing_frequency': 'weekly',
        })
        action_weekly = slot_weekly.action_create_sale_order()
        order_weekly = self.env['sale.order'].browse(action_weekly['res_id'])
        # Price should be 100 / 4 = 25
        self.assertEqual(order_weekly.order_line.price_unit, 25.0)

        # Bi-weekly
        slot_biweekly = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'partner_id': self.partner.id,
            'billing_frequency': 'biweekly',
        })
        action_biweekly = slot_biweekly.action_create_sale_order()
        order_biweekly = self.env['sale.order'].browse(action_biweekly['res_id'])
        # Price should be 100 / 2 = 50
        self.assertEqual(order_biweekly.order_line.price_unit, 50.0)

    def test_expiry_notification_cron(self):
        """ Test that the cron creates an activity for slots expiring in 5 days """
        expiry_date = fields.Date.today() + relativedelta(days=5)
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'partner_id': self.partner.id,
            'state': 'booked',
            'end_date': expiry_date,
        })
        
        # Mocking sale line to avoid errors in activity creation
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'media_digital_screen_id': self.screen.id,
        })
        slot.sale_line_id = line.id

        # Run cron
        self.Slot._cron_notify_expiring_slots()

        # Check for activity
        activity = self.env['mail.activity'].search([
            ('res_id', '=', slot.id),
            ('res_model', '=', 'media.dooh.slot')
        ])
        self.assertTrue(activity)
        self.assertIn("Slot Expiring Soon", activity.summary)

    def test_slot_creation_without_dates(self):
        """ Test that a slot can be created without partner and dates """
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'ad_duration': 15,
        })
        self.assertTrue(slot.id)
        self.assertFalse(slot.partner_id)
        self.assertFalse(slot.start_date)
        self.assertFalse(slot.end_date)
        self.assertEqual(slot.state, 'available')
