from odoo import models, fields, api, _
import re
import requests
from odoo.exceptions import UserError, ValidationError

class MediaSiteMixin(models.AbstractModel):
    _name = 'media.site.mixin'
    _description = 'Media Site Mixin'

    def action_fetch_coordinates(self):
        """Manual trigger for coordinate fetching from Google Maps Link"""
        for record in self:
            if record.google_maps_link:
                record._onchange_google_maps_link()
        return True

    @api.onchange('google_maps_link')
    def _onchange_google_maps_link(self):
        if self.google_maps_link:
            link = self.google_maps_link.strip()
            
            # Handle shortened links (goo.gl/maps or maps.app.goo.gl)
            if 'goo.gl' in link:
                try:
                    # Resolve the redirect to get the full URL with coordinates
                    response = requests.get(link, allow_redirects=True, timeout=3)
                    link = response.url
                except Exception:
                    # If resolution fails (e.g., no internet), we fall back to the original link
                    pass

            # Reorder prioritization: Site location (dir/search/q) should come before map center (@)
            
            # Pattern 1: dir//lat,lon or search/lat,lon (Common for shared pins)
            match = re.search(r'(?:dir//|search/)(-?\d+\.\d+),(-?\d+\.\d+)', link)
            if match:
                self.latitude = float(match.group(1))
                self.longitude = float(match.group(2))
                return

            # Pattern 2: q=lat,lon (Search URL)
            match = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', link)
            if match:
                self.latitude = float(match.group(1))
                self.longitude = float(match.group(2))
                return

            # Pattern 3: !3d(-?\d+\.\d+)!4d(-?\d+\.\d+) (Deep link format)
            match = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', link)
            if match:
                self.latitude = float(match.group(1))
                self.longitude = float(match.group(2))
                return

            # Pattern 4: @lat,lon,zoom (Standard Desktop URL - Fallback to map center)
            match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', link)
            if match:
                self.latitude = float(match.group(1))
                self.longitude = float(match.group(2))
                return

    @api.depends('face_ids', 'face_ids.occupancy_status', 'face_ids.price_per_month', 'permit_history_ids', 'expense_ids', 'lease_line_ids')
    def _compute_site_stats(self):
        for record in self:
            record.face_count = len(record.face_ids)
            record.permit_count = len(record.permit_history_ids)
            record.expenses_count = len(record.expense_ids)
            record.rentals_count = len(record.lease_line_ids)
            
            record.total_faces_count = record.face_count
            record.occupied_faces_count = len(record.face_ids.filtered(lambda f: f.occupancy_status == 'booked'))
            record.available_faces_count = record.total_faces_count - record.occupied_faces_count
            record.total_monthly_revenue = sum(record.face_ids.mapped('price_per_month'))

    def action_view_faces(self):
        self.ensure_one()
        # Use the base site ID (self.site_id.id if called from delegated model, or self.id if base)
        base_id = self.site_id.id if hasattr(self, 'site_id') else self.id
        return {
            'name': _('Faces'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.face',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', base_id)],
            'context': {'default_site_id': base_id},
        }

    def action_view_permits(self):
        self.ensure_one()
        base_id = self.site_id.id if hasattr(self, 'site_id') else self.id
        return {
            'name': _('Permits'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.permit.history',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', base_id)],
            'context': {'default_site_id': base_id},
        }

    def action_view_rentals(self):
        self.ensure_one()
        return {
            'name': _('Rentals'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.lease_line_ids.ids)],
        }

    def action_view_expenses(self):
        self.ensure_one()
        base_id = self.site_id.id if hasattr(self, 'site_id') else self.id
        return {
            'name': _('Expenses'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.expense',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', base_id)],
            'context': {'default_site_id': base_id},
        }

    def _compute_lease_history(self):
        for record in self:
            record.lease_line_ids = self.env['sale.order.line'].search([
                ('media_face_id', 'in', record.face_ids.ids)
            ])

class MediaCounty(models.Model):
    _name = 'media.county'
    _description = 'Kenya County'
    _order = 'name'

    name = fields.Char(string='County Name', required=True)
    code = fields.Char(string='County Code')

class MediaSubCounty(models.Model):
    _name = 'media.sub_county'
    _description = 'Kenya Sub-County'
    _order = 'name'

    name = fields.Char(string='Sub-County Name', required=True)
    county_id = fields.Many2one('media.county', string='County', required=True, ondelete='cascade')

class MediaSite(models.Model):
    _name = 'media.site'
    _description = 'Media Site'
    _inherit = ['media.site.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Site Name', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    shop_name = fields.Char(string='Shop Name', tracking=True)
    code = fields.Char(string='Site Code', tracking=True)
    site_category = fields.Selection([
        ('billboard', 'Billboard'),
        ('canopy', 'Canopy')
    ], string='Site Category', default='billboard', required=True)
    
    # Geographic Fields
    street = fields.Char()
    city = fields.Char()
    district = fields.Char()
    zip = fields.Char()
    country_id = fields.Many2one('res.country', string='Country')
    road_type = fields.Selection([
        ('highway', 'Highway'),
        ('main_road', 'Main Road'),
        ('urban_road', 'Urban Road'),
        ('rural_road', 'Rural Road')
    ], string='Road Type')
    
    # Geographic / Shared Data
    county_id = fields.Many2one('media.county', string='County')
    sub_county_id = fields.Many2one('media.sub_county', string='Sub-County')
    latitude = fields.Float(string='Latitude', digits=(16, 6))
    longitude = fields.Float(string='Longitude', digits=(16, 6))
    google_maps_link = fields.Char(string='Google Maps Link')
    
    # Links (Common to all assets)
    face_ids = fields.One2many('media.face', 'site_id', string='Faces')
    permit_history_ids = fields.One2many('media.permit.history', 'site_id', string='Permit History')
    lease_line_ids = fields.One2many('sale.order.line', compute='_compute_lease_history', string='Lease History')
    expense_ids = fields.One2many('media.expense', 'site_id', string='Expenses')
    image_ids = fields.Many2many('ir.attachment', string='Site Photos')
    color = fields.Integer(string='Color Index')
    
    active = fields.Boolean(default=True)
    

    
    total_faces_count = fields.Integer(compute='_compute_site_stats', string='Total Faces', store=True, aggregator="sum")
    occupied_faces_count = fields.Integer(compute='_compute_site_stats', string='Occupied Faces', store=True, aggregator="sum")
    available_faces_count = fields.Integer(compute='_compute_site_stats', string='Available Faces', store=True, aggregator="sum")
    total_monthly_revenue = fields.Float(compute='_compute_site_stats', string='Monthly Revenue', store=True, aggregator="sum")

    face_count = fields.Integer(compute='_compute_site_stats', string='Faces Count')
    permit_count = fields.Integer(compute='_compute_site_stats', string='Permits Count')
    rentals_count = fields.Integer(compute='_compute_site_stats', string='Rentals Count')
    expenses_count = fields.Integer(compute='_compute_site_stats', string='Expenses Count')


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                # Sites created directly might not have a category-specific sequence
                # but we keep this as a fallback.
                vals['name'] = self.env['ir.sequence'].next_by_code('media.site') or 'New'
        return super(MediaSite, self).create(vals_list)

class MediaBillboard(models.Model):
    _name = 'media.billboard'
    _description = 'Billboard Asset'
    _inherits = {'media.site': 'site_id'}
    _inherit = ['media.site.mixin', 'mail.thread', 'mail.activity.mixin']

    site_id = fields.Many2one('media.site', string='Base Site', required=True, ondelete='cascade')
    
    description = fields.Text(string='Description')
    location_text = fields.Char(string='Location')
    height = fields.Float(string='Height')
    width = fields.Float(string='Width')
    image_1 = fields.Image(string='Image 1')
    image_2 = fields.Image(string='Image 2')
    comments = fields.Text(string='Comments')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['site_category'] = 'billboard'
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('media.billboard') or 'New'
        return super(MediaBillboard, self).create(vals_list)

class MediaCanopy(models.Model):
    _name = 'media.canopy'
    _description = 'Canopy Asset'
    _inherits = {'media.site': 'site_id'}
    _inherit = ['media.site.mixin', 'mail.thread', 'mail.activity.mixin']

    site_id = fields.Many2one('media.site', string='Base Site', required=True, ondelete='cascade')

    duka_type = fields.Selection([
        ('normal_shop', 'Normal Shop'),
        ('modern_kiosk', 'Modern Kiosk'),
        ('kiosk', 'Kiosk'),
        ('restaurant', 'Restaurant'),
        ('na', 'NA')
    ], string='Type of Duka')
    
    description = fields.Text(string='Description')
    
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('damaged', 'Damaged'),
        ('withdrawn', 'Withdrawn')
    ], string='Status', default='active', tracking=True)
    status_reason = fields.Char(string='Status Reason')
    
    contact_name = fields.Char(string='Contact Name')
    contact_phone = fields.Char(string='Contact Phone')
    location_phone = fields.Char(string='Canopy Location (Phone)')
    allocated_date = fields.Date(string='Allocated Date')
    
    canopy_image = fields.Image(string='Canopy Image')
    measurement_image_1 = fields.Image(string='Image Measurement')
    measurement_image_2 = fields.Image(string='Measurement 2')
    measurement_image_3 = fields.Image(string='Measurement 3')
    measurement_image_4 = fields.Image(string='Measurement 4')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['site_category'] = 'canopy'
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('media.canopy') or 'New'
        return super(MediaCanopy, self).create(vals_list)


