{
    "name": "Generate Batch Payment Link",
    'description': """ Select multiple invoices and generate one link. """,
    "author": "Odolution",
    "category": "CRM",
    'currency': "USD",
    "license": "OPL-1",
    'category': 'Extra Tools',
    'live_test_url':'https://youtu.be/QOuly0C8Upc',
    'price': 30.00,
    "version": "14.0.1",

    "depends": [
        'account','sale','website_sale'
    ],

    "data": [
        'security/ir.model.access.csv',
        'views/main_view.xml',
    ],
    'images': ['static/description/background.gif'],
    "auto_install": False,
    "application": True,
    "installable": True,
}
