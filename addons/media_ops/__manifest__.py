{
    'name': 'Media Operations',
    'version': '1.0',
    'category': 'Operations',
    'summary': 'Flighting and Installation Workflow for Media Assets',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['media_inventory', 'project', 'media_security'],

    'data': [
        'security/ir.model.access.csv',
        'data/job_card_sequence.xml',
        'views/project_task_views.xml',
        'views/job_card_views.xml',
        'views/maintenance_team_views.xml',
        'views/media_inventory_inherit_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
}
