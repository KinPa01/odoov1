# -*- coding: utf-8 -*-
from odoo import models

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        """ Override of `payment` to add auto-confirm for Wire Transfers """
        super()._post_process()

        for pending_tx in self.filtered(lambda tx: tx.state == 'pending' and tx.provider_code == 'custom'):
            sales_orders = pending_tx.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent'])
            if sales_orders:
                # ยืนยัน order ทันทีเมื่อลูกค้าโอนเงิน เพื่อตัดสต็อกทันที (ไม่ให้หน้าร้านขายซ้ำ)
                sales_orders.with_context(send_email=True).action_confirm()
                for order in sales_orders:
                    order.message_post(body="✅ ยืนยันคำสั่งซื้ออัตโนมัติ (ชำระผ่านการโอนเงิน) เพื่อจองสินค้าป้องกันสินค้าหมด")
