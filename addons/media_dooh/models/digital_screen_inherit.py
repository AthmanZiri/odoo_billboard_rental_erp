from odoo import models, fields, api

class MediaDigitalScreen(models.Model):
    _inherit = 'media.digital.screen'

    loop_duration = fields.Integer(string='Loop Duration (sec)', compute='_compute_loop_duration', store=True)
    slot_duration = fields.Integer(string='Slot Duration (sec)', default=15)
    
    slot_ids = fields.One2many('media.dooh.slot', 'digital_screen_id', string='Digital Slots')
    order_line_ids = fields.One2many('sale.order.line', 'media_digital_screen_id', string='Order History')
    
    @api.depends('slot_duration', 'number_of_slots')
    def _compute_loop_duration(self):
        for screen in self:
            screen.loop_duration = screen.slot_duration * screen.number_of_slots

    def _set_number_of_slots(self):
        """ Automatically create or remove slots based on number_of_slots field """
        for screen in self:
            current_slots = screen.slot_ids
            target_count = screen.number_of_slots
            current_count = len(current_slots)
            
            if target_count > current_count:
                # Create more slots
                slots_to_create = []
                for i in range(current_count + 1, target_count + 1):
                    slots_to_create.append({
                        'digital_screen_id': screen.id,
                        'name': 'New',
                    })
                if slots_to_create:
                    self.env['media.dooh.slot'].create(slots_to_create)
            
            elif target_count < current_count:
                # Remove extra available slots to match target
                # Prioritize removing available ones from the end
                diff = current_count - target_count
                available_slots = current_slots.filtered(lambda s: s.state == 'available').sorted(key=lambda s: s.id, reverse=True)
                
                slots_to_unlink = available_slots[:diff]
                slots_to_unlink.unlink()
    
    occupied_slots = fields.Integer(string='Occupied Slots', compute='_compute_slot_counts_and_views', store=True)
    available_slots = fields.Integer(string='Available Slots', compute='_compute_slot_counts_and_views', store=True)
    slot_count = fields.Integer(compute='_compute_slot_counts_and_views', store=True)

    @api.depends('slot_ids.state', 'number_of_slots', 'operating_hours_start', 'operating_hours_end', 'slot_duration')
    def _compute_slot_counts_and_views(self):
        for screen in self:
            occupied = len(screen.slot_ids.filtered(lambda s: s.state == 'booked'))
            screen.occupied_slots = occupied
            screen.available_slots = screen.number_of_slots - occupied
            screen.slot_count = len(screen.slot_ids)

            duration_hours = screen.operating_hours_end - screen.operating_hours_start
            if duration_hours > 0:
                total_seconds = duration_hours * 3600
                loop_duration = screen.slot_duration * screen.number_of_slots
                screen.views_per_day = int(total_seconds / loop_duration) if loop_duration > 0 else 0
            else:
                screen.views_per_day = 0

    def action_view_slots(self):
        self.ensure_one()
        return {
            'name': 'Digital Slots',
            'type': 'ir.actions.act_window',
            'res_model': 'media.dooh.slot',
            'view_mode': 'list,form',
            'domain': [('digital_screen_id', '=', self.id)],
            'context': {'default_digital_screen_id': self.id},
        }
