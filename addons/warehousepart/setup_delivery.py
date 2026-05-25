"""
setup_delivery.py — ตั้งค่า Delivery Methods สำหรับเว็บไซต์
"""
company = env['res.company'].search([], limit=1)

# หา/สร้าง product สำหรับค่าจัดส่ง
def get_or_create_delivery_product(name, price):
    prod = env['product.product'].search([
        ('name', '=', name), ('type', '=', 'service')
    ], limit=1)
    if not prod:
        tmpl = env['product.template'].create({
            'name': name,
            'type': 'service',
            'list_price': price,
            'sale_ok': True,
            'purchase_ok': False,
        })
        prod = tmpl.product_variant_ids[0]
        print(f"   สร้าง product: {name}")
    return prod

# ─── 1. แก้ "Standard delivery" ────────────────────────────────
prod_std = get_or_create_delivery_product('ค่าจัดส่งทั่วประเทศ', 50)
std = env['delivery.carrier'].browse(1)
std.write({
    'name': 'จัดส่งทั่วประเทศ',
    'delivery_type': 'fixed',
    'fixed_price': 50.0,
    'product_id': prod_std.id,
    'active': True,
    'website_published': True,
})
print(f"✅ {std.name}: ราคา 50฿ | published={std.website_published}")

# ─── 2. แก้/สร้าง "รับสินค้าเอง" ──────────────────────────────
pickup = env['delivery.carrier'].search([('name', 'ilike', 'รับ')], limit=1)
prod_pickup = get_or_create_delivery_product('รับสินค้าเองที่ร้าน', 0)
if not pickup:
    pickup = env['delivery.carrier'].create({
        'name': 'รับสินค้าเองที่ร้าน (ฟรี)',
        'delivery_type': 'fixed',
        'fixed_price': 0.0,
        'product_id': prod_pickup.id,
        'active': True,
        'website_published': True,
        'company_id': company.id,
    })
    print(f"✅ สร้าง: {pickup.name}: ฟรี")
else:
    pickup.write({
        'active': True,
        'website_published': True,
        'fixed_price': 0.0,
        'product_id': prod_pickup.id,
    })
    print(f"✅ อัปเดต: {pickup.name}: ฟรี")

# ─── 3. เปิด Kerry Express ─────────────────────────────────────
kerry = env['delivery.carrier'].browse(2)
if kerry.exists():
    kerry.write({'website_published': True})
    print(f"✅ เปิด: {kerry.name}")

env.cr.commit()

print("\n📋 Delivery Carriers ทั้งหมด:")
for c in env['delivery.carrier'].search([]):
    print(f"  [{c.id}] {c.name:40} | {getattr(c,'fixed_price',0):5.0f}฿ | pub={c.website_published} | active={c.active}")

print("\n✅ Done! reload หน้า checkout แล้วจะเห็นตัวเลือกจัดส่งครับ")
