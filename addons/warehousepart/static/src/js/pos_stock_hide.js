/** @odoo-module **/
/**
 * warehousepart/static/src/js/pos_stock_hide.js
 *
 * กรองสินค้าหมดสต็อกออกจาก POS ด้วย 2 วิธีพร้อมกัน:
 * 1. patch PosStore.filterExcludedProducts — ซ่อนจาก product grid
 * 2. patch ProductScreen.addProductToOrder — block ก่อน add to cart
 *
 * รองรับ Odoo v19: is_storable=True = สินค้ามี inventory tracking
 */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { _t } from "@web/core/l10n/translation";

// ============================================================
// PATCH 1: ซ่อนสินค้าหมดสต็อกจาก product grid
// ============================================================
patch(PosStore.prototype, {
    async initServerData() {
        const res = await super.initServerData();
        // เชื่อมต่อ websocket สำหรับ PRODUCT_STOCK_UPDATE
        this.data.connectWebSocket("PRODUCT_STOCK_UPDATE", this.productStockUpdateNotification.bind(this));
        return res;
    },

    productStockUpdateNotification(data) {
        console.log("WAREHOUSEPART: Received stock update via WebSocket", data);
        if (data && data.updates) {
            for (const update of data.updates) {
                const tmpl = this.models["product.template"].get(update.id);
                if (tmpl) {
                    console.log(`WAREHOUSEPART: Updating product ${tmpl.display_name} (ID: ${tmpl.id}) stock to ${update.qty_available}`);
                    tmpl.update({ qty_available: update.qty_available });
                }
            }
        }
    },

    filterExcludedProducts(products) {
        const baseResult = super.filterExcludedProducts(products);
        return baseResult.filter((product) => {
            if (!product.is_storable) {
                return true; // service/non-tracked → แสดงเสมอ
            }
            const qty = product.qty_available;
            if (qty === undefined || qty === null) {
                return true; // ถ้าไม่มีข้อมูล → แสดงไว้ก่อน
            }
            return qty > 0;
        });
    },
});

// ============================================================
// PATCH 2: Block การเพิ่มสินค้าหมดสต็อกเข้าตะกร้า (safety net)
// ============================================================
patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        // ตรวจสอบ stock ก่อน add to cart
        if (product.is_storable) {
            const qty = product.qty_available;
            if (qty !== undefined && qty !== null && qty <= 0) {
                this.dialog.add(
                    (await import("@web/core/confirmation_dialog/confirmation_dialog"))
                        .AlertDialog,
                    {
                        title: _t("สินค้าหมด"),
                        body: _t(
                            '"%s" ไม่มีสต็อกคงเหลือ ไม่สามารถเพิ่มในบิลได้',
                            product.display_name || product.name
                        ),
                    }
                );
                return; // หยุดไม่ให้ add to cart
            }
        }
        // ถ้าสต็อกเพียงพอ → เรียก parent ปกติ
        return super.addProductToOrder(product);
    },
});
