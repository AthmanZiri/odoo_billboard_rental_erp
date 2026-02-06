from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

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
    end_date = fields.Date(string='End Date', default=lambda self: fields.Date.today() + relativedelta(months=1))
    
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
    
    billing_frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly')
    ], string='Billing Frequency', default='monthly')

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

    def action_create_sale_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Please select a Client before creating a Sale Order."))
        if not self.face_id.product_id:
            raise UserError(_("The selected Billboard Face does not have a linked product for invoicing."))
        
        # Create Sale Order
        order_vals = {
            'partner_id': self.partner_id.id,
            'lease_start_date': self.start_date,
            'lease_end_date': self.end_date,
            'origin': self.name,
        }
        order = self.env['sale.order'].create(order_vals)
        
        # Calculate price based on SOV and frequency
        base_price = self.face_id.price_per_month
        sov_price = base_price * (self.sov / 100.0)
        
        if self.billing_frequency == 'weekly':
            sov_price = sov_price / 4.0
        elif self.billing_frequency == 'biweekly':
            sov_price = sov_price / 2.0
        
        # Create Order Line
        line_vals = {
            'order_id': order.id,
            'product_id': self.face_id.product_id.id,
            'media_face_id': self.face_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'price_unit': sov_price,
            'product_uom_qty': 1.0,
            'name': _("Digital Slot [%s] on Face %s (SOV: %s%%)") % (self.name, self.face_id.display_name, self.sov),
        }
        line = self.env['sale.order.line'].create(line_vals)
        
        self.sale_line_id = line.id
        self.state = 'reserved'
        
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
