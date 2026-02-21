from odoo import models, fields, api, _

class MediaDigitalScreen(models.Model):
    _name = 'media.digital.screen'
    _description = 'Digital Screen Asset'
    _inherits = {'media.site': 'site_id'}
    _inherit = ['media.site.mixin', 'mail.thread', 'mail.activity.mixin']

    site_id = fields.Many2one('media.site', string='Base Site', required=True, ondelete='cascade')

    # Digital Specs
    pixel_pitch = fields.Char(string='Pixel Pitch')
    resolution = fields.Char(string='Resolution (WxH)')
    refresh_rate = fields.Char(string='Refresh Rate')
    supported_formats = fields.Char(string='Supported Formats', help='e.g., MP4, JPG, PNG')
    
    # Professional Specs
    operating_hours_start = fields.Float(string='Operating Hours Start', default=5.5, help="e.g. 5.5 for 5:30 AM")
    operating_hours_end = fields.Float(string='Operating Hours End', default=23.5, help="e.g. 23.5 for 11:30 PM")
    views_per_day = fields.Integer(string='Views per Day', default=0)
    orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape')
    ], string='Orientation', default='portrait')
    content_size_rec = fields.Char(string='Recommended Content Size', default='768 x 960')
    target_audience = fields.Text(string='Target Audience')

    # Pricing (Delegated to the underlying Face usually, but we keep it here for easy editing)
    # We will sync these to the underlying face.
    pricing_type = fields.Selection([
        ('fixed', 'Fixed (Monthly)'),
        ('daily', 'Daily'),
        ('slot_monthly', 'Price per Slot (Monthly)'),
        ('slot_biweekly', 'Price per Slot (Bi-weekly)'),
        ('slot_weekly', 'Price per Slot (Weekly)'),
        ('cpm', 'CPM (Cost Per Mille)'),
        ('dynamic', 'Dynamic (Traffic Based)')
    ], string='Pricing Type', default='fixed')
    
    price_per_month = fields.Float(string='Price per Month')
    price_per_day = fields.Float(string='Price per Day')
    cpm_rate = fields.Float(string='CPM Rate')

    # Dimensions (Can override site mixin or just use them)
    height = fields.Float(string='Height (m)')
    width = fields.Float(string='Width (m)')
    
    image_1 = fields.Image(string='Screen Image')

    product_id = fields.Many2one('product.product', string='Linked Product', help='Product used for invoicing this screen', ondelete='restrict')
    number_of_slots = fields.Integer(string='Number of Slots', default=6, inverse='_set_number_of_slots')

    def _set_number_of_slots(self):
        # This will be implemented in media_dooh to handle slot creation/removal
        pass

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['site_category'] = 'billboard' # or 'digital' if we added it to selection, but billboard is fine for now as general category
            if vals.get('name', 'New') == 'New':
                 vals['name'] = self.env['ir.sequence'].next_by_code('media.digital.screen') or 'New'
        
        screens = super(MediaDigitalScreen, self).create(vals_list)
        for screen in screens:
            screen._sync_product()
            
        return screens

    def write(self, vals):
        res = super(MediaDigitalScreen, self).write(vals)
        if any(f in vals for f in ['name', 'code', 'price_per_month', 'price_per_day']):
            for record in self:
                record._sync_product()
        return res

    def _sync_product(self):
        self.ensure_one()
        product_name = self.name
        
        product_vals = {
            'name': product_name,
            'list_price': self.price_per_month or self.price_per_day or 0.0,
            'type': 'service',
            'sale_ok': True,
            'purchase_ok': False,
            'default_code': self.code,
        }
        
        if not self.product_id:
            product = self.env['product.product'].create(product_vals)
            self.product_id = product.id
        else:
            self.product_id.write(product_vals)
