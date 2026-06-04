# -*- coding: utf-8 -*-
"""
Ran Ahlai — Flash Sale + Homepage Categories JSON API Controller (Odoo 19)
"""
import json
import random as _random
from datetime import datetime, timezone
from odoo import http
from odoo.http import request, Response

SLOT_HOURS = 8
EPOCH_START_TS = 1748217600  # 2025-05-26 00:00:00 UTC


def _calc_slot_info():
    """คำนวณ slot index และเวลาที่เหลือในรอบปัจจุบัน"""
    now_ts = datetime.now(timezone.utc).timestamp()
    elapsed = now_ts - EPOCH_START_TS
    slot_secs = SLOT_HOURS * 3600
    secs_into_slot = elapsed % slot_secs
    secs_left = slot_secs - secs_into_slot
    slot_index = int(elapsed // slot_secs)
    expires_at = int(now_ts + secs_left)
    return slot_index, int(secs_left), expires_at


def _shuffle_with_seed(items, seed):
    """สุ่มรายการโดยใช้ seed (slot_index) — ผู้ใช้ทุกคนในรอบเดียวกันจะเห็นสินค้าเดียวกัน"""
    items_copy = list(items)
    rng = _random.Random(seed)
    rng.shuffle(items_copy)
    return items_copy


class FlashSaleController(http.Controller):

    @http.route('/flash-sale/update-now', type='http', auth='user', website=True)
    def flash_sale_update_now(self, **kw):
        """
        Endpoint สำหรับ Admin กดอัปเดตส่วนลด Flash Sale แบบ Manual
        เข้าได้โดยพิมพ์ /flash-sale/update-now บน URL (ต้องล็อกอิน Admin)
        """
        FlashSale = request.env['warehousepart.flash.sale'].sudo()
        config = FlashSale.search([('active', '=', True)], limit=1)
        if config:
            config.action_update_discount()
            return request.redirect('/?flash_sale_updated=1')
        return "ไม่พบการตั้งค่า Flash Sale"

    @http.route('/flash-sale/data', type='http', auth='public', website=True, csrf=False)
    def flash_sale_data(self, **kw):
        """
        JSON API ส่งข้อมูล Flash Sale:
        - expires_at (Unix timestamp UTC) — เวลาสิ้นสุดรอบปัจจุบัน
        - slot_index — รอบปัจจุบัน (เปลี่ยนทุก 8 ชั่วโมง ใช้เป็น seed สำหรับ random)
        - products list พร้อมราคาที่ลดแล้ว (สุ่มใหม่ทุกรอบ)
        """
        slot_index, secs_left, expires_at = _calc_slot_info()

        FlashSale = request.env['warehousepart.flash.sale'].sudo()
        config = FlashSale.search([('active', '=', True)], limit=1)

        if not config:
            payload = {
                'expires_at': expires_at,
                'slot_index': slot_index,
                'secs_left': secs_left,
                'products': [],
                'discount_pct': 0,
            }
            return _json_response(payload)

        max_display = int(config.max_display_products or 4)

        # ดึงสินค้าทั้งหมดที่มีใน Flash Sale (รองรับทั้งระบบเลือกสินค้าเอง และระบบใช้ Tag)
        all_templates = config._get_flash_templates()

        # สุ่มโดยใช้ slot_index เป็น seed — รอบเดียวกัน = สินค้าชุดเดิม
        shuffled = _shuffle_with_seed(list(all_templates), seed=slot_index)
        selected = shuffled[:max_display]

        products = []
        for tmpl in selected:
            original_price = tmpl.list_price
            discount_pct = config.discount_percent
            sale_price = round(original_price * (1.0 - discount_pct / 100.0), 2)

            try:
                # ใช้คลังที่ตั้งค่าไว้ใน Website → Settings → Warehouse
                online_wh = request.website.warehouse_id
                online_qty = request.env['product.template'].get_warehouse_stock_by_id(
                    tmpl.id, online_wh.id if online_wh else False
                )
                in_stock = online_qty > 0
                qty_online = online_qty
            except Exception:
                in_stock = True
                qty_online = None

            products.append({
                'id': tmpl.id,
                'name': tmpl.name,
                'url': _get_product_url(request, tmpl),
                'image_url': f'/web/image/product.template/{tmpl.id}/image_512',
                'price': sale_price,
                'original_price': original_price,
                'discount_pct': int(discount_pct),
                'brand': getattr(tmpl, 'part_brand', '') or '',
                'in_stock': in_stock,
                'qty_online': qty_online,  # จำนวนในคลังออนไลน์ (None = ไม่รู้)
            })

        payload = {
            'expires_at': expires_at,
            'slot_index': slot_index,
            'secs_left': secs_left,
            'discount_pct': int(config.discount_percent),
            'total_products': len(all_templates),
            'products': products,
            'tag_id': config.tag_id.id if config.tag_id else False,
        }
        return _json_response(payload)

    @http.route('/homepage/categories', type='http', auth='public', website=True, csrf=False)
    def homepage_categories(self, **kw):
        """
        JSON API ส่งข้อมูลหมวดหมู่ที่ Admin กำหนดไว้สำหรับหน้าแรก
        Frontend จะ fetch endpoint นี้เพื่อ render กริดหมวดหมู่
        """
        cats = request.env['warehousepart.homepage.category'].sudo().search(
            [('active', '=', True)],
            order='sequence, id'
        )

        result = []
        for cat in cats:
            # สร้าง URL สำหรับ filter shop ตามหมวดหมู่
            if cat.website_categ_id:
                shop_url = f'/shop?categ_id={cat.website_categ_id.id}'
                categ_name = cat.website_categ_id.name
            else:
                shop_url = '/shop'
                categ_name = cat.name

            # นับสินค้าในหมวดนี้
            if cat.website_categ_id:
                try:
                    count = request.env['product.template'].sudo().search_count([
                        ('public_categ_ids', 'in', [cat.website_categ_id.id]),
                        ('is_published', '=', True),
                        ('active', '=', True),
                    ])
                except Exception:
                    count = 0
            else:
                count = 0

            result.append({
                'id': cat.id,
                'name': cat.name,
                'icon': cat.icon or '🔧',
                'url': shop_url,
                'product_count': count,
                'categ_name': categ_name,
            })

        payload = {'categories': result, 'count': len(result)}
        return _json_response(payload)

    @http.route('/homepage/best-sellers', type='http', auth='public', website=True, csrf=False)
    def homepage_best_sellers(self, **kw):
        """
        JSON API ส่งข้อมูลสินค้าแนะนำ (Best Sellers) ที่ Admin กำหนดไว้
        Frontend fetch ที่นี่เพื่อ render ส่วน Best Sellers บนหน้าแรก
        """
        products = request.env['warehousepart.homepage.product'].sudo().search(
            [('active', '=', True)],
            order='sequence, id'
        )

        result = []
        for item in products:
            tmpl = item.product_tmpl_id
            if not tmpl or not tmpl.active:
                continue

            try:
                # ใช้คลังที่ตั้งค่าไว้ใน Website → Settings → Warehouse
                online_wh = request.website.warehouse_id
                online_qty = request.env['product.template'].get_warehouse_stock_by_id(
                    tmpl.id, online_wh.id if online_wh else False
                )
                in_stock = online_qty > 0
                qty_online = online_qty
            except Exception:
                in_stock = True
                qty_online = None

            # Badge color mapping to CSS class
            color_map = {
                'red': '#e63946', 'orange': '#ff6b35',
                'gold': '#ffd700', 'green': '#2dc653', 'blue': '#4895ef'
            }
            badge_color = color_map.get(item.badge_color or 'red', '#e63946')

            result.append({
                'id': tmpl.id,
                'name': tmpl.name,
                'url': _get_product_url(request, tmpl),
                'image_url': f'/web/image/product.template/{tmpl.id}/image_512',
                'price': tmpl.list_price,
                'badge_text': item.badge_text or '',
                'badge_color': badge_color,
                'in_stock': in_stock,
                'qty_online': qty_online,  # จำนวนในคลังออนไลน์
                'sequence': item.sequence,
            })

        return _json_response({'products': result, 'count': len(result)})

    @http.route('/api/warehouse-stock/<int:product_tmpl_id>', type='http', auth='public', website=True, csrf=False)
    def warehouse_stock(self, product_tmpl_id, **kw):
        """
        JSON API: ดูสต็อกแยกตามคลังของ product
        GET /api/warehouse-stock/42
        Response: { "product_id": 42, "pos_qty": 6.0, "online_qty": 4.0 }
        """
        try:
            Product = request.env['product.template']
            pos_qty = Product.get_warehouse_stock(product_tmpl_id, 'POS')
            online_qty = Product.get_warehouse_stock(product_tmpl_id, 'ONLIN')
            tmpl = request.env['product.template'].sudo().browse(product_tmpl_id)
            return _json_response({
                'product_id': product_tmpl_id,
                'product_name': tmpl.name if tmpl.exists() else '',
                'pos_qty': pos_qty,      # สต็อกหน้าร้าน
                'online_qty': online_qty, # สต็อกออนไลน์
                'total_qty': pos_qty + online_qty,
            })
        except Exception as e:
            return _json_response({'error': str(e)})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_product_url(req, tmpl):
    """สร้าง URL สินค้าที่คลิกได้"""
    try:
        if hasattr(req.env['ir.http'], '_slug'):
            slug = req.env['ir.http']._slug(tmpl)
            return f'/shop/{slug}'
    except Exception:
        pass
    try:
        safe_name = ''.join(
            c if c.isalnum() or c == '-' else '-'
            for c in tmpl.name.lower().replace(' ', '-')
        ).strip('-')
        return f'/shop/{safe_name}-{tmpl.id}'
    except Exception:
        return f'/shop?product_id={tmpl.id}'


def _json_response(payload):
    """สร้าง JSON Response พร้อม header ที่ถูกต้อง"""
    return Response(
        json.dumps(payload, ensure_ascii=False),
        content_type='application/json; charset=utf-8',
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'Access-Control-Allow-Origin': '*',
        }
    )
