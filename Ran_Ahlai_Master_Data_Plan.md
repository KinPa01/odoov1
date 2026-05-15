# 📋 Odoo Ran Ahlai — Master Data Flow แผนทำทีละขั้นตอน

> เอกสารอ้างอิง: `Odoo_Ran_Ahlai_Master_Data_Flow_Detailed.docx`  
> โมดูลปัจจุบัน: `warehousepart` (Custom Odoo Module)

---

## 🗺️ ภาพรวม — 6 หมวดหลัก (ตามลำดับที่ต้องทำ)

| ลำดับ | หมวด | สถานะ |
|-------|------|--------|
| 1 | **Product Master Data** — SKU, Barcode, Cost, Price, Category | 🔲 รอทำ |
| 2 | **Supplier & Purchase** — Vendor, ราคาซื้อ, Lead Time | 🔲 รอทำ |
| 3 | **Inventory & Location** — คลัง, ชั้นวาง, Opening Stock | 🔲 รอทำ |
| 4 | **POS & Payment Method** — จุดขาย, วิธีรับเงิน, Barcode | 🔲 รอทำ |
| 5 | **User Roles & Access Rights** — Admin, Manager, Cashier, Stock Staff | 🔲 รอทำ |
| 6 | **Website / eCommerce** — เปิดหลังสุด เมื่อ POS นิ่งแล้ว | 🔲 ทำภายหลัง |

---

## 📦 Phase 1 — Product Master Data

### Fields ที่ต้องมีในแต่ละสินค้า

| Field | จำเป็น | ตัวอย่าง |
|-------|--------|---------|
| SKU / Internal Reference | ✅ ต้องมี | `BRK-VIOS-001` |
| Barcode | ✅ ควรมี | `885100000001` |
| Product Name | ✅ ต้องมี | ผ้าเบรกหน้า Toyota Vios |
| Category | ✅ ต้องมี | ระบบเบรก |
| Brand | ควรมี | Bendix |
| Car Model / Fitment | ควรมี | Toyota Vios 2013-2018 |
| Unit of Measure | ✅ ต้องมี | ชิ้น / ชุด / ลิตร |
| Product Type | ✅ ต้องมี | Storable Product |
| Cost | ✅ ต้องมี | 650 |
| Sales Price | ✅ ต้องมี | 950 |
| Vendor / Supplier | ควรมี | SUP-001 |
| Stock Location | ควรมี | B1 |
| Min / Max Stock | ควรมี | 3 / 20 |
| Available in POS | ✅ ต้องกำหนด | Yes |
| Tax | ✅ ต้องกำหนด | VAT 7% |
| Costing Method | ✅ ต้องกำหนด | Average Cost |
| Tracking | ตามสินค้า | No Tracking / Lot / Serial |

### หมวดสินค้า (Product Category)

| Code | ชื่อหมวด | ตัวอย่าง |
|------|---------|---------|
| OIL | น้ำมันเครื่อง | 10W-40, 5W-30 |
| BRK | ระบบเบรก | ผ้าเบรก, จานเบรก |
| FIL | กรอง | กรองน้ำมัน, กรองอากาศ |
| BAT | แบตเตอรี่ | NS40, NS60 |
| SUS | ช่วงล่าง | โช้ค, ลูกหมาก |
| ELEC | ระบบไฟ | หลอดไฟ, ฟิวส์ |

### ตัวอย่างสินค้าในระบบ

| SKU | สินค้า | ต้นทุน | ราคาขาย | Margin |
|-----|-------|--------|---------|--------|
| OIL-10W40-001 | น้ำมันเครื่อง 10W-40 | 520 | 690 | 24.64% |
| BRK-VIOS-001 | ผ้าเบรกหน้า Vios | 650 | 950 | 31.58% |
| FIL-HONDA-001 | กรองน้ำมัน Honda | 90 | 180 | 50.00% |
| BAT-NS60-001 | แบตเตอรี่ NS60 | 1,450 | 2,100 | 30.95% |
| SUS-VIGO-001 | ลูกหมากปีกนก Vigo | 380 | 650 | 41.54% |

---

## 🏭 Phase 2 — Supplier & Purchase

- ต้องมี Supplier Record ก่อน สร้าง Purchase Order
- Field ที่สำคัญ: Vendor Name, ราคาซื้อต่อ SKU, Lead Time, Currency
- ต้องเชื่อม Vendor Price ใน Product form ด้วย

---

## 📍 Phase 3 — Inventory & Location

### Stock Location ที่ต้องตั้ง
- คลังหลักของร้าน (Warehouse)
- ชั้นวาง A1, B1, C1, D1, E1 (ตรงกับ Location field ในสินค้า)

### Opening Stock
- นับของจริงแล้วใส่เข้าระบบก่อน Go-live
- ใช้ Inventory Adjustment

### Reordering Rules

| SKU | Min Qty | Max Qty | Supplier |
|-----|---------|---------|---------|
| BRK-VIOS-001 | 3 | 20 | SUP-001 |
| FIL-HONDA-001 | 10 | 50 | SUP-002 |
| BAT-NS60-001 | 2 | 10 | SUP-003 |
| OIL-10W40-001 | 6 | 36 | SUP-001 |

---

## 🖥️ Phase 4 — POS & Payment Method

- **Payment Methods ที่ต้องตั้ง:** เงินสด, โอน, QR Code, บัตร
- **Available in POS = True** สำหรับทุกสินค้าที่ขายหน้าร้าน
- ตั้ง Barcode ให้ถูกต้องเพื่อใช้ยิงขาย POS

### Pricelist

| Pricelist | ใช้กับ | เงื่อนไข |
|-----------|-------|---------|
| Retail Price | ลูกค้าทั่วไป | Sales Price มาตรฐาน |
| Garage Price | อู่ซ่อมรถ | ลด 10% |
| Member Price | สมาชิก | ลด 5% |
| Online Price | ลูกค้าออนไลน์ | รวมค่าจัดส่ง |

---

## 👤 Phase 5 — User Roles & Access Rights

| Role | ทำได้ | ทำไม่ได้ |
|------|-------|---------|
| Admin / Owner | ตั้งค่าทุกอย่าง, Config | — |
| Store Manager | จัดการสินค้า, ราคา, รายงาน, คืนเงิน | — |
| Cashier | ขาย POS, รับเงิน, คืนเงินตาม policy | แก้ต้นทุน, อัปเดตสต็อก |
| Inventory Staff | รับของ, นับสต็อก, Inventory Adjustment | แก้ราคาขาย, ต้นทุน |
| Accountant | บันทึกค่าใช้จ่าย, P&L | Operation หน้าร้าน |
| Website Admin | เผยแพร่สินค้า, จัดการออนไลน์ | แก้ต้นทุน, สต็อก |

---

## 💰 การคำนวณกำไร (Profit Calculation)

| รายการ | สูตร | ตัวอย่าง |
|--------|-----|---------|
| ยอดขาย | ราคาขาย × จำนวน | 950 × 1 = 950 |
| ต้นทุนสินค้าที่ขาย (COGS) | Cost × จำนวน | 650 × 1 = 650 |
| กำไรขั้นต้น | ยอดขาย - COGS | 950 - 650 = 300 |
| Gross Margin % | กำไร / ยอดขาย × 100 | 31.58% |
| กำไรสุทธิ | กำไรขั้นต้น - ค่าใช้จ่าย | หักเช่า, เงินเดือน, ค่าไฟ |

---

## 📊 Reports ที่ต้องดูได้

| รายงาน | ตอบคำถาม |
|--------|---------|
| Sales by Product | สินค้าไหนขายดี |
| Sales by Category | หมวดไหนทำยอดสูง |
| Gross Profit by Product | สินค้าไหนกำไรดี/ต่ำ |
| POS Daily Sales | ยอดขายรายวัน |
| Inventory Valuation | มูลค่าสต็อกคงเหลือ |
| Low Stock / Reordering | สินค้าไหนต้องสั่งเพิ่ม |
| Expense Report | ค่าใช้จ่ายร้าน |
| Profit & Loss | กำไร/ขาดทุนร้าน |

---

## ✅ Go-Live Checklist

| หมวด | Checkpoint | สถานะ |
|------|-----------|-------|
| Product | ทุก SKU มี Barcode, Cost, Price, Category | 🔲 |
| Inventory | Opening Stock ถูกต้องตามนับจริง | 🔲 |
| Location | ชั้นวางตรงกับหน้าร้าน | 🔲 |
| Purchase | Supplier และราคาซื้อถูกต้อง | 🔲 |
| POS | ยิง Barcode ได้ ตัดสต็อกถูก | 🔲 |
| Payment | เงินสด, โอน, QR, บัตร ครบ | 🔲 |
| User | Cashier แก้ต้นทุนไม่ได้ | 🔲 |
| Reports | ดูยอดขาย, กำไร, สต็อกได้ | 🔲 |
| Accounting | บันทึกค่าใช้จ่าย P&L | 🔲 |
| Website | ทำหลังสุด | ⏳ |

---

## 🚀 แผนทำงานจริงในระบบ Odoo (Custom Module)

> ขั้นตอนต่อไปนี้เป็นสิ่งที่จะทำทีละ Phase

### Phase 1 — เตรียม Product Master ✨ **เริ่มที่นี่**
- ตรวจสอบ `spare.part` model ว่ามี field ครบตามที่กำหนด
- เพิ่ม field ที่ยังขาด เช่น `brand`, `car_model`, `location_id`, `min_qty`, `max_qty`
- ตรวจสอบ Product Category (`spare.category`) 

### Phase 2 — Supplier & Purchase
- ตรวจสอบ/เพิ่ม Supplier model
- เชื่อม Vendor Price กับ Product

### Phase 3 — Inventory & Stock Location  
- ตรวจสอบ Location model
- เพิ่ม Opening Stock wizard

### Phase 4 — POS Integration
- ตรวจสอบ Barcode scanning ใน POS
- Payment method ครบ

### Phase 5 — User & Roles
- ตรวจสอบ Access Rights ตาม Role

### Phase 6 — Website (ทำภายหลัง)
- เปิดหลังจาก POS นิ่งแล้ว
