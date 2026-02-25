from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_cancel(self):
        # 1. Collect all related assets before cancellation for targeted recomputation
        # Face IDs from order lines
        face_ids = self.order_line.mapped('media_face_id').ids
        # Slot IDs from order lines
        slot_ids = self.order_line.mapped('media_slot_id').ids
        # Digital Screen IDs from order lines
        screen_ids = self.order_line.mapped('media_digital_screen_id').ids
        
        # 2. Cancel related media rentals
        rentals = self.env['media.rental'].sudo().search([('sale_order_id', 'in', self.ids)])
        if rentals:
            rentals.write({'state': 'cancel'})

        # 3. Perform the standard cancellation
        res = super(SaleOrder, self).action_cancel()

        # 4. Trigger recomputations for occupancy and availability statuses
        if face_ids:
            faces = self.env['media.face'].browse(face_ids)
            faces.modified(['occupancy_status', 'current_booking_start', 'current_booking_end', 'next_available_date', 'is_reserved'])
        
        if slot_ids:
            slots = self.env['media.dooh.slot'].browse(slot_ids)
            slots.modified(['state', 'is_expiring_soon'])
            
        if screen_ids:
            screens = self.env['media.digital.screen'].browse(screen_ids)
            screens.modified(['occupied_slots', 'available_slots'])

        return res
