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
    
    occupied_slots = fields.Integer(string='Occupied Slots', compute='_compute_slot_counts')
    available_slots = fields.Integer(string='Available Slots', compute='_compute_slot_counts')
    
    @api.depends('slot_ids.state')
    def _compute_slot_counts(self):
        for face in self:
            occupied = len(face.slot_ids.filtered(lambda s: s.state == 'booked'))
            face.occupied_slots = occupied
            face.available_slots = face.number_of_slots - occupied
