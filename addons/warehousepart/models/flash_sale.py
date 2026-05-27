# -*- coding: utf-8 -*-
"""
Ran Ahlai — Flash Sale Model (Odoo 19 compatible)
รองรับ 2 โหมด:
  1. เลือกสินค้าโดยตรง (flash_product_ids) — Admin เลือกรายสินค้า
  2. ใช้ Tag (tag_id) — สินค้าที่ติด tag อัตโนมัติ
"""

from odoo import models, fields, api
import logging
import random

_logger = logging.getLogger(__name__)


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    is_flash_sale = fields.Boolean(string='Is Flash Sale', default=False)


class FlashSaleSession(models.Model):
    """
    Flash Sale Config — รองรับการเลือกสินค้าโดยตรง หรือเลือกผ่าน Tag
    """
    _name = 'warehousepart.flash.sale'
    _description = 'Flash Sale Configuration'

    name = fields.Char(string='ชื่อ Flash Sale', required=True)

    # ── โหมด 1: เลือกสินค้าโดยตรง ──────────────────────────────
    flash_product_ids = fields.Many2many(
        'product.template',
        'flash_sale_product_rel',
        'flash_sale_id',
        'product_tmpl_id',
        string='สินค้า Flash Sale (เลือกเอง)',
        domain=[('is_published', '=', True), ('active', '=', True)],
        help='เลือกสินค้าที่ต้องการลดราคาโดยตรง — ถ้าเลือกไว้จะใช้แทน Tag'
    )

    # ── โหมด 2: ใช้ Tag (Fallback) ──────────────────────────────
    tag_id = fields.Many2one(
        'product.tag',
        string='Product Tag (ถ้าไม่เลือกสินค้าเอง)',
        help='ถ้าไม่ได้เลือกสินค้าโดยตรง จะใช้สินค้าที่มี Tag นี้แทน'
    )

    discount_percent = fields.Float(string='ส่วนลด (%)', default=20.0)
    max_display_products = fields.Integer(
        string='จำนวนสูงสุดที่แสดงบนหน้าแรก',
        default=4,
        help='จำนวนสินค้า Flash Sale ที่แสดงในแต่ละรอบ (สุ่มใหม่ทุก 8 ชั่วโมง)'
    )
    active = fields.Boolean(default=True)

    # Computed: แสดงจำนวนสินค้าทั้งหมดใน Flash Sale
    total_product_count = fields.Integer(
        string='จำนวนสินค้าทั้งหมดใน Flash Sale',
        compute='_compute_total_product_count',
        store=False,
    )

    @api.depends('flash_product_ids', 'tag_id')
    def _compute_total_product_count(self):
        for rec in self:
            templates = rec._get_flash_templates()
            rec.total_product_count = len(templates)

    def _get_flash_templates(self):
        """
        ดึงสินค้า Flash Sale ทั้งหมด:
        - ถ้า flash_product_ids มีข้อมูล → ใช้รายการนั้น
        - ถ้าไม่มี → ดึงสินค้าที่ติด tag_id
        """
        if self.flash_product_ids:
            # กรองเฉพาะสินค้าที่ยังเปิดอยู่
            return self.flash_product_ids.filtered(
                lambda t: t.active and t.is_published
            )
        elif self.tag_id:
            return self.env['product.template'].search([
                ('product_tag_ids', 'in', [self.tag_id.id]),
                ('is_published', '=', True),
                ('active', '=', True),
            ])
        return self.env['product.template']

    def action_update_discount(self):
        """
        อัปเดตส่วนลดเข้าสู่ Pricelist ทุกตัวที่ Active ในระบบ
        """
        # 1. ลบรายการส่วนลด Flash Sale เก่าทั้งหมด
        old_items = self.env['product.pricelist.item'].search([
            ('is_flash_sale', '=', True)
        ])
        if old_items:
            _logger.info('FlashSale: ลบส่วนลดเดิม %d รายการ', len(old_items))
            old_items.unlink()

        # 2. ค้นหาการตั้งค่าที่ active
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            _logger.info('FlashSale: ไม่พบการตั้งค่า')
            return

        # 3. ดึงสินค้า Flash Sale
        templates = config._get_flash_templates()
        if not templates:
            _logger.info('FlashSale: ไม่มีสินค้าใน Flash Sale')
            return

        # 4. อัปเดต Pricelist ทุกตัว
        all_pricelists = self.env['product.pricelist'].search([])
        for pl in all_pricelists:
            for tmpl in templates:
                self.env['product.pricelist.item'].create({
                    'pricelist_id': pl.id,
                    'compute_price': 'percentage',
                    'applied_on': '1_product',
                    'product_tmpl_id': tmpl.id,
                    'percent_price': config.discount_percent,
                    'price_discount': config.discount_percent,
                    'is_flash_sale': True,
                })

        _logger.info(
            'FlashSale: อัปเดตส่วนลด %.1f%% ให้กับ %d สินค้า ลงใน %d Pricelists',
            config.discount_percent, len(templates), len(all_pricelists)
        )


class HomepageCategory(models.Model):
    """
    Homepage Category Config — Admin กำหนดหมวดหมู่ที่แสดงบนหน้าแรก
    """
    _name = 'warehousepart.homepage.category'
    _description = 'Homepage Category Display Config'
    _order = 'sequence, id'

    name = fields.Char(string='ชื่อหมวดหมู่ (แสดงบนเว็บ)', required=True)
    icon = fields.Char(
        string='ไอคอน (Emoji)',
        default='🔧',
        help='ใส่ emoji เช่น 🛢️ ⚙️ 🔧 🔘 💡 🌬️'
    )
    website_categ_id = fields.Many2one(
        'product.public.category',
        string='หมวดหมู่เว็บไซต์ (website_sale)',
        help='เลือกหมวดหมู่ website_sale — URL จะเป็น /shop?categ_id=X'
    )
    sequence = fields.Integer(string='ลำดับ', default=10)
    active = fields.Boolean(string='แสดงบนหน้าแรก', default=True)
    product_count = fields.Integer(
        string='จำนวนสินค้า',
        compute='_compute_product_count',
        store=False
    )

    @api.depends('website_categ_id')
    def _compute_product_count(self):
        for rec in self:
            if rec.website_categ_id:
                rec.product_count = self.env['product.template'].search_count([
                    ('public_categ_ids', 'in', [rec.website_categ_id.id]),
                    ('is_published', '=', True),
                    ('active', '=', True),
                ])
            else:
                rec.product_count = 0


class HomepageFeaturedProduct(models.Model):
    """
    Best Sellers / Featured Products — Admin เลือกสินค้าแสดงบน Homepage
    จัดการจาก Backend → ร้านอาหลั่ย → จัดการหน้าเว็บไซต์ → สินค้าแนะนำ
    """
    _name = 'warehousepart.homepage.product'
    _description = 'Homepage Featured Product'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='สินค้า',
        required=True,
        domain=[('is_published', '=', True), ('active', '=', True)],
        help='เลือกสินค้าที่จะแสดงในส่วน Best Sellers บนหน้าแรก'
    )
    badge_text = fields.Char(
        string='ป้ายกำกับ (Badge)',
        help='เช่น BEST SELLER, HOT, NEW, SALE — เว้นว่างถ้าไม่ต้องการป้าย'
    )
    badge_color = fields.Selection([
        ('red',    '🔴 แดง'),
        ('orange', '🟠 ส้ม'),
        ('gold',   '🟡 ทอง'),
        ('green',  '🟢 เขียว'),
        ('blue',   '🔵 น้ำเงิน'),
    ], string='สีป้าย', default='red')
    sequence = fields.Integer(string='ลำดับ', default=10)
    active = fields.Boolean(string='แสดงบนหน้าแรก', default=True)

    # Computed display fields
    product_name = fields.Char(related='product_tmpl_id.name', string='ชื่อสินค้า', readonly=True)
    product_price = fields.Float(related='product_tmpl_id.list_price', string='ราคา', readonly=True)
