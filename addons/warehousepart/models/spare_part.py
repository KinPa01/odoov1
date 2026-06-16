# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ─── Custom Fields for Spare Parts ────────────────────────────
    part_brand = fields.Char(string='ยี่ห้อ / Brand', help='ยี่ห้อของอะไหล่ชิ้นนี้')
    car_model = fields.Char(string='รุ่นรถ / Fitment', help='รุ่นรถที่สามารถนำอะไหล่นี้ไปใช้งานได้')
    shelf_location = fields.Many2one(
        'stock.location', string='ชั้นวาง (Shelf)',
        help='ตำแหน่งชั้นวางสินค้า',
        domain="[('usage', '=', 'internal')]",
    )

    # ─── Webike Integration ───────────────────────────────────────
    webike_url = fields.Char(string='Webike URL')
    webike_sku = fields.Char(string='Webike SKU')

    # ─── Stock Per Warehouse (computed, read-only) ────────────────
    qty_pos_warehouse = fields.Float(
        string='สต็อกหน้าร้าน (POS)',
        compute='_compute_warehouse_qtys',
        digits=(16, 2),
        help='จำนวนสินค้าในคลังหน้าร้าน (POS warehouse)',
    )
    # หมายเหตุ: qty_online_warehouse ถูกลบออก
    # เพราะใช้คลังออนไลน์ที่มีอยู่แล้วในระบบ (ตั้งค่าผ่าน Website → Settings → Warehouse)

    @api.depends('product_variant_ids')
    def _compute_warehouse_qtys(self):
        """
        คำนวณสต็อกเฉพาะคลังหน้าร้าน (POS warehouse, code=POS)
        ใช้ SQL batch query เพื่อประสิทธิภาพสูงสุด
        """
        tmpl_ids = self.ids
        if not tmpl_ids:
            for rec in self:
                rec.qty_pos_warehouse = 0.0
            return

        self.env.cr.execute("""
            SELECT
                pp.product_tmpl_id,
                COALESCE(SUM(sq.quantity), 0) AS qty
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN stock_warehouse sw ON (
                sl.parent_path LIKE (
                    SELECT sl2.parent_path || '%%'
                    FROM stock_location sl2
                    WHERE sl2.id = sw.lot_stock_id
                )
                OR sl.id = sw.lot_stock_id
            )
            WHERE sl.usage = 'internal'
              AND pp.product_tmpl_id = ANY(%s)
              AND sw.code = 'POS'
            GROUP BY pp.product_tmpl_id
        """, (tmpl_ids,))

        qty_map = {row[0]: float(row[1]) for row in self.env.cr.fetchall()}
        for rec in self:
            rec.qty_pos_warehouse = qty_map.get(rec.id, 0.0)

    # ─── Public Helpers ───────────────────────────────────────────
    @api.model
    def get_warehouse_stock(self, product_tmpl_id, warehouse_code):
        """
        คืนจำนวนสต็อกของ product template ใน warehouse ที่ระบุ (ผ่าน code เช่น 'POS')
        ใช้งาน: self.env['product.template'].get_warehouse_stock(42, 'POS')
        """
        self.env.cr.execute("""
            SELECT COALESCE(SUM(sq.quantity), 0)
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN stock_warehouse sw ON (
                sl.parent_path LIKE (
                    SELECT sl2.parent_path || '%%'
                    FROM stock_location sl2
                    WHERE sl2.id = sw.lot_stock_id
                )
                OR sl.id = sw.lot_stock_id
            )
            WHERE sl.usage = 'internal'
              AND pp.product_tmpl_id = %s
              AND sw.code = %s
        """, (product_tmpl_id, warehouse_code))
        result = self.env.cr.fetchone()
        return float(result[0]) if result else 0.0

    @api.model
    def get_warehouse_stock_by_id(self, product_tmpl_id, warehouse_id):
        """
        คืนจำนวนสต็อกของ product template ใน warehouse ที่ระบุ (ผ่าน warehouse_id)
        ใช้งาน: self.env['product.template'].get_warehouse_stock_by_id(42, website.warehouse_id.id)
        สะดวกกว่าเมื่อมี warehouse record อยู่แล้ว (เช่น website.warehouse_id)
        """
        if not warehouse_id:
            return 0.0
        self.env.cr.execute("""
            SELECT COALESCE(SUM(sq.quantity), 0)
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            JOIN product_product pp ON sq.product_id = pp.id
            JOIN stock_warehouse sw ON (
                sl.parent_path LIKE (
                    SELECT sl2.parent_path || '%%'
                    FROM stock_location sl2
                    WHERE sl2.id = sw.lot_stock_id
                )
                OR sl.id = sw.lot_stock_id
            )
            WHERE sl.usage = 'internal'
              AND pp.product_tmpl_id = %s
              AND sw.id = %s
        """, (product_tmpl_id, warehouse_id))
        result = self.env.cr.fetchone()
        return float(result[0]) if result else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._sync_flash_sale_pricelist()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if 'product_tag_ids' in vals:
            self._sync_flash_sale_pricelist()
        return res

    def _sync_flash_sale_pricelist(self):
        """
        ซิงค์รายการส่วนลด Pricelist สำหรับสินค้าที่มี/ไม่มีแท็ก Flash Sale แบบเรียลไทม์
        """
        config = self.env['warehousepart.flash.sale'].sudo().search([('active', '=', True)], limit=1)
        if not config or config.mode != 'auto' or not config.tag_id:
            return

        flash_tag = config.tag_id
        all_pricelists = self.env['product.pricelist'].sudo().search([])

        for tmpl in self:
            has_tag = flash_tag in tmpl.product_tag_ids
            # ค้นหา pricelist items เก่าของสินค้านี้
            existing_items = self.env['product.pricelist.item'].sudo().search([
                ('product_tmpl_id', '=', tmpl.id),
                ('is_flash_sale', '=', True)
            ])

            if has_tag:
                # ถ้ามีแท็กแต่ยังไม่มี pricelist item -> สร้างให้ครบทุก pricelist
                for pl in all_pricelists:
                    item_exists = existing_items.filtered(lambda i: i.pricelist_id == pl)
                    if not item_exists:
                        self.env['product.pricelist.item'].sudo().create({
                            'pricelist_id': pl.id,
                            'compute_price': 'percentage',
                            'applied_on': '1_product',
                            'product_tmpl_id': tmpl.id,
                            'percent_price': config.discount_percent,
                            'price_discount': config.discount_percent,
                            'is_flash_sale': True,
                        })
            else:
                # ถ้าไม่มีแท็กแต่มี pricelist item -> ลบทิ้ง
                if existing_items:
                    existing_items.unlink()

    @api.model
    def _search_get_detail(self, website, order, options):
        res = super()._search_get_detail(website, order, options)
        if 'search_fields' in res:
            # เพิ่มให้สามารถค้นหาจากยี่ห้อและรุ่นรถได้ที่ช่องค้นหาหน้าเว็บ
            res['search_fields'].extend(['part_brand', 'car_model'])
        return res

    def get_online_qty(self, website=None):
        """
        คำนวณจำนวนสต็อกคงเหลือในคลังออนไลน์สำหรับสินค้าชิ้นนี้
        """
        self.ensure_one()
        wh = website and website.warehouse_id
        if not wh:
            wh = self.env['stock.warehouse'].sudo().search([('code', '=', 'ONLIN')], limit=1) or \
                 self.env['stock.warehouse'].sudo().search([('code', '=', 'WH')], limit=1)
        if not wh:
            return 0.0
        return self.get_warehouse_stock_by_id(self.id, wh.id)

    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website):
        """
        ถ้าสินค้าหมดในคลังออนไลน์ (free_qty <= 0) และยังไม่ได้ระบุ out_of_stock_message ในระบบหลังบ้าน
        ให้แสดงข้อความแจ้งเตือนสินค้าหมดโดยอัตโนมัติ (Auto Out-of-Stock Message)
        """
        res = super()._get_additionnal_combination_info(product_or_template, quantity, uom, date, website)
        
        # ตรวจสอบว่าสินค้ามีสต็อกต่ำกว่าหรือเท่ากับ 0 ในคลังออนไลน์
        if product_or_template.is_storable and res.get('free_qty', 0.0) <= 0:
            if not res.get('out_of_stock_message'):
                # กำหนดข้อความแจ้งเตือนหมดแบบ Auto
                if res.get('allow_out_of_stock_order'):
                    res['out_of_stock_message'] = '<b>สินค้าหมดชั่วคราว!</b> (แต่คุณยังสามารถสั่งซื้อล่วงหน้าได้ ทางเรากำลังเร่งเติมสต็อกครับ)'
                else:
                    res['out_of_stock_message'] = '<b>สินค้าหมดชั่วคราว!</b> (ทางเรากำลังเร่งเติมสต็อกครับ)'
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    shortage_reason = fields.Selection([
        ('none', 'ไม่มี / None'),
        ('supplier_short', 'ซัพพลายเออร์ส่งไม่ครบ / Supplier Short-shipped'),
        ('damaged', 'สินค้าแตกหัก/เสียหาย / Damaged'),
        ('lost', 'สูญหาย / Lost'),
        ('other', 'อื่นๆ (ระบุในหมายเหตุ) / Other'),
    ], string='สาเหตุสินค้าขาด / Shortage Reason', default='none')
    shortage_note = fields.Char(string='หมายเหตุสินค้าขาด / Shortage Note')

    shelf_location = fields.Many2one(
        'stock.location',
        string='ชั้นวาง (Shelf)',
        related='product_id.product_tmpl_id.shelf_location',
        readonly=True,
    )
    location_qty = fields.Float(
        string='สต็อกต้นทาง',
        compute='_compute_locations_qty',
        digits=(16, 2),
    )
    location_dest_qty = fields.Float(
        string='สต็อกปลายทาง',
        compute='_compute_locations_qty',
        digits=(16, 2),
    )

    @api.depends('product_id', 'location_id', 'location_dest_id')
    def _compute_locations_qty(self):
        for move in self:
            if move.product_id and move.location_id:
                # Odoo standard context search for location qty
                move.location_qty = move.product_id.with_context(location=move.location_id.id).qty_available
            else:
                move.location_qty = 0.0

            if move.product_id and move.location_dest_id:
                # Odoo standard context search for location qty
                move.location_dest_qty = move.product_id.with_context(location=move.location_dest_id.id).qty_available
            else:
                move.location_dest_qty = 0.0

    def _prepare_move_split_vals(self, qty):
        vals = super()._prepare_move_split_vals(qty)
        vals.update({
            'shortage_reason': 'none',
            'shortage_note': False,
        })
        return vals


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_pending = fields.Float(
        string='ค้างรับ / Pending Qty',
        compute='_compute_qty_pending',
        store=True,
    )
    shortage_reasons = fields.Char(
        string='สาเหตุสินค้าขาด / Shortage Reasons',
        compute='_compute_shortage_info',
    )
    shortage_notes = fields.Char(
        string='หมายเหตุสินค้าขาด / Shortage Notes',
        compute='_compute_shortage_info',
    )

    @api.depends('product_qty', 'qty_received')
    def _compute_qty_pending(self):
        for line in self:
            line.qty_pending = max(0.0, line.product_qty - line.qty_received)

    @api.depends('move_ids.shortage_reason', 'move_ids.shortage_note', 'move_ids.state')
    def _compute_shortage_info(self):
        for line in self:
            reasons = []
            notes = []
            for move in line.move_ids.filtered(lambda m: m.state == 'done'):
                if move.shortage_reason and move.shortage_reason != 'none':
                    reason_label = dict(move._fields['shortage_reason'].selection).get(move.shortage_reason, move.shortage_reason)
                    reasons.append(reason_label)
                if move.shortage_note:
                    notes.append(move.shortage_note)
            line.shortage_reasons = ", ".join(set(reasons)) if reasons else "—"
            line.shortage_notes = ", ".join(set(notes)) if notes else "—"



