{
    'name': 'Multi Invoice Payment For Customer and Vendor | Partial Payments',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Register single payments for multiple customer invoices or vendor bills with partial payment support.',
    'description': """
        This module allows users to select multiple open invoices or bills and allocate one payment across them in a single transaction.
        Key Features:
        - Single payment for multiple invoices/bills.
        - Full support for partial payments.
        - Easy allocation of payment amounts across documents.
        - Compliance with standard accounting principles.
    """,
    'author': 'JengaSol Consulting',
    'website': 'https://jengasol.co.ke',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/account_multi_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
