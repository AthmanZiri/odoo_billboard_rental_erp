{
    'name': 'Media Reports Sync',
    'version': '1.0',
    'category': 'Technical',
    'summary': 'Unified report customizations for Media ERP',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['sale', 'account', 'media_inventory', 'media_finance'],
    'data': [
        # 'data/paperformat_data.xml',
        'report/report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
