# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ─── Custom Fields for Spare Parts ────────────────────────────
    part_brand = fields.Char(string='ยี่ห้อ / Brand', help='ยี่ห้อของอะไหล่ชิ้นนี้')
    car_model = fields.Char(string='รุ่นรถ / Fitment', help='รุ่นรถที่สามารถนำอะไหล่นี้ไปใช้งานได้')
    
    # ─── Webike Integration ───────────────────────────────────────
    webike_url = fields.Char(string='Webike URL')
    webike_sku = fields.Char(string='Webike SKU')

