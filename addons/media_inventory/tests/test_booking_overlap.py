from odoo.tests.common import TransactionCase
from odoo import fields
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class TestBookingOverlap(TransactionCase):

    def setUp(self):
        super(TestBookingOverlap, self).setUp()
        self.Partner = self.env['res.partner']
        self.Face = self.env['media.face']
        self.Site = self.env['media.site']
        self.SO = self.env['sale.order']

        self.partner = self.Partner.create({'name': 'Test Client'})
        self.site = self.Site.create({'name': 'Test Site', 'code': 'TS'})
        self.face = self.Face.create({
            'name': 'Face 1',
            'site_id': self.site.id,
            'face_type': 'inbound',
        })

    def test_booking_touching_dates(self):
        """ Test that a new booking can start on the same day an old one ends """
        mar_1 = fields.Date.from_string('2026-03-01')
        mar_31 = fields.Date.from_string('2026-03-31')
        apr_30 = fields.Date.from_string('2026-04-30')

        # 1. Create first booking: Mar 1 to Mar 31
        order1 = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': mar_1,
                'end_date': mar_31,
            })]
        })
        order1.action_confirm()

        # 2. Try to create second booking: Mar 31 to Apr 30
        # This is expected to fail currently, but we want it to SUCCEED after our fix.
        try:
            order2 = self.SO.create({
                'partner_id': self.partner.id,
                'order_line': [(0, 0, {
                    'product_id': self.face.product_id.id,
                    'media_face_id': self.face.id,
                    'start_date': mar_31,
                    'end_date': apr_30,
                })]
            })
            # If we are here, it means it didn't raise ValidationError during create
            # (though the constraint might only trigger on write/flush if not carefully handled)
            # In Odoo, @api.constrains triggers on creation of the record in DB.
        except ValidationError:
            self.fail("ValidationError raised for touching dates (Mar 31 - Mar 31), but it should be allowed.")

    def test_booking_real_overlap(self):
        """ Test that a real overlap is still blocked """
        mar_1 = fields.Date.from_string('2026-03-01')
        mar_31 = fields.Date.from_string('2026-03-31')
        mar_30 = fields.Date.from_string('2026-03-30')
        apr_30 = fields.Date.from_string('2026-04-30')

        # 1. Create first booking: Mar 1 to Mar 31
        order1 = self.SO.create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': mar_1,
                'end_date': mar_31,
            })]
        })
        order1.action_confirm()

        # 2. Try to create second booking: Mar 30 to Apr 30 (1 day real overlap)
        with self.assertRaises(ValidationError):
            self.SO.create({
                'partner_id': self.partner.id,
                'order_line': [(0, 0, {
                    'product_id': self.face.product_id.id,
                    'media_face_id': self.face.id,
                    'start_date': mar_30,
                    'end_date': apr_30,
                })]
            })
