from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class MediaDoohSlot(models.Model):
    _name = 'media.dooh.slot'
    _description = 'DOOH Slot'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Slot Name', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    digital_screen_id = fields.Many2one('media.digital.screen', string='Digital Screen', required=True, ondelete='cascade')
    sale_line_ids = fields.One2many('sale.order.line', 'media_slot_id', string='Lease Lines')
    
    version_ids = fields.One2many('media.dooh.content.version', 'slot_id', string='Creative Versions')
    
    @api.depends('name', 'digital_screen_id.name')
    def _compute_display_name(self):
        for slot in self:
            if slot.digital_screen_id:
                slot.display_name = "%s - %s" % (slot.digital_screen_id.name, slot.name)
            else:
                slot.display_name = slot.name
    
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked')
    ], string='Status', compute='_compute_current_booking', store=True, default='available', tracking=True)
    
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
    
    ad_duration = fields.Integer(string='Ad Duration (sec)', default=15, help="Duration of the ad in seconds. Must be 15s.")
    is_expiring_soon = fields.Boolean(string='Expiring Soon', compute='_compute_expiry_status', store=True)

    @api.depends('sale_line_ids.state', 'sale_line_ids.start_date', 'sale_line_ids.end_date')
    def _compute_current_booking(self):
        today = fields.Date.today()
        for slot in self:
            # Check for active bookings
            active_booking = slot.sale_line_ids.filtered(lambda l: 
                l.state in ['sale', 'done'] and 
                l.start_date and l.end_date and
                l.start_date <= today <= l.end_date
            )
            if active_booking:
                slot.state = 'booked'
                continue

            # Check for reserved bookings
            reserved_booking = slot.sale_line_ids.filtered(lambda l: 
                l.state in ['draft', 'sent'] and 
                l.start_date and l.end_date and
                l.start_date <= today <= l.end_date
            )
            if reserved_booking:
                slot.state = 'reserved'
            else:
                slot.state = 'available'

    @api.depends('sale_line_ids.state', 'sale_line_ids.end_date')
    def _compute_expiry_status(self):
        today = fields.Date.today()
        soon = today + relativedelta(days=5)
        for slot in self:
            # Find the end date of the *current* active booking
            active_line = slot.sale_line_ids.filtered(lambda l: 
                l.state in ['sale', 'done'] and 
                l.start_date and l.end_date and
                l.start_date <= today <= l.end_date
            ).sorted(key=lambda l: l.end_date, reverse=True)
            
            end_date = active_line[0].end_date if active_line else False
            slot.is_expiring_soon = (
                slot.state == 'booked' and 
                end_date and 
                today <= end_date <= soon
            )

    @api.constrains('ad_duration')

    def _check_ad_duration(self):
        for slot in self:
            if slot.ad_duration != 15:
                raise UserError(_("Ad duration must be exactly 15 seconds."))


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('media.dooh.slot') or 'New'
        return super(MediaDoohSlot, self).create(vals_list)

    @api.depends('digital_screen_id.number_of_slots')
    def _compute_sov(self):
        for slot in self:
            if slot.digital_screen_id.number_of_slots > 0:
                slot.sov = 100.0 / slot.digital_screen_id.number_of_slots
            else:
                slot.sov = 0.0

    def action_create_sale_order(self):
        self.ensure_one()
        order_vals = {
            'origin': self.name,
            'order_line': [(0, 0, {
                'product_id': screen.product_id.id,
                'name': _("Digital Slot: %s | Screen: %s | SOV: %s%%") % (
                    self.name, screen.display_name, self.sov
                ),
                'product_uom_qty': 1.0,
                'price_unit': price_unit,
                'media_digital_screen_id': screen.id,
                'media_slot_id': self.id,
            })],
        }
        order = self.env['sale.order'].create(order_vals)
        
        return {
            'name': _('Sale Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _cron_notify_expiring_slots(self):
        """ Notify users about slots expiring in 5 days """
        expiry_date = fields.Date.today() + relativedelta(days=5)
        expiring_slots = self.search([
            ('state', '=', 'booked'),
            ('end_date', '=', expiry_date)
        ])
        
        for slot in expiring_slots:
            # Create a mail activity for the salesperson or a default manager
            # Find the active sale line covering today to get the salesperson
            today = fields.Date.today()
            active_line = slot.sale_line_ids.filtered(lambda l: l.state in ['sale', 'done'] and l.start_date <= today <= l.end_date).sorted(key=lambda l: l.end_date, reverse=True)
            user_id = active_line[0].order_id.user_id if active_line else self.env.user
            end_date = active_line[0].end_date if active_line else False
            
            slot.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today(),
                summary=_("Slot Expiring Soon: %s") % slot.name,
                note=_("The digital slot %s on screen %s is set to expire on %s (in 5 days).") % (
                    slot.name, slot.digital_screen_id.display_name, end_date
                ),
                user_id=user_id.id
            )

