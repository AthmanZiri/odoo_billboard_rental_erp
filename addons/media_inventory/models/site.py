from odoo import models, fields, api
import re
import requests
from odoo.exceptions import UserError

class MediaSite(models.Model):
    _name = 'media.site'
    _description = 'Media Site'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Site Name', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    code = fields.Char(string='Site Code', tracking=True)
    
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
    
    # GPS and Links
    latitude = fields.Float(string='Latitude', digits=(16, 5))
    longitude = fields.Float(string='Longitude', digits=(16, 5))
    google_maps_link = fields.Char(string='Google Maps Link')
    
    # Links
    face_ids = fields.One2many('media.face', 'site_id', string='Faces')
    permit_history_ids = fields.One2many('media.permit.history', 'site_id', string='Permit History')
    lease_line_ids = fields.One2many('sale.order.line', compute='_compute_lease_history', string='Lease History')
    
    image_ids = fields.Many2many('ir.attachment', string='Site Photos')
    color = fields.Integer(string='Color Index')
    
    active = fields.Boolean(default=True)
    
    total_faces_count = fields.Integer(compute='_compute_site_stats', string='Total Faces', store=True, group_operator="sum")
    occupied_faces_count = fields.Integer(compute='_compute_site_stats', string='Occupied Faces', store=True, group_operator="sum")
    available_faces_count = fields.Integer(compute='_compute_site_stats', string='Available Faces', store=True, group_operator="sum")
    total_monthly_revenue = fields.Float(compute='_compute_site_stats', string='Monthly Revenue', store=True, group_operator="sum")

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

    @api.depends('face_ids', 'face_ids.occupancy_status', 'face_ids.price_per_month')
    def _compute_site_stats(self):
        for site in self:
            site.total_faces_count = len(site.face_ids)
            site.occupied_faces_count = len(site.face_ids.filtered(lambda f: f.occupancy_status == 'booked'))
            site.available_faces_count = site.total_faces_count - site.occupied_faces_count
            site.total_monthly_revenue = sum(site.face_ids.mapped('price_per_month'))

    def _compute_lease_history(self):
        for site in self:
            site.lease_line_ids = self.env['sale.order.line'].search([
                ('media_face_id', 'in', site.face_ids.ids)
            ])
