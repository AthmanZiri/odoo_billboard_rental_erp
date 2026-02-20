from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class MediaDoohSlot(models.Model):
    _name = 'media.dooh.slot'
    _description = 'DOOH Slot'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Slot Name', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    digital_screen_id = fields.Many2one('media.digital.screen', string='Digital Screen', required=True, ondelete='cascade')
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
    
    ad_duration = fields.Integer(string='Ad Duration (sec)', default=15, help="Duration of the ad in seconds. Must be 15s.")
    is_expiring_soon = fields.Boolean(string='Expiring Soon', compute='_compute_expiry_status', store=True)

    @api.depends('end_date', 'state')
    def _compute_expiry_status(self):
        today = fields.Date.today()
        soon = today + relativedelta(days=5)
        for slot in self:
            slot.is_expiring_soon = (
                slot.state == 'booked' and 
                slot.end_date and 
                today <= slot.end_date <= soon
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
        if not self.partner_id:
            raise UserError(_("Please select a Client before creating a Sale Order."))
        if not self.digital_screen_id.product_id:
            raise UserError(_("The selected Digital Screen does not have a linked product for invoicing."))

        # Determine price based on pricing type
        screen = self.digital_screen_id
        price_unit = 0.0
        
        if screen.pricing_type == 'slot_monthly':
            price_unit = screen.price_slot_monthly
        elif screen.pricing_type == 'slot_biweekly':
            price_unit = screen.price_slot_biweekly
        elif screen.pricing_type == 'slot_weekly':
            price_unit = screen.price_slot_weekly
        elif screen.pricing_type == 'fixed':
            # Charge the full configured price per slot
            price_unit = screen.price_per_month
            
            # Adjust for billing frequency
            if self.billing_frequency == 'biweekly':
                price_unit /= 2.0
            elif self.billing_frequency == 'weekly':
                price_unit /= 4.0
        else:
            # Fallback or other pricing types
            price_unit = screen.price_per_month

        order_vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': [(0, 0, {
                'product_id': screen.product_id.id,
                'name': _("Digital Slot: %s | Screen: %s | SOV: %s%%") % (
                    self.name, screen.display_name, self.sov
                ),
                'product_uom_qty': 1.0,
                'price_unit': price_unit,
                'media_digital_screen_id': screen.id,
                'start_date': self.start_date, # Added back start_date
                'end_date': self.end_date,     # Added back end_date
            })],
        }
        order = self.env['sale.order'].create(order_vals)
        line = order.order_line[0] # Get the created line

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
            user_id = slot.sale_line_id.order_id.user_id or self.env.user
            slot.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today(),
                summary=_("Slot Expiring Soon: %s") % slot.name,
                note=_("The digital slot %s on screen %s is set to expire on %s (in 5 days).") % (
                    slot.name, slot.digital_screen_id.display_name, slot.end_date
                ),
                user_id=user_id.id
            )

