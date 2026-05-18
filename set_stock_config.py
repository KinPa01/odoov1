# Run this script using your odoo shell or environment similar to fix_web.py
for product in env['product.template'].search([]):
    try:
        product.write({
            'allow_out_of_stock_order': False,
            'show_availability': True,
            'available_threshold': 5
        })
        print("Updated product:", product.name)
    except Exception as e:
        print("Could not update product:", product.name, e)

# อัปเดตการตั้งค่า POS (ถ้ามีให้ตั้งค่าป้องกันการขายของหมดสต๊อก)
for pos_config in env['pos.config'].search([]):
    try:
        # ในบางเวอร์ชันจะมีช่องนี้
        pos_config.write({
            'negative_order_group': False,
        })
        print("Updated POS config:", pos_config.name)
    except:
        pass

env.cr.commit()
print("อัปเดตการตั้งค่า E-Commerce และ POS เรียบร้อยแล้ว")
