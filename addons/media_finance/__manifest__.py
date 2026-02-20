{
    'name': 'Media Finance',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Revenue Recognition and Site P&L for Media Assets',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['media_inventory', 'account', 'sale_management', 'board'],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/billing_crons.xml',
        'views/site_views.xml',
        'views/dashboard_views.xml',
        'wizard/rental_wizard_views.xml',
        'views/rental_views.xml',
        'views/face_views_inherit.xml',
        'views/account_move_views.xml',
        'report/report_invoice_inherit.xml',
        'views/menus.xml',
    ],
    'installable': True,
}
