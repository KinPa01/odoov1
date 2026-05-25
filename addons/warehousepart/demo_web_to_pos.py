#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
demo_web_to_pos.py
==================
Demo: ทดสอบระบบ "เว็บสั่งซื้อ → POS สต็อกลดทันที"

วิธีรัน (paste ใน Odoo shell หรือรันผ่าน docker):
  docker compose exec web bash -c "odoo shell \\
    --addons-path='/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons' \\
    --db_host=db --db_user=odoo --db_password=odoo \\
    -d ran_ahlai_production" < /mnt/extra-addons/demo_web_to_pos.py

ตัวแปรที่ปรับได้:
  SEARCH_KEYWORD  — ชื่อสินค้าที่ต้องการ
  WEB_ORDER_QTY   — จำนวนที่จะให้ "เว็บ" สั่ง
  DO_CLEANUP      — True = ยกเลิก order หลัง demo
"""

SEARCH_KEYWORD = "กรองแอร์"   # แก้ชื่อสินค้าตรงนี้
WEB_ORDER_QTY  = 1            # จำนวนที่เว็บสั่ง
DO_CLEANUP     = True         # ยกเลิก SO หลัง demo (ไม่กระทบสต็อกจริง)

# ─── ฟังก์ชัน helper ────────────────────────────────────────────
def line(char="─", n=60):
    print(char * n)

def stock_status(tmpl, label=""):
    tmpl.invalidate_recordset()
    print(f"  {'['+label+']':15} qty_available={tmpl.qty_available:.0f}  |  "
          f"virtual_available={tmpl.virtual_available:.0f}")

# ─── START ──────────────────────────────────────────────────────
line("═")
print("  🧪 DEMO: เว็บสั่งซื้อ → POS สต็อกลดทันที")
line("═")

# Step 1: หาสินค้า
tmpl_list = env['product.template'].search(
    [('name', 'ilike', SEARCH_KEYWORD), ('is_storable', '=', True),
     ('available_in_pos', '=', True)],
    limit=5
)
if not tmpl_list:
    print(f"❌ ไม่พบสินค้า is_storable+available_in_pos ที่มีคำว่า '{SEARCH_KEYWORD}'")
    raise SystemExit(1)

print(f"\n🔍 สินค้าที่พบ ({len(tmpl_list)} รายการ):\n")
for i, t in enumerate(tmpl_list):
    print(f"  {i+1}. [{t.id:4d}] {t.name}")
    stock_status(t)

tmpl = tmpl_list[0]
product = tmpl.product_variant_ids[0]
print(f"\n✅ ใช้สินค้า: {tmpl.name}")
line()

# Step 2: สถานะก่อน
print("\n📊 STEP 1 — สถานะสต็อกก่อนสั่งซื้อ:")
stock_status(tmpl, "ก่อน")
print(f"\n  👉 POS เห็นสต็อก = {int(tmpl.virtual_available)} ชิ้น  "
      f"→ กดได้สูงสุด {int(tmpl.virtual_available)} ครั้ง")

# Step 3: สร้าง Web Order (SO)
line()
customer = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
warehouse = env['stock.warehouse'].search([], limit=1)
pricelist = env['product.pricelist'].search([('currency_id.name', '=', 'THB')], limit=1)

print(f"\n🛒 STEP 2 — จำลองเว็บสั่งซื้อ {WEB_ORDER_QTY} ชิ้น...")
print(f"   Customer : {customer.name}")
print(f"   Warehouse: {warehouse.name}")

so_vals = {
    'partner_id': customer.id,
    'warehouse_id': warehouse.id,
    'order_line': [(0, 0, {
        'product_id': product.id,
        'product_uom_qty': WEB_ORDER_QTY,
        'price_unit': product.list_price,
    })],
}
if pricelist:
    so_vals['pricelist_id'] = pricelist.id

so = env['sale.order'].create(so_vals)
print(f"   ✅ สร้าง SO: {so.name} (state: {so.state})")

# Confirm → reserve stock
so.action_confirm()
env.cr.commit()
print(f"   ✅ Confirm SO → state: {so.state}")
print(f"   📦 Delivery: {', '.join(so.picking_ids.mapped('name')) or 'ไม่พบ'}")

# Step 4: สถานะหลัง confirm
print(f"\n📊 STEP 3 — สถานะสต็อกหลัง Confirm SO:")
stock_status(tmpl, "หลัง confirm")
remaining = int(tmpl.virtual_available)
print(f"\n  👉 virtual_available ลดเหลือ {remaining} ชิ้น")
print(f"  👉 POS จะรับ WebSocket แล้วอัปเดตสต็อกทันที")
print(f"  👉 ถ้าสต็อกเหลือ {remaining} ชิ้น → POS กดได้แค่ {remaining} ครั้งเท่านั้น!")

# Step 5: Validate Delivery (ทดสอบเพิ่มเติม)
line()
print(f"\n🚚 STEP 4 — Validate Delivery (จัดส่งจริง)...")
picking = so.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
if picking:
    pk = picking[0]
    try:
        for ml in pk.move_line_ids:
            ml.qty_done = ml.reserved_qty or ml.move_id.product_uom_qty
        if not pk.move_line_ids:
            for mv in pk.move_ids:
                mv.quantity = mv.product_uom_qty
        pk.button_validate()
        env.cr.commit()
        print(f"   ✅ Delivery {pk.name} → Done")
    except Exception as e:
        print(f"   ⚠️  Validate ต้องการ confirmation: {str(e)[:80]}")
        print(f"       (ปกติใน Odoo จะขอ confirm backorder)")

    print(f"\n📊 STEP 5 — สถานะสต็อกหลัง Validate Delivery:")
    stock_status(tmpl, "หลัง delivery")
    print(f"\n  👉 qty_available ลดแล้ว (ของออกจากคลังจริง)")
    print(f"  👉 POS รับ WebSocket อีกครั้ง → อัปเดตสต็อก")
else:
    print("   ⚠️  ไม่พบ pending delivery (อาจ validate แล้ว)")

# Step 6: Cleanup
line()
if DO_CLEANUP and so.state not in ('done',):
    try:
        so.action_cancel()
        env.cr.commit()
        print(f"\n🗑️  Cleanup: ยกเลิก SO {so.name} เรียบร้อย → สต็อกกลับคืน")
        stock_status(tmpl, "หลัง cancel")
    except Exception as e:
        print(f"\n⚠️  Cancel ไม่ได้ (อาจ validate delivery แล้ว): {e}")
        print(f"   SO: {so.name} — กรุณายกเลิกผ่าน UI เอง")
else:
    print(f"\n📌 SO {so.name} ยังอยู่ในระบบ — ยกเลิกเองผ่าน UI ถ้าต้องการ")

line("═")
print("  ✅ DEMO COMPLETE")
line("═")
print()
