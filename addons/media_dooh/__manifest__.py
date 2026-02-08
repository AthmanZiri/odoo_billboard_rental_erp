{
    'name': 'Media DOOH',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Digital Out-of-Home Slot and Loop Management',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['media_inventory'],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/reports_data.xml',
        'views/face_views.xml',

        'views/slot_views.xml',
        'views/menus.xml',
        'views/sale_views.xml',
    ],
    'installable': True,
}
