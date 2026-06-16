# สรุปการจัดตั้ง Role & User Accounts — ร้านอาหลั่ย

## ไฟล์ที่เปลี่ยนแปลง

| ไฟล์ | สิ่งที่เปลี่ยน |
|------|---------------|
| [spare_security.xml](file:///c:/Users/autod/Desktop/inten/warehousepart/odoo/addons/warehousepart/security/spare_security.xml) | เพิ่ม `implied_ids` ของ Odoo built-in groups ให้แต่ละ role |
| [employee_data.xml](file:///c:/Users/autod/Desktop/inten/warehousepart/odoo/addons/warehousepart/data/employee_data.xml) | สร้าง `res.users` ทั้ง 9 คน + ผูก `user_id` กับ `hr.employee` |
| [menu_views.xml](file:///c:/Users/autod/Desktop/inten/warehousepart/odoo/addons/warehousepart/views/menu_views.xml) | ล็อค `groups=` บนทุกเมนู + เพิ่มเมนู "ข้อมูลพนักงานและเงินเดือน" |

---

## สรุป Role และสิทธิ์

### 👑 เจ้าของร้าน — `group_spare_owner`
- ดูและจัดการ **ทุกอย่าง** ในระบบ
- implied groups: `account.group_account_manager`, `stock.group_stock_manager`, `point_of_sale.group_pos_manager`, `purchase.group_purchase_manager`, `base.group_erp_manager`

### 💰 พนักงานบัญชี — `group_spare_accountant`
- เข้าถึง: **รายรับ-รายจ่าย**, **บัญชีทั้งหมด**, **ข้อมูลพนักงานและเงินเดือน**, **เวลาทำงาน**
- implied groups: `account.group_account_user`
- ❌ ไม่เห็น: คลัง, POS, จัดซื้อ

### 🏭 พนักงานคลัง — `group_spare_inventory`
- เข้าถึง: **คลังสินค้าและการจัดส่ง**, **โอนย้ายอะไหล่ด่วน**, **ชั้นวางสินค้า**, **แคตตาล็อก**, **เวลาทำงาน**
- implied groups: `stock.group_stock_user`
- ❌ ไม่เห็น: POS, บัญชี, จัดซื้อ

### 🏪 พนักงานขายหน้าร้าน — `group_spare_cashier`
- เข้าถึง: **ระบบขาย POS** เท่านั้น + **เวลาทำงาน**
- implied groups: `point_of_sale.group_pos_user`
- ❌ ไม่เห็น: คลัง, บัญชี, จัดซื้อ, แคตตาล็อก

---

## รายชื่อพนักงานและ Login

| ชื่อ | ตำแหน่ง | Login | Role |
|------|---------|-------|------|
| คุณรัน เจ้าของร้าน | เจ้าของ | `owner@ran-ahlai.com` | 👑 เจ้าของ |
| คุณนิดา บัญชีดี | บัญชี | `account@ran-ahlai.com` | 💰 บัญชี |
| คุณสมชาย คลังดี | คลัง 1 | `inv01@ran-ahlai.com` | 🏭 คลัง |
| คุณวิชัย จัดสต็อก | คลัง 2 | `inv02@ran-ahlai.com` | 🏭 คลัง |
| คุณสุดา รับของ | คลัง 3 | `inv03@ran-ahlai.com` | 🏭 คลัง |
| คุณประสิทธิ์ โกดังใหญ่ | คลัง 4 | `inv04@ran-ahlai.com` | 🏭 คลัง |
| คุณมานะ ขนส่งดี | คลัง 5 | `inv05@ran-ahlai.com` | 🏭 คลัง |
| คุณปลา หน้าร้าน | หน้าร้าน 1 | `front01@ran-ahlai.com` | 🏪 หน้าร้าน |
| คุณก้อง หน้าร้าน | หน้าร้าน 2 | `front02@ran-ahlai.com` | 🏪 หน้าร้าน |

> [!IMPORTANT]
> รหัสผ่าน default ทุกคน: **`Changeme@1`** — ควรให้พนักงานเปลี่ยนหลัง login ครั้งแรก

---

## วิธี Update โมดูล

```bash
# รัน odoo-bin เพื่อ update module
python odoo-bin -u warehousepart -d <ชื่อฐานข้อมูล>
```

> [!NOTE]
> เนื่องจาก `res.users` ถูกสร้างด้วย `noupdate="1"` รหัสผ่านจะ**ไม่ถูกรีเซ็ต**เมื่อ update module ซ้ำ

## ตารางสิทธิ์เมนู

| เมนู | 👑 เจ้าของ | 💰 บัญชี | 🏭 คลัง | 🏪 หน้าร้าน |
|------|:---:|:---:|:---:|:---:|
| ฐานข้อมูลอะไหล่ | ✅ | ✅ | ✅ | ❌ |
| ชั้นวางสินค้า | ✅ | ❌ | ✅ | ✅ |
| คลังและการจัดส่ง | ✅ | ❌ | ✅ | ❌ |
| โอนย้ายอะไหล่ด่วน | ✅ | ❌ | ✅ | ❌ |
| ดูสต็อก (read-only) | ❌ | ❌ | ❌ | ✅ |
| ระบบขาย POS | ✅ | ❌ | ❌ | ✅ |
| บัญชีและการเงิน | ✅ | ✅ | ❌ | ❌ |
| ข้อมูลพนักงาน/เงินเดือน | ✅ | ✅ | ❌ | ❌ |
| สั่งซื้อ (Purchase) | ✅ | ❌ | ❌ | ❌ |
| ข้อมูลผู้ติดต่อ | ✅ | ❌ | ❌ | ❌ |
| เวลาทำงาน | ✅ | ✅ | ✅ | ✅ |
| จัดการเว็บไซต์ | ✅ | ❌ | ❌ | ❌ |
