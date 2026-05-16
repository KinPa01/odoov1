# -*- coding: utf-8 -*-
{
    'name': 'ร้านอาหลั่ย — ระบบจัดการอะไหล่รถยนต์',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'ปรับแต่งระบบ Odoo มาตรฐานเพื่อใช้เป็นร้านขายอะไหล่รถยนต์',
    'author': 'Ran Ahlai',
    'depends': ['base', 'mail', 'product', 'point_of_sale', 'stock', 'purchase'],
    'data': [
        'views/spare_part_views.xml',
        'views/menu_views.xml',
        'data/spare_part_demo.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}
