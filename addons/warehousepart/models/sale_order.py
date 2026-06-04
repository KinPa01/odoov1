# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_received = fields.Boolean(
        string="Customer Received",
        default=False,
        help="Indicates if the customer has manually confirmed receipt of the order.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create: ถ้า order มาจาก website (มี website_id) ให้ผูก warehouse
        กับ warehouse ที่กำหนดไว้ใน website นั้น (คลังอะไหล่ออนไลน์)
        """
        orders = super().create(vals_list)
        for order in orders:
            order._set_online_warehouse_if_needed()
        return orders

    def _set_online_warehouse_if_needed(self):
        """
        ถ้า order นี้มี website_id (มาจาก eCommerce) และ website นั้น
        กำหนด warehouse_id ไว้ → ใช้ warehouse นั้นเป็น source
        ถ้า warehouse ของ website ไม่ได้ตั้งค่าไว้ → Fallback หา warehouse_online
        """
        self.ensure_one()
        if not self.website_id:
            return  # ไม่ใช่ order จาก website → ไม่แตะ

        # ดึง warehouse จาก website config ก่อน (ตั้งค่าไว้ใน warehouse_setup.xml)
        target_warehouse = self.website_id.warehouse_id
        if not target_warehouse:
            # Fallback: ค้นหา warehouse ที่ชื่อ "คลังออนไลน์" โดยตรง
            target_warehouse = self.env['stock.warehouse'].search(
                [('code', '=', 'ONLIN')], limit=1
            )

        if target_warehouse and target_warehouse != self.warehouse_id:
            _logger.info(
                "WAREHOUSEPART: Online order %s → set warehouse to '%s' (was: '%s')",
                self.name or '(new)',
                target_warehouse.name,
                self.warehouse_id.name if self.warehouse_id else 'unset',
            )
            self.warehouse_id = target_warehouse

