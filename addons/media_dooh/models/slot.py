from odoo import models, fields, api

class MediaDoohSlot(models.Model):
    _name = 'media.dooh.slot'
    _description = 'DOOH Slot'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Slot Name', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    face_id = fields.Many2one('media.face', string='Face', required=True, ondelete='cascade', domain=[('face_type', '=', 'digital')])
    partner_id = fields.Many2one('res.partner', string='Client')
    sale_line_id = fields.Many2one('sale.order.line', string='Lease Line', ondelete='set null')
    
    version_ids = fields.One2many('media.dooh.content.version', 'slot_id', string='Creative Versions')
    
    start_date = fields.Date(string='Start Date', default=fields.Date.today)
    end_date = fields.Date(string='End Date', default=lambda self: fields.Date.add(fields.Date.today(), months=1))
    
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked')
    ], string='Status', default='available', tracking=True)
    
    sov = fields.Float(string='Share of Voice (%)', compute='_compute_sov', store=True)
    
    content_file = fields.Binary(string='Creative File')
    content_filename = fields.Char(string='Creative Filename')
    content_type = fields.Selection([
        ('image', 'Image'),
        ('video', 'Video')
    ], string='Content Type', default='image')
    
    play_start_time = fields.Float(string='Play Start Time', default=0.0, help="e.g. 20.0 for 8:00 PM")
    play_end_time = fields.Float(string='Play End Time', default=23.99)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('media.dooh.slot') or 'New'
        return super(MediaDoohSlot, self).create(vals_list)

    @api.depends('face_id.number_of_slots')
    def _compute_sov(self):
        for slot in self:
            if slot.face_id.number_of_slots > 0:
                slot.sov = 100.0 / slot.face_id.number_of_slots
            else:
                slot.sov = 0.0
