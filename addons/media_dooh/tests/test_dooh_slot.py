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
            })
        
        # Valid duration
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'ad_duration': 15,
        })
        self.assertEqual(slot.ad_duration, 15)

    def test_dynamic_status_computation(self):
        """ Test that slot status changes based on SO lines """
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'ad_duration': 15,
        })
        self.assertEqual(slot.state, 'available')

        # Create a draft SO line
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        today = fields.Date.today()
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'media_slot_id': slot.id,
            'start_date': today,
            'end_date': today + relativedelta(days=1),
        })
        
        slot._compute_current_booking()
        self.assertEqual(slot.state, 'reserved')

        # Confirm the SO
        order.action_confirm()
        slot._compute_current_booking()
        self.assertEqual(slot.state, 'booked')

    def test_expiry_notification_cron(self):
        """ Test that the cron creates an activity for slots expiring in 5 days """
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'ad_duration': 15,
        })
        
        today = fields.Date.today()
        expiry_date = today + relativedelta(days=5)
        
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'media_slot_id': slot.id,
            'start_date': today - relativedelta(days=2),
            'end_date': expiry_date,
        })
        order.action_confirm()
        
        slot._compute_current_booking()
        slot._compute_expiry_status()
        self.assertEqual(slot.state, 'booked')
        self.assertTrue(slot.is_expiring_soon)

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
        """ Test that a slot can be created cleanly """
        slot = self.Slot.create({
            'digital_screen_id': self.screen.id,
            'ad_duration': 15,
        })
        self.assertTrue(slot.id)
        self.assertEqual(slot.state, 'available')
