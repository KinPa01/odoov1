# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line._check_online_stock()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'product_uom_qty' in vals:
            for line in self:
                line._check_online_stock()
        return res

    def _check_online_stock(self):
        """
        ตรวจสอบสต็อกเฉพาะในคลัง ONLINE warehouse สำหรับ order ที่มาจาก website
        ป้องกันลูกค้าสั่งเกินสต็อกที่มีจริงในคลังออนไลน์
        """
        self.ensure_one()
        if not self.order_id.website_id:
            return  # ไม่ใช่ online order → ไม่ตรวจ

        product = self.product_id
        if not product or not product.is_storable:
            return  # ไม่ใช่ storable product → ไม่ตรวจ

        qty_needed = self.product_uom_qty
        if qty_needed <= 0:
            return

        # ใช้ warehouse ของ order (ถูก sale_order.py ตั้งเป็น website warehouse แล้ว)
        wh = self.order_id.warehouse_id
        online_qty = self.env['product.template'].sudo().get_warehouse_stock_by_id(
            product.product_tmpl_id.id, wh.id if wh else False
        )

        _logger.info(
            "WAREHOUSEPART: Online stock check — product=%s need=%.0f available_online=%.0f",
            product.display_name, qty_needed, online_qty
        )

        if online_qty < qty_needed:
            raise ValidationError(_(
                "ขออภัยครับ สินค้า %(product)s มีในคลังออนไลน์ %(online)g ชิ้น "
                "แต่ต้องการ %(need)g ชิ้น (มีคนสั่งซื้อไปก่อนหน้านี้)",
                product=product.display_name,
                online=online_qty,
                need=qty_needed,
            ))
