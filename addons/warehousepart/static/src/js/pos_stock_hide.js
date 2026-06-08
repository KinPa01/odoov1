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
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

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
                    console.log(`WAREHOUSEPART: Updating product ${tmpl.display_name} stock: qty_available=${update.qty_available}, virtual_available=${update.virtual_available}`);
                    tmpl.update({
                        qty_available: update.qty_available,
                        virtual_available: update.virtual_available,
                    });
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
            // ใช้ virtual_available (หัก reserved จาก web orders ด้วย)
            // ถ้าไม่มีข้อมูล → fallback ไปใช้ qty_available
            const qty = product.virtual_available ?? product.qty_available;
            if (qty === undefined || qty === null) {
                return true; // ถ้าไม่มีข้อมูล → แสดงไว้ก่อน
            }
            return qty > 0;
        });
    },
});

// ============================================================
// PATCH 2: จำกัดจำนวนสินค้าในตะกร้าไม่ให้เกินสต็อกจริง
// ============================================================
patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        if (product.is_storable) {
            // ใช้ virtual_available = qty_available - reserved (รวม web orders ที่ pending)
            // ถ้าไม่มี virtual_available ให้ fallback ไปใช้ qty_available
            const maxQty = product.virtual_available ?? product.qty_available;

            // ถ้าสต็อกเป็น 0 หรือน้อยกว่า → บล็อกทันที
            if (maxQty !== undefined && maxQty !== null && maxQty <= 0) {
                this.dialog.add(AlertDialog, {
                    title: _t("สินค้าหมด"),
                    body: _t(
                        '"%s" ไม่มีสต็อกคงเหลือ ไม่สามารถเพิ่มในบิลได้',
                        product.display_name || product.name
                    ),
                });
                return;
            }

            // คำนวณจำนวนที่อยู่ในตะกร้า (Odoo v19: this.currentOrder.lines)
            if (maxQty !== undefined && maxQty !== null) {
                // Odoo v19 ใช้ this.currentOrder.lines (ดูจาก product_screen.js บรรทัด ~120)
                const lines = this.currentOrder?.lines || [];
                let qtyInCart = 0;
                for (const ol of lines) {
                    try {
                        // Odoo v19: ol.product_id.product_tmpl_id.id เปรียบกับ product.id
                        if (ol.product_id?.product_tmpl_id?.id === product.id) {
                            qtyInCart += (ol.qty || 0);
                        }
                    } catch (_) {}
                }

                // ถ้าจำนวนในตะกร้า >= สต็อก → บล็อก
                if (qtyInCart >= maxQty) {
                    this.dialog.add(AlertDialog, {
                        title: _t("สต็อกไม่เพียงพอ"),
                        body: _t(
                            '"%s" มีสต็อกเหลือ %s ชิ้น และในบิลมีแล้ว %s ชิ้น ไม่สามารถเพิ่มได้อีก',
                            product.display_name || product.name,
                            maxQty,
                            qtyInCart
                        ),
                    });
                    return;
                }
            }
        }

        // ถ้าสต็อกเพียงพอ → เรียก parent ปกติ
        return super.addProductToOrder(product);
    },
});

// ============================================================
// PATCH 3: แสดง Flash Sale badge บน POS product card
// ============================================================
// Odoo v19 POS ใช้ OWL component — เพิ่ม CSS ผ่าน document สำหรับ flash sale marker
(function initPosFlashSaleBadges() {
    // ใส่ CSS สำหรับ flash sale badge บน POS
    const style = document.createElement('style');
    style.textContent = `
        /* ── POS Flash Sale Badge ─────────────────────────── */
        .product-list .product-info-badge-flash {
            display: inline-block;
            background: linear-gradient(135deg, #e63946, #ff6b35);
            color: #fff;
            font-size: 0.6rem;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 3px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-left: 4px;
            vertical-align: middle;
            animation: pos-flash-pulse 2s infinite;
        }

        @keyframes pos-flash-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.75; }
        }

        /* ── POS Low Stock indicator ──────────────────────── */
        .product-list .product-info-low-stock {
            display: inline-block;
            background: rgba(255, 165, 0, 0.2);
            border: 1px solid rgba(255, 165, 0, 0.5);
            color: #ffb347;
            font-size: 0.55rem;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            margin-left: 4px;
            vertical-align: middle;
        }
    `;
    document.head.appendChild(style);

    // Observer สำหรับ POS product cards (Odoo v19 OWL render ใช้ mutation observer)
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType !== 1) continue;
                // ตรวจสอบ product cards ที่เพิ่มใหม่
                const productItems = node.querySelectorAll
                    ? node.querySelectorAll('.product-name, .product-info')
                    : [];
                productItems.forEach(el => annotatePosProduct(el));
            }
        }
    });

    function annotatePosProduct(el) {
        // หา product data จาก parent .product
        const card = el.closest('.product');
        if (!card || card._flashAnnotated) return;
        card._flashAnnotated = true;

        // ตรวจจาก data attribute หรือ text
        const priceEl = card.querySelector('.price-tag');
        const nameEl = card.querySelector('.product-name');
        if (!priceEl || !nameEl) return;

        // ถ้าราคาถูกกว่าปกติ (is_flash_sale ถูกตั้งผ่าน pricelist) → แสดง badge
        // ใช้ data attribute ที่ Odoo inject ถ้ามี
        const isFlashSale = card.dataset.isFlashSale === 'true';
        const qty = parseFloat(card.dataset.qtyAvailable || '999');

        if (isFlashSale && !nameEl.querySelector('.product-info-badge-flash')) {
            const badge = document.createElement('span');
            badge.className = 'product-info-badge-flash';
            badge.textContent = '⚡ SALE';
            nameEl.appendChild(badge);
        }

        if (qty > 0 && qty <= 5 && !nameEl.querySelector('.product-info-low-stock')) {
            const badge = document.createElement('span');
            badge.className = 'product-info-low-stock';
            badge.textContent = `⚠ เหลือ ${Math.floor(qty)}`;
            nameEl.appendChild(badge);
        }
    }

    // เริ่ม observe เมื่อ POS DOM พร้อม
    function startObserving() {
        const posRoot = document.querySelector('.pos-content, #pos-content, .pos');
        if (posRoot) {
            observer.observe(posRoot, { childList: true, subtree: true });
            // Annotate items ที่มีอยู่แล้ว
            posRoot.querySelectorAll('.product-name, .product-info').forEach(el => annotatePosProduct(el));
        } else {
            // ยังไม่พร้อม รอ
            setTimeout(startObserving, 500);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startObserving);
    } else {
        startObserving();
    }
})();
