# -*- coding: utf-8 -*-
{
    'name': 'ร้านอาหลั่ย — ระบบจัดการอะไหล่รถยนต์',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'ปรับแต่งระบบ Odoo มาตรฐานเพื่อใช้เป็นร้านขายอะไหล่รถยนต์',
    'author': 'Ran Ahlai',
    'depends': [
        'base', 
        'mail', 
        'product', 
        'point_of_sale', 
        'stock', 
        'purchase',
        'website_sale',
        'hr',
        'pos_hr',
        'account',
        'l10n_th',
        'delivery'
    ],
    'data': [
        'security/spare_security.xml',
        'security/ir.model.access.csv',
        'views/spare_quick_transfer_views.xml',
        'views/spare_part_views.xml',
        'views/menu_views.xml',
        'views/website_templates.xml',
        'views/report_templates.xml',
        'data/ran_ahlai_master_data.xml',
        'data/ran_ahlai_master_data_bulk.xml',
        'data/website_pages.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'warehousepart/static/src/scss/minimal_shop.scss',
        ],
        'point_of_sale.assets_prod': [
            'warehousepart/static/src/xml/pos_receipt.xml',
            'warehousepart/static/src/js/pos_stock_hide.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}
