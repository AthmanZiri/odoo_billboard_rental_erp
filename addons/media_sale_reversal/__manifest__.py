{
    'name': 'Media Sale Reversal',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Reverse booked assets on Sale Order cancellation',
    'description': """
        Automatically reverses booked assets (Faces, Digital Screens, Canopies)
        and cancels related rentals when a Sale Order is cancelled.
    """,
    'author': 'Antigravity',
    'depends': ['sale', 'media_finance', 'media_inventory', 'media_dooh'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
