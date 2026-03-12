# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Kenya eTIMS VSCU Integration(v19)",
    'countries': ['ke'],
    'summary': """
            Kenya eTIMS Device VSCU Integration
        """,
    'description': """
       This module integrates with the Kenyan VSCU eTIMS device.
    """,
    'author': 'Morris-Kinyua',
    'category': 'Accounting/Localizations/EDI',
    'version': '19.0.1.0.0',
    'website': 'https://wa.me/2547105050561',
    'support': 'https://wa.me/2547105050561',
    'license': 'OPL-1',
    'depends': ['l10n_ke','stock','product_unspsc'],
    'data': [
        'data/l10n_ke_etims_vscu_v19.code.csv',
        'data/ir_cron_data.xml',
        # 'data/uom.uom.csv',
        'views/account_tax_views.xml',
        'views/product_views.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/uom_uom_views.xml',
        'views/l10n_ke_etims_vscu_code_views.xml',
        'views/l10n_ke_etims_vscu_notice_views.xml',
        'views/menuitems.xml',
        'security/ir.model.access.csv',
        'wizard/account_move_reversal_view.xml',
    ],
    'images': ['static/description/icon.png'],
    'price': 600.00,
    'currency': 'USD',
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_product.xml',
    ],
    'post_init_hook': '_post_init_hook',
        'auto_install': ['l10n_ke'],
}
