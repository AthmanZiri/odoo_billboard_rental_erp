{
    'name': 'Media Expiry Notifications',
    'version': '1.0',
    'summary': 'Configurable Expiry Notifications for Media Assets',
    'description': 'Provides email and push notifications for billboard faces, digital slots, and canopies expiring in configured number of days.',
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'category': 'Media/Inventory',
    'depends': ['mail', 'media_inventory', 'media_dooh', 'media_finance'],
    'data': [
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
