{
    'name': 'Media Inventory',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage Billboard/Canopy Sites and Faces for OOH Media',
    'description': """
        Centralized system for managing Billboard and Canopy inventory.
        Hierarchy: Site > Face.
    """,
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',

    'depends': ['sale_management', 'base_geolocalize', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/kenya_locations.xml',
        'data/ir_sequence_data.xml',
        'data/inventory_crons.xml',
        'wizard/canopy_status_wizard_views.xml',
        'views/site_views.xml',
        'views/face_views.xml',
        'views/sale_views.xml',
        'views/expense_views.xml',
        'views/menus.xml',
        'report/media_reports.xml',
        'report/media_asset_report.xml',
        'report/media_proposal_report.xml',
        'report/media_proposal_template.xml',
        'report/media_sale_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'media_inventory/static/src/css/map_styles.css',
            'media_inventory/static/src/js/billboard_map.js',
            'media_inventory/static/src/xml/map_templates.xml',
        ],
    },
    'installable': True,
    'application': True,
}
