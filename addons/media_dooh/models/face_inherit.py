from odoo import models, fields, api

class MediaFace(models.Model):
    _inherit = 'media.face'

    loop_duration = fields.Integer(string='Loop Duration (sec)', default=60)
    number_of_slots = fields.Integer(string='Number of Slots', default=6)
    slot_ids = fields.One2many('media.dooh.slot', 'face_id', string='Digital Slots')
    
    occupied_slots = fields.Integer(string='Occupied Slots', compute='_compute_slot_counts')
    available_slots = fields.Integer(string='Available Slots', compute='_compute_slot_counts')
    
    @api.depends('slot_ids.state')
    def _compute_slot_counts(self):
        for face in self:
            occupied = len(face.slot_ids.filtered(lambda s: s.state == 'booked'))
            face.occupied_slots = occupied
            face.available_slots = face.number_of_slots - occupied
