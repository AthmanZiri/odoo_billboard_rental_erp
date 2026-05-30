from odoo.tests.common import TransactionCase
from odoo import fields
from dateutil.relativedelta import relativedelta


class TestMediaReserveInventory(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Face = self.env['media.face']
        self.Site = self.env['media.site']
        self.SO = self.env['sale.order']
        self.site = self.Site.create({'name': 'Reserve Site', 'code': 'RS'})
        self.face = self.Face.create({
            'name': 'Reserve Face',
            'site_id': self.site.id,
            'face_type': 'inbound',
        })
        self.partner = self.env['res.partner'].create({'name': 'Reserve Client'})

    def test_draft_quotation_does_not_reserve_by_default(self):
        today = fields.Date.today()
        order = self.SO.create({
            'partner_id': self.partner.id,
            'media_reserve_inventory': False,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': today,
                'end_date': today + relativedelta(months=1),
            })],
        })
        self.face._compute_occupancy_status()
        self.assertEqual(self.face.occupancy_status, 'available')

    def test_draft_quotation_reserves_when_enabled(self):
        today = fields.Date.today()
        self.SO.create({
            'partner_id': self.partner.id,
            'media_reserve_inventory': True,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': today,
                'end_date': today + relativedelta(months=1),
            })],
        })
        self.face._compute_occupancy_status()
        self.assertEqual(self.face.occupancy_status, 'reserved')

    def test_reservation_date_from_quotation(self):
        today = fields.Date.today()
        order = self.SO.create({
            'partner_id': self.partner.id,
            'media_reserve_inventory': True,
            'order_line': [(0, 0, {
                'product_id': self.face.product_id.id,
                'media_face_id': self.face.id,
                'start_date': today,
                'end_date': today + relativedelta(months=1),
            })],
        })
        self.face._compute_reservation_info()
        self.assertEqual(self.face.reservation_date, fields.Date.to_date(order.date_order))
        self.assertEqual(self.face.reserved_partner_id, self.partner)
