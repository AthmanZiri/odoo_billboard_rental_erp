{
    'name': 'Media Partner History',
    'version': '1.0',
    'summary': 'View media rentals and printing history in customer profile',
    'category': 'Marketing/Billboard',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['media_inventory', 'media_finance', 'media_dooh', 'sale', 'sale_management'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
