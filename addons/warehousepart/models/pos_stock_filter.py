# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class ProductTemplatePos(models.Model):
    """
    ซ่อนสินค้าที่ไม่มีสต็อก (qty_available <= 0) ออกจาก POS
    รองรับ Odoo v19 ที่ใช้ type='consu' + is_storable=True
    """
    _inherit = 'product.template'

    def _get_pos_stock_tmpl_ids(self, company_id):
        """
        คืน set ของ product_tmpl_id ที่มีสต็อก > 0 ใน internal locations
        """
        self.env.cr.execute("""
            SELECT DISTINCT pp.product_tmpl_id
            FROM stock_quant sq
            JOIN stock_location sl ON sq.location_id = sl.id
            JOIN product_product pp ON sq.product_id = pp.id
            WHERE sl.usage = 'internal'
              AND sq.quantity > 0
              AND (sl.company_id = %s OR sl.company_id IS NULL)
        """, (company_id,))
        return {row[0] for row in self.env.cr.fetchall()}

    @api.model
    def _load_pos_data_fields(self, config_id):
        """เพิ่ม qty_available และ virtual_available เพื่อให้ POS Frontend ใช้ตรวจสต็อก"""
        fields = super()._load_pos_data_fields(config_id)
        if 'qty_available' not in fields:
            fields.append('qty_available')
        # virtual_available = qty_available - reserved (รวม web orders ที่ pending delivery)
        if 'virtual_available' not in fields:
            fields.append('virtual_available')
        return fields

    @api.model
    def _load_pos_data_search_read(self, data, config):
        """
        Override: กรองสินค้า is_storable ที่มี stock <= 0 ออกจากผลลัพธ์

        Odoo v19 มี 2 paths:
        1. limit_count path (SQL) — ไม่เรียก _load_pos_data_domain ของเรา
        2. normal path — เรียก _load_pos_data_domain
        เราจึง override ที่ระดับนี้เพื่อรองรับทั้ง 2 paths
        """
        # เรียก parent ก่อน (ให้ Odoo โหลดสินค้าตามปกติ)
        products_data = super()._load_pos_data_search_read(data, config)

        # ดึง tmpl_ids ที่มีสต็อก > 0
        tmpl_ids_with_stock = self._get_pos_stock_tmpl_ids(config.company_id.id)
        _logger.info(
            "WAREHOUSEPART: Found %d product templates with stock > 0",
            len(tmpl_ids_with_stock)
        )

        # กรองออก: สินค้า is_storable=True ที่ไม่มีสต็อก
        before = len(products_data)
        products_data = [
            p for p in products_data
            if not p.get('is_storable', False)  # ไม่ใช่ storable → แสดง
            or p['id'] in tmpl_ids_with_stock    # storable + มีสต็อก → แสดง
        ]
        after = len(products_data)
        _logger.info(
            "WAREHOUSEPART: Filtered products from %d → %d (removed %d out-of-stock)",
            before, after, before - after
        )

        return products_data

    def _notify_pos_stock_change(self):
        """
        ส่ง websocket / bus notification ไปยัง POS session ที่เปิดอยู่ทั้งหมด
        เพื่อให้อัปเดตสต็อก real-time โดยไม่ต้อง reload หน้าจอ
        """
        sessions = self.env['pos.session'].search([('state', '=', 'opened')])
        if not sessions:
            return

        updates = []
        for tmpl in self:
            if not tmpl.available_in_pos or not tmpl.is_storable:
                continue
            updates.append({
                'id': tmpl.id,
                'qty_available': tmpl.qty_available,
                # virtual_available = qty_available - reserved (หักของที่ web/SO จอง)
                'virtual_available': tmpl.virtual_available,
            })

        if not updates:
            return

        for session in sessions:
            try:
                _logger.info("WAREHOUSEPART: Notifying POS session %s of stock updates for %d templates", session.name, len(updates))
                session._notify('PRODUCT_STOCK_UPDATE', {
                    'updates': updates
                })
            except Exception as e:
                _logger.error("WAREHOUSEPART: Failed to notify POS session: %s", e)



class PosOrderStockCheck(models.Model):
    """
    ป้องกันการขายสินค้าเกินสต็อกจริงใน POS (Server-side validation)
    """
    _inherit = 'pos.order'

    def _process_saved_order(self, draft):
        """Override: ตรวจสอบสต็อกก่อนบันทึก order เป็น paid"""
        if not draft and not self.is_refund and self.state not in ('cancel', 'paid', 'done'):
            self._check_pos_stock_availability()
        return super()._process_saved_order(draft)

    def _check_pos_stock_availability(self):
        """ตรวจสอบสต็อกทุก line ใน order นี้"""
        self.ensure_one()

        picking_type = self.config_id.picking_type_id
        location_id = picking_type.default_location_src_id if picking_type else False

        product_qtys = {}
        for line in self.lines:
            product = line.product_id
            # v19: ใช้ is_storable แทน type=='product'
            if not product.is_storable:
                continue
            qty = line.qty
            if qty <= 0:
                continue
            product_qtys[product.id] = product_qtys.get(product.id, 0) + qty

        if not product_qtys:
            return

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        out_of_stock = []

        for product_id, qty_to_sell in product_qtys.items():
            product = self.env['product.product'].browse(product_id)
            if location_id:
                available_qty = product.with_context(location=location_id.id).qty_available
            else:
                available_qty = product.qty_available

            if float_compare(available_qty, qty_to_sell, precision_digits=precision) < 0:
                out_of_stock.append(
                    _("• %(product)s: ต้องการ %(need)g ชิ้น, มีในสต็อก %(have)g ชิ้น",
                      product=product.display_name,
                      need=qty_to_sell,
                      have=available_qty)
                )

        if out_of_stock:
            raise UserError(
                _("❌ ไม่สามารถยืนยันการขายได้ เนื่องจากสินค้าต่อไปนี้มีสต็อกไม่เพียงพอ:\n\n%(items)s\n\n"
                  "กรุณาลดจำนวนสินค้าหรือตรวจสอบสต็อกก่อนดำเนินการต่อ",
                  items="\n".join(out_of_stock))
            )


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_create_multi
    def create(self, vals_list):
        quants = super().create(vals_list)
        quants.mapped('product_id.product_tmpl_id')._notify_pos_stock_change()
        return quants

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['quantity', 'location_id', 'product_id']):
            self.mapped('product_id.product_tmpl_id')._notify_pos_stock_change()
        return res

    def unlink(self):
        templates = self.mapped('product_id.product_tmpl_id')
        res = super().unlink()
        templates._notify_pos_stock_change()
        return res


class StockMove(models.Model):
    """
    Hook บน stock.move เพื่อแจ้ง POS ทันทีเมื่อ virtual_available เปลี่ยน
    เช่น เมื่อเว็บ confirm order → stock reserved → virtual_available ลด
    ไม่ต้องรอ validate delivery (qty_available เปลี่ยน)
    """
    _inherit = 'stock.move'

    def write(self, vals):
        res = super().write(vals)
        # เมื่อ state เปลี่ยน (reserved, done, cancel) → virtual_available เปลี่ยน
        if 'state' in vals and vals['state'] in ('assigned', 'done', 'cancel'):
            templates = self.filtered(
                lambda m: m.product_id and m.product_id.is_storable
            ).mapped('product_id.product_tmpl_id').filtered(
                lambda t: t.available_in_pos
            )
            if templates:
                templates._notify_pos_stock_change()
        return res
