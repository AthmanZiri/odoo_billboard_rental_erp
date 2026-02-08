{
    'name': 'Media Security',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Watchman and Incident Management for Media Sites',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['media_inventory', 'hr'],

    'data': [
        'security/ir.model.access.csv',
        'views/watchman_views.xml',
        'views/incident_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
}
