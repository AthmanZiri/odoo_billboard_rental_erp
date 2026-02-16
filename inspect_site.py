
import odoo
from odoo import api, SUPERUSER_ID

def check_site_data(env):
    site_name = 'SITE/0001'
    print(f"Checking for site: {site_name}")
    
    # 1. Search without domain (Raw search)
    sites = env['media.site'].search([('name', '=', site_name)])
    print(f"Found {len(sites)} sites with name '{site_name}'")
    
    for site in sites:
        print(f"ID: {site.id}")
        print(f"Name: {site.name}")
        print(f"Category: {site.site_category}")
        print(f"Active: {site.active}")
        
        # Check if it exists in media.billboard
        billboard = env['media.billboard'].search([('site_id', '=', site.id)])
        print(f"Linked Billboard ID: {billboard.id if billboard else 'None'}")

    # 2. Search WITH the domain used in the view
    domain_sites = env['media.site'].search([('name', '=', site_name), ('site_category', '=', 'billboard')])
    print(f"Found {len(domain_sites)} sites with name '{site_name}' AND category='billboard'")

