{
    'name': 'Media Executive Dashboard',
    'version': '2.0',
    'category': 'Sales',
    'summary': 'Founder KPIs, utilization trends, and drill-down executive dashboard',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': [
        'media_inventory',
        'media_finance',
        'board',
        'sale_management',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/executive_snapshot_views.xml',
        'views/executive_county_metric_views.xml',
        'views/executive_dashboard_views.xml',
        'views/executive_board_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'media_dashboard/static/src/scss/executive_dashboard.scss',
            'media_dashboard/static/src/js/executive_dashboard.js',
            'media_dashboard/static/src/xml/executive_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
}
