from odoo import models, fields, api, _

import re
import requests
from odoo.exceptions import UserError

from odoo.exceptions import UserError

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
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Site Name', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
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
    
    # Canopy Specific Fields
    duka_type = fields.Selection([
        ('normal_shop', 'Normal Shop'),
        ('modern_kiosk', 'Modern Kiosk'),
        ('kiosk', 'Kiosk'),
        ('restaurant', 'Restaurant'),
        ('na', 'NA')
    ], string='Type of Duka')
    
    canopy_type = fields.Selection([
        ('canopy', 'Canopy'),
        ('kiosk', 'Kiosk'),
        ('none', 'NONE'),
        ('other', 'Other')
    ], string='Canopy Type')
    
    description_canopy = fields.Text(string='Description')
    
    canopy_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('damaged', 'Damaged'),
        ('withdrawn', 'Withdrawn')
    ], string='Canopy Status', default='active', tracking=True)
    canopy_status_reason = fields.Char(string='Status Reason')
    
    canopy_contact_name = fields.Char(string='Contact Name')
    canopy_contact_phone = fields.Char(string='Contact Phone')
    
    # New Configurable Locations
    county_id = fields.Many2one('media.county', string='County')
    sub_county_id = fields.Many2one('media.sub_county', string='Sub-County')
    
    # Legacy fields (keeping for compatibility)
    county = fields.Char(string='County (Legacy)')
    area = fields.Char(string='Area (Legacy)')
    
    canopy_phone = fields.Char(string='Canopy Location (Phone)')
    allocated_date = fields.Date(string='Allocated Date')
    
    canopy_image = fields.Image(string='Canopy Image')
    measurement_image_1 = fields.Image(string='Image Measurement')
    measurement_image_2 = fields.Image(string='Measurement 2')
    measurement_image_3 = fields.Image(string='Measurement 3')
    measurement_image_4 = fields.Image(string='Measurement 4')
    
    # Billboard Specific Fields
    billboard_description = fields.Text(string='Description')
    billboard_location_text = fields.Char(string='Location')
    billboard_height = fields.Float(string='Height')
    billboard_width = fields.Float(string='Width')
    billboard_image_1 = fields.Image(string='Image 1')
    billboard_image_2 = fields.Image(string='Image 2')
    billboard_comments = fields.Text(string='Comments')
    
    # GPS and Links
    latitude = fields.Float(string='Latitude', digits=(16, 6))
    longitude = fields.Float(string='Longitude', digits=(16, 6))
    google_maps_link = fields.Char(string='Google Maps Link')
    
    # Links
    face_ids = fields.One2many('media.face', 'site_id', string='Faces')
    permit_history_ids = fields.One2many('media.permit.history', 'site_id', string='Permit History')
    lease_line_ids = fields.One2many('sale.order.line', compute='_compute_lease_history', string='Lease History')
    expense_ids = fields.One2many('media.expense', 'site_id', string='Expenses')
    
    image_ids = fields.Many2many('ir.attachment', string='Site Photos')
    color = fields.Integer(string='Color Index')
    
    active = fields.Boolean(default=True)
    
    total_faces_count = fields.Integer(compute='_compute_site_stats', string='Total Faces', store=True, group_operator="sum")
    occupied_faces_count = fields.Integer(compute='_compute_site_stats', string='Occupied Faces', store=True, group_operator="sum")
    available_faces_count = fields.Integer(compute='_compute_site_stats', string='Available Faces', store=True, group_operator="sum")
    total_monthly_revenue = fields.Float(compute='_compute_site_stats', string='Monthly Revenue', store=True, group_operator="sum")

    def action_fetch_coordinates(self):
        """Manual trigger for coordinate fetching from Google Maps Link"""
        for record in self:
            if record.google_maps_link:
                record._onchange_google_maps_link()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('media.site') or 'New'
        return super(MediaSite, self).create(vals_list)

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

    face_count = fields.Integer(compute='_compute_site_stats', string='Faces Count')
    permit_count = fields.Integer(compute='_compute_site_stats', string='Permits Count')
    rentals_count = fields.Integer(compute='_compute_site_stats', string='Rentals Count')
    expenses_count = fields.Integer(compute='_compute_site_stats', string='Expenses Count')

    @api.depends('face_ids', 'face_ids.occupancy_status', 'face_ids.price_per_month', 'permit_history_ids', 'expense_ids', 'lease_line_ids')
    def _compute_site_stats(self):
        for site in self:
            site.face_count = len(site.face_ids)
            site.permit_count = len(site.permit_history_ids)
            site.expenses_count = len(site.expense_ids)
            site.rentals_count = len(site.lease_line_ids)
            
            site.total_faces_count = site.face_count
            site.occupied_faces_count = len(site.face_ids.filtered(lambda f: f.occupancy_status == 'booked'))
            site.available_faces_count = site.total_faces_count - site.occupied_faces_count
            site.total_monthly_revenue = sum(site.face_ids.mapped('price_per_month'))

    def action_view_faces(self):
        self.ensure_one()
        return {
            'name': _('Faces'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.face',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id},
        }

    def action_view_permits(self):
        self.ensure_one()
        return {
            'name': _('Permits'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.permit.history',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id},
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
        return {
            'name': _('Expenses'),
            'type': 'ir.actions.act_window',
            'res_model': 'media.expense',
            'view_mode': 'list,form',
            'domain': [('site_id', '=', self.id)],
            'context': {'default_site_id': self.id},
        }

    def _compute_lease_history(self):
        for site in self:
            site.lease_line_ids = self.env['sale.order.line'].search([
                ('media_face_id', 'in', site.face_ids.ids)
            ])

