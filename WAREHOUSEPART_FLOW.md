# Warehousepart System - Complete Flow

## Overview
Warehousepart is a customized Odoo 19 system for Ran Ahlai auto spare parts shop.
It supports both online (website) and offline (POS) sales channels.

---

## 1. Spare Parts Management

**Model**: ProductTemplate + Custom Fields

Custom Fields:
- Brand (ยี่ห้อ): part_brand
- Fitment (รุ่นรถ): car_model
- Shelf Location (ชั้นวาง): shelf_location
- Webike URL: webike_url
- Webike SKU: webike_sku

Display Requirements:
- Website: is_published=True AND active=True
- POS: qty > 0 (auto-hide zero stock)
- Categories and Tags: Linked via product.product_tag_ids

---

## 2. Quick Transfer (Inventory Movement)

**Model**: SpareQuickTransfer (Transient Wizard)

Flow:
1. Select source warehouse (location_src_id)
2. Select destination warehouse (location_dest_id) - must be different
3. Add product lines with quantities
4. System shows available qty in source location (Real-time)
5. Validation: different locations, qty > 0, at least 1 product
6. Create Stock Picking (Internal Transfer type)
7. Confirm and assign (triggers stock reservation)

---

## 3. Flash Sale System

**Model**: FlashSaleSession

Characteristics:
- **Slot**: 8-hour rotation (SLOT_HOURS = 8)
- **Randomization**: Seed = slot_index (all users in same round see same products)
- **Discount**: discount_percent (default 20%)
- **Max Display**: max_display_products (default 4)
- **Active**: Toggle to enable/disable

Two Modes:
1. **Direct**: Admin selects products manually (flash_product_ids)
2. **Tag**: Uses Product Tag as fallback (tag_id)

Action: action_update_discount() 
- Deletes old Flash Sale price items
- Creates new Pricelist Items with discount
- Updates all Pricelists globally

API Endpoint:
- URL: /flash-sale/data
- Method: GET
- Auth: public
- Response: JSON with expires_at, slot_index, secs_left, products[], discount_pct

---

## 4. Homepage Management

**HomepageCategory**:
- name: Display name (shown on homepage)
- icon: Emoji (e.g., bolt, wrench, oil, etc.)
- website_categ_id: Link to Product Category
- sequence: Display order
- active: Show/hide toggle
- product_count: Computed field

**HomepageFeaturedProduct**:
- product_tmpl_id: Product (published + active only)
- badge_text: Badge label (BEST SELLER, HOT, NEW, SALE)
- badge_color: Color (red, orange, gold, green, blue)
- sequence: Display order

Management: Backend → Ran Ahlai → Website → Featured Products

---

## 5. E-commerce + Customer Portal

### Purchase Flow:
1. Customer browses website
2. Add products to cart
3. Go to checkout
4. Select payment method: Wire Transfer
5. Customer transfers money manually to account
   (Outside Odoo - manual process currently)
6. Admin marks payment as complete in Odoo
7. Payment Transaction created (provider_code: 'custom')
8. _post_process() triggered:
   - Auto-confirm SaleOrder
   - Stock immediately reserved
   - Message posted to order
9. Warehouse picks → packs → ships
10. Customer receives order
11. Customer clicks "Confirm Received" in portal
12. Order marked completed (customer_received = True)

### SaleOrder Extensions:
- customer_received: Boolean (False by default, True when customer confirms)

### Customer Portal:
- URL: /my/orders
- Tabs: TO PAY, TO SHIP, TO RECEIVE, COMPLETED, CANCELLED, ALL
- Tab badges show order count
- Sortable by date, total, status
- Date range filtering available
- "Confirm Received" button triggers customer_received=True

---

## 6. Point of Sale (POS)

### Stock Filter (pos_stock_filter.py):
- Purpose: Hide products with qty=0 from POS display
- Benefit: Reduces confusion, speeds up cashier workflow

### Web Sync (pos_web_sync.py):
- Purpose: Real-time synchronization between POS and backend
- Syncs: Stock updates, price changes, new products

### Custom Receipt (pos_receipt.xml):
- Purpose: Modified receipt template
- Includes: Logo, shop name, item formatting, payment details

### POS Enhancements (pos_enhancements.xml):
- UI improvements, keyboard shortcuts, quick action buttons

### Custom Styling (pos_custom.scss):
- Visual design: Colors, fonts, button styles, responsive layout

---

## 7. Security & Access Control

**File**: security/spare_security.xml + ir.model.access.csv

**Role-Based Access**:

Admin/Owner: Full access to all operations
Sales Manager: Orders, customers, reporting (cannot modify cost)
Cashier: POS sales, payment, cannot modify inventory/cost
Warehouse Staff: Stock, picking, transfers only
Customer: View own orders only

**IR Rules**: Define data visibility boundaries per group

---

## 8. Key APIs & Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| /flash-sale/data | GET | public | Get Flash Sale products |
| /flash-sale/update-now | GET | user | Admin update discounts |
| /my/orders | GET | user | Customer portal |
| /my/orders/receive/<id> | POST | user | Confirm receipt |

---

## 9. Data Models

| Model | Type | Purpose |
|-------|------|---------|
| ProductTemplate | Inherited | Product with custom fields |
| SaleOrder | Inherited | Sales order with customer_received |
| SpareQuickTransfer | Transient | Inventory transfer wizard |
| FlashSaleSession | Standalone | Flash sale configuration |
| HomepageCategory | Standalone | Homepage category display |
| HomepageFeaturedProduct | Standalone | Featured products display |
| PaymentTransaction | Inherited | Auto-confirm on payment |

---

## 10. Module Dependencies

base, mail, product, point_of_sale, stock, purchase, website_sale, website, hr, pos_hr, account, l10n_th (Thailand), delivery

---

## 11. Master Data Files

- ran_ahlai_master_data.xml: Standard products
- ran_ahlai_master_data_bulk.xml: Bulk product imports
- demo_tracking_data.xml: Sample order data
- website_pages.xml: Static pages (About, Contact)
- flash_sale_data.xml: Default Flash Sale config

---

## 12. File Structure

warehousepart/
  models/
    - spare_part.py (Product extensions)
    - spare_quick_transfer.py (Transfer wizard)
    - flash_sale.py (Flash sale + homepage)
    - sale_order.py (Sales order extensions)
    - payment_transaction.py (Payment auto-confirm)
  controllers/
    - flash_sale_controller.py (API)
    - portal.py (Customer portal)
  views/ (UI templates)
  security/ (Access control)
  data/ (Master data XML)
  static/ (CSS, JS, templates)

---

## 13. Frontend Assets

**Website** (web.assets_frontend):
- minimal_shop.scss: Shop styling
- website_frontend.js: Dynamic interactions

**POS** (point_of_sale.assets_prod):
- pos_receipt.xml: Receipt template
- pos_stock_hide.js: Hide zero items
- pos_enhancements.xml: UI enhancements
- pos_custom.scss: POS styling

---

## 14. Common Workflows

**Admin**:
1. Manage products (brand, fitment, shelf)
2. Setup Flash Sale (discount %, products)
3. Configure homepage (categories, featured)
4. Monitor orders and payments

**Warehouse**:
1. Quick transfer inventory between shelves
2. Check stock levels
3. Receive new purchases
4. Prepare orders for shipping

**POS Cashier**:
1. Scan barcode to add item
2. Receive payment (cash/transfer/card)
3. Print receipt
4. Handle returns

**Customer**:
1. Browse website
2. Add to cart and checkout
3. Pay via wire transfer
4. Track order in portal
5. Confirm receipt

---

**Module**: warehousepart  
**Version**: 19.0.2.0.0  
**Name**: ร้านอาหลั่ย — ระบบจัดการอะไหล่รถยนต์  
**Author**: Ran Ahlai  
**Category**: Inventory  
**Date**: May 28, 2026