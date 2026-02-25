{
    'name': 'Partner Ledger Multi-Partner Filter',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Adds multi-partner filtering to the Dynamic Partner Ledger report',
    'author': 'Antigravity',
    'website': 'https://www.google.com',
    'depends': ['dynamic_accounts_report'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'partner_ledger_filter/static/src/xml/partner_ledger_view.xml',
            'partner_ledger_filter/static/src/js/partner_ledger_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
