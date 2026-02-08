from odoo import models, fields, api

class MediaFace(models.Model):
    _inherit = 'media.face'

    loop_duration = fields.Integer(string='Loop Duration (sec)', compute='_compute_loop_duration', store=True)
    slot_duration = fields.Integer(string='Slot Duration (sec)', default=15)
    number_of_slots = fields.Integer(string='Number of Slots', default=10)
    slot_ids = fields.One2many('media.dooh.slot', 'face_id', string='Digital Slots')
    
    @api.depends('slot_duration', 'number_of_slots')
    def _compute_loop_duration(self):
        for face in self:
            face.loop_duration = face.slot_duration * face.number_of_slots
    
    occupied_slots = fields.Integer(string='Occupied Slots', compute='_compute_slot_counts_and_views', store=True)
    available_slots = fields.Integer(string='Available Slots', compute='_compute_slot_counts_and_views', store=True)
    slot_count = fields.Integer(compute='_compute_slot_counts_and_views')


    @api.depends('slot_ids.state', 'number_of_slots', 'operating_hours_start', 'operating_hours_end', 'slot_duration')
    def _compute_slot_counts_and_views(self):
        for face in self:
            occupied = len(face.slot_ids.filtered(lambda s: s.state == 'booked'))
            face.occupied_slots = occupied
            face.available_slots = face.number_of_slots - occupied
            face.slot_count = len(face.slot_ids)

            # Computing views_per_day here to stay consistent with dependencies
            if face.face_type == 'digital':
                duration_hours = face.operating_hours_end - face.operating_hours_start
                if duration_hours > 0:
                    total_seconds = duration_hours * 3600
                    loop_duration = face.slot_duration * face.number_of_slots
                    face.views_per_day = int(total_seconds / loop_duration) if loop_duration > 0 else 0
                else:
                    face.views_per_day = 0
            else:
                face.views_per_day = 0

    def action_view_slots(self):
        self.ensure_one()
        return {
            'name': 'Digital Slots',
            'type': 'ir.actions.act_window',
            'res_model': 'media.dooh.slot',
            'view_mode': 'list,form',
            'domain': [('face_id', '=', self.id)],
            'context': {'default_face_id': self.id},
        }


