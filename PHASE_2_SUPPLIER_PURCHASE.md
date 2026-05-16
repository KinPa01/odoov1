# 📋 Phase 2 — Supplier & Purchase Implementation Report

## ✅ แล้วเสร็จ (COMPLETED)

### 1. **Supplier Model (spare.supplier)** 
- ✅ Code, Name, Contact Person
- ✅ Phone, Email, Address  
- ✅ Payment Terms (Cash, Credit 7/15/30/60 days)
- ✅ Lead Time (days)
- ✅ Currency Support (THB, USD, JPY)
- ✅ Active/Inactive toggle
- ✅ Tracking & Activity Log
- ✅ Button to view products from this supplier

**File:** `models/spare_supplier.py`

---

### 2. **Vendor Price Model (spare.vendor.price)** ✨ NEW!
- ✅ Link to spare.part (Storable) + spare.supplier
- ✅ Supplier's own code/SKU
- ✅ Price Unit (สกุลเงิน THB/USD/JPY)
- ✅ Min Qty (ปริมาณขั้นต่ำสำหรับราคานี้)
- ✅ Lead Time (override supplier's default)
- ✅ Currency auto-convert to THB (estimate)
- ✅ Margin % calculation vs Sales Price
- ✅ Is Default flag (ใช้ราคานี้เป็นหลัก)
- ✅ Unique constraint: 1 supplier per part (ห้ามซ้ำ)

**File:** `models/spare_vendor_price.py`

**Formula:**
```
Cost THB = Price Unit × Exchange Rate
Margin % = (Sales Price - Cost THB) / Sales Price × 100
```

---

### 3. **Purchase Order Model (spare.purchase.order)**
- ✅ Auto-generated PO Number
- ✅ Supplier Selection
- ✅ Order Date, Expected Delivery Date
- ✅ State workflow: Draft → Confirmed → Received → Cancel
- ✅ Line items with:
  - Part ID
  - Description
  - Qty
  - Unit Price
  - Subtotal (auto-calc)
- ✅ Total Amount calculation
- ✅ Auto-receive function (updates inventory + cost)
- ✅ Costing Method: Average Cost (AVCO)

**File:** `models/spare_purchase.py`

**Auto-receipt logic:**
```
When "Receive" button clicked:
  - qty_on_hand += received_qty
  - If AVCO: avg_cost = (old_qty×old_cost + new_qty×new_price) / new_qty
  - State → "received"
```

---

### 4. **UI/Views Updates**

#### spare_part_views.xml
- ✅ Added "ราคาซื้อจากผู้จัดจำหน่าย" tab
- ✅ Inline tree view of vendor prices
- ✅ Shows: Supplier, Code, Price, Currency, Lead Time, Margin%

#### spare_supplier_views.xml  
- ✅ List view: code, name, contact, phone, email, payment_term, lead_time, part_count
- ✅ Form view: company info, terms, contact, address, notes, activity log

#### spare_purchase_views.xml (existing, updated)
- ✅ List: PO number, supplier, date, expected date, total, state (badge)
- ✅ Form: Header (state workflow), supplier info, line items, notes, activity
- ✅ Buttons: Confirm, Receive, Cancel, Draft

#### spare_vendor_price_views.xml ✨ NEW!
- ✅ List: part, supplier, code, price, currency, cost_thb, qty, lead_time, margin%, default flag
- ✅ Form: Part + Supplier, price fields, terms, gauge widget for margin
- ✅ Inline tree for embedded use

---

### 5. **Menu Integration**
- ✅ Menu item: "ราคาซื้อจากผู้จัดจำหน่าย" under "🛒 การจัดซื้อ"
- ✅ Menu item: "🏭 ผู้จัดจำหน่าย" (main)
- ✅ Menu item: "ใบสั่งซื้อ (PO)" under "🛒 การจัดซื้อ"

**File:** `views/menu_views.xml`

---

### 6. **Access Control (Security)**
- ✅ `spare.vendor.price` read-only for group_warehousepart_user
- ✅ `spare.vendor.price` full CRUD for group_warehousepart_manager
- ✅ `spare.supplier` read-only for group_warehousepart_user  
- ✅ `spare.supplier` full CRUD for group_warehousepart_manager
- ✅ `spare.purchase.order` (read/write) for group_warehousepart_user
- ✅ `spare.purchase.order` (full CRUD) for group_warehousepart_manager

**File:** `security/ir.model.access.csv`

---

### 7. **Demo Data** 📦

#### Suppliers (3 ตัว)
- SUP-001: บริษัท ท็อปออย จำกัด (Lead Time: 3 วัน, Credit 30)
- SUP-002: ห้างหุ้นส่วน ฟิลเตอร์โปร (Lead Time: 2 วัน, Credit 15)
- SUP-003: บริษัท แบตเตอรี่ไทย จำกัด (Lead Time: 5 วัน, Credit 30)

**File:** `data/spare_supplier_demo.xml`

#### Vendor Prices (6 records)
- OIL-10W40-001 ← SUP-001 @ 520 THB ✓ Default
- OIL-5W30-001 ← SUP-001 @ 750 THB ✓ Default
- BRK-VIOS-001 ← SUP-001 @ 650 THB ✓ Default
- BRK-CITY-001 ← SUP-001 @ 480 THB ✓ Default
- FIL-HONDA-001 ← SUP-002 @ 90 THB ✓ Default (min qty: 10)
- FIL-HONDA-001 ← SUP-001 @ 95 THB (alternate supplier, min qty: 1)

**File:** `data/spare_vendor_price_demo.xml`

#### Purchase Orders (3 example POs)
- **PO/2025/0001** (Draft): Top Oil - น้ำมัน 10W40 ×12 + 5W30 ×6
- **PO/2025/0002** (Draft): Filter Pro - กรองน้ำมัน Honda ×30
- **PO/2025/0003** (Confirmed): Top Oil - ผ้าเบรก Vios ×10 + City ×8

**File:** `data/spare_purchase_order_demo.xml`

---

## 🧪 Testing Checklist

- [ ] Install warehousepart module
- [ ] Check supplier list (3 suppliers visible)
- [ ] Check vendor price list (6 prices visible)
- [ ] Create new supplier
- [ ] Create new vendor price
- [ ] Edit existing vendor price
- [ ] Create PO from scratch
- [ ] Add PO lines with auto-pricing
- [ ] Confirm PO (state: Draft → Confirmed)
- [ ] Receive PO → Check inventory updated
- [ ] Check Cost calculation (AVCO)
- [ ] View vendor prices in Product form tab
- [ ] Verify Margin % calculation
- [ ] Test currency conversion (USD/JPY to THB)
- [ ] Test unique constraint (no duplicate part+supplier)
- [ ] Access control: User can read, Manager can CRUD

---

## 📊 Data Model Relationships

```
spare.supplier (ผู้จัดจำหน่าย)
    ├─ 1:Many → spare.vendor.price
    └─ 1:Many → spare.purchase.order

spare.part (สินค้า)
    ├─ 1:Many → spare.vendor.price
    └─ Many:1 ← spare.supplier (primary)

spare.vendor.price (ราคาซื้อ)
    ├─ Many:1 → spare.part
    └─ Many:1 → spare.supplier

spare.purchase.order (ใบสั่งซื้อ)
    ├─ Many:1 → spare.supplier
    ├─ 1:Many → spare.purchase.order.line
    └─ Many:1 ← spare.part (via line)

spare.purchase.order.line (รายการสั่งซื้อ)
    ├─ Many:1 → spare.purchase.order
    └─ Many:1 → spare.part
```

---

## 🚀 Ready for Phase 3

✅ **Phase 2 Supplier & Purchase** — เสร็จสมบูรณ์ พร้อมทดสอบ

**Next Phase:** Phase 3 — Inventory & Location

---

**Last Updated:** 2025-05-15  
**Module Version:** 19.0.1.0.0  
**Status:** ✅ READY FOR TESTING
