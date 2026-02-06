from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import datetime

class MediaFace(models.Model):
    _name = 'media.face'
    _description = 'Media Face/Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Face Name', required=True, tracking=True)
    code = fields.Char(string='Face Code', tracking=True)
    
    site_id = fields.Many2one('media.site', string='Site', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Linked Product', help='Product used for invoicing this face', ondelete='restrict')
    
    face_type = fields.Selection([
        ('inbound', 'Inbound Face'),
        ('outbound', 'Outbound Face'),
        ('digital', 'Digital Face'),
        ('fascia_north', 'Fascia North'),
        ('fascia_south', 'Fascia South'),
        ('fascia_east', 'Fascia East'),
        ('fascia_west', 'Fascia West')
    ], string='Face Type', required=True)
    
    # Technical Specs
    height = fields.Float(string='Height (m)')
    width = fields.Float(string='Width (m)')
    illumination_type = fields.Selection([
        ('backlit', 'Backlit'),
        ('frontlit', 'Frontlit'),
        ('unlit', 'Unlit'),
        ('led', 'LED/Digital')
    ], string='Illumination')
    
    # Digital Specs (Specific to Digital Type)
    pixel_pitch = fields.Char(string='Pixel Pitch')
    resolution = fields.Char(string='Resolution (WxH)')
    refresh_rate = fields.Char(string='Refresh Rate')
    supported_formats = fields.Char(string='Supported Formats', help='e.g., MP4, JPG, PNG')
    
    # Pricing
    pricing_type = fields.Selection([
        ('fixed', 'Fixed (Monthly)'),
        ('daily', 'Daily'),
        ('cpm', 'CPM (Cost Per Mille)'),
        ('dynamic', 'Dynamic (Traffic Based)')
    ], string='Pricing Type', default='fixed')
    
    price_per_month = fields.Float(string='Price per Month')
    price_per_day = fields.Float(string='Price per Day')
    cpm_rate = fields.Float(string='CPM Rate')
    
    estimated_monthly_impressions = fields.Integer(string='Est. Monthly Impressions')
    
    active = fields.Boolean(default=True)
    lease_line_ids = fields.One2many('sale.order.line', 'media_face_id', string='Lease Lines')
    expense_ids = fields.One2many('media.expense', 'media_face_id', string='Expenses')
    
    occupancy_status = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('maintenance', 'Maintenance')
    ], string='Occupancy Status', compute='_compute_occupancy_status', store=True, default='available')

    next_available_date = fields.Date(string='Available From', compute='_compute_next_available_date', store=True)
    current_booking_start = fields.Date(string='Booking Start', compute='_compute_current_booking_dates', store=True)
    current_booking_end = fields.Date(string='Booking End', compute='_compute_current_booking_dates', store=True)
    
    is_soon_available = fields.Boolean(compute='_compute_status_flags', store=True)
    is_expired = fields.Boolean(compute='_compute_status_flags', store=True)
    is_reserved = fields.Boolean(compute='_compute_status_flags', store=True)

    @api.depends('lease_line_ids.state', 'lease_line_ids.start_date', 'lease_line_ids.end_date')
    def _compute_current_booking_dates(self):
        today = fields.Date.today()
        for record in self:
            active_lease = record.lease_line_ids.filtered(lambda l: 
                l.state in ['sale', 'done'] and 
                l.start_date and l.end_date and
                l.start_date <= today <= l.end_date
            ).sorted(key=lambda l: l.end_date, reverse=True)
            
            if active_lease:
                record.current_booking_start = active_lease[0].start_date
                record.current_booking_end = active_lease[0].end_date
            else:
                record.current_booking_start = False
                record.current_booking_end = False

    @api.depends('occupancy_status', 'current_booking_end', 'lease_line_ids.state')
    def _compute_status_flags(self):
        today = fields.Date.today()
        soon = today + relativedelta(days=30)
        for record in self:
            record.is_soon_available = record.occupancy_status == 'booked' and record.current_booking_end and record.current_booking_end <= soon
            record.is_expired = record.current_booking_end and record.current_booking_end < today
            record.is_reserved = any(l.state == 'draft' for l in record.lease_line_ids)

    @api.depends('lease_line_ids.end_date', 'lease_line_ids.state')
    def _compute_next_available_date(self):
        today = fields.Date.today()
        for record in self:
            future_rentals = record.lease_line_ids.filtered(lambda l: 
                l.state in ['sale', 'done'] and 
                l.end_date and l.end_date >= today
            ).sorted(key=lambda l: l.end_date, reverse=True)
            
            if future_rentals:
                record.next_available_date = future_rentals[0].end_date + relativedelta(days=1)
            else:
                record.next_available_date = today

    @api.depends('name', 'code', 'site_id', 'next_available_date')
    def _compute_display_name(self):
        today = fields.Date.today()
        for record in self:
            name = record.name
            if record.code:
                name = "[%s] %s" % (record.code, name)
            if record.site_id:
                site_name = record.site_id.code or record.site_id.name
                name = "%s / %s" % (site_name, name)
            
            # Show availability info if booked in the future
            if record.next_available_date and record.next_available_date > today:
                # Find the current/last rental end date
                last_line = record.lease_line_ids.filtered(lambda l: l.state in ['sale', 'done'] and l.end_date >= today).sorted(key=lambda l: l.end_date, reverse=True)
                if last_line:
                    name += " (Booked until: %s)" % last_line[0].end_date.strftime('%b %d')
            
            record.display_name = name


    @api.model_create_multi
    def create(self, vals_list):
        records = super(MediaFace, self).create(vals_list)
        for record in records:
            record._sync_product()
        return records

    def write(self, vals):
        res = super(MediaFace, self).write(vals)
        if any(f in vals for f in ['name', 'code', 'site_id', 'price_per_month', 'price_per_day']):
            for record in self:
                record._sync_product()
        return res

    def _sync_product(self):
        self.ensure_one()
        product_name = self.name
        if self.site_id:
            product_name = "%s / %s" % (self.site_id.name, self.name)
        
        product_vals = {
            'name': product_name,
            'list_price': self.price_per_month or self.price_per_day or 0.0,
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'default_code': self.code or (self.site_id.code if self.site_id else False),
        }
        
        if not self.product_id:
            product = self.env['product.product'].create(product_vals)
            self.product_id = product.id
        else:
            self.product_id.write(product_vals)

    @api.depends('active', 'lease_line_ids.state', 'lease_line_ids.start_date', 'lease_line_ids.end_date')
    def _compute_occupancy_status(self):
        today = fields.Date.today()
        for record in self:
            # Find any active lease line covering today
            active_lease = record.lease_line_ids.filtered(lambda l: 
                l.state in ['sale', 'done'] and 
                l.start_date and l.end_date and
                l.start_date <= today <= l.end_date
            )
            record.occupancy_status = 'booked' if active_lease else 'available'
    
    @api.onchange('face_type')
    def _onchange_face_type(self):
        if self.face_type == 'digital':
            self.illumination_type = 'led'
