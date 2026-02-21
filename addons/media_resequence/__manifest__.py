{
    'name': 'Media Resequence',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Resequence and Renumber Media Assets',
    'description': """
        Allows users to reorder billboards, canopies, and digital screens via drag-and-drop 
        and bulk-renumber their serial numbers based on the new sequence.
    """,
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['media_inventory', 'media_dooh'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/resequence_wizard_views.xml',
        'views/media_assets_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
