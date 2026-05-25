product = env['product.template'].search([('name','ilike','กรองอากาศ Honda Wave')], limit=1)
partner = env['res.partner'].search([('customer_rank','>',0)], limit=1, order='customer_rank desc')
wh = env['stock.warehouse'].search([], limit=1)

print(f'\nสินค้า: {product.name}')
print(f'Partner: {partner.name}')
print(f'\n[ก่อน] qty_available={product.qty_available} | virtual_available={product.virtual_available}')

so = env['sale.order'].create({
    'partner_id': partner.id,
    'warehouse_id': wh.id,
    'order_line': [(0,0,{
        'product_id': product.product_variant_ids[0].id,
        'product_uom_qty': 1,
        'price_unit': product.list_price
    })]
})
print(f'SO created: {so.name}')
so.action_confirm()
env.cr.commit()
print(f'SO confirmed: {so.state}')
product.invalidate_recordset()
print(f'[หลัง confirm] qty_available={product.qty_available} | virtual_available={product.virtual_available}')
so.action_cancel()
env.cr.commit()
product.invalidate_recordset()
print(f'[หลัง cancel]  qty_available={product.qty_available} | virtual_available={product.virtual_available}')
print('\nDEMO COMPLETE')
