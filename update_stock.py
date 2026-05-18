location = env.ref('stock.stock_location_stock')
codes = ['OIL-10W40-001', 'BRK-VIOS-001', 'FIL-HONDA-001', 'BAT-NS60-001', 'SUS-VIGO-001']
for code in codes:
    product = env['product.product'].search([('default_code', '=', code)], limit=1)
    if product:
        # FORCE storable
        product.is_storable = True
        
        quant = env['stock.quant'].search([('product_id', '=', product.id), ('location_id', '=', location.id)])
        if not quant:
            quant = env['stock.quant'].create({
                'product_id': product.id,
                'location_id': location.id,
            })
        quant.inventory_quantity = 50
        quant.action_apply_inventory()
        print('Updated', code)
env.cr.commit()
