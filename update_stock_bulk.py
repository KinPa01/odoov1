location = env.ref('stock.stock_location_stock')
codes = [
    'TIRE-IRC-001', 'TIRE-MIC-001', 'CHN-DID-001', 
    'BRK-NMAX-001', 'BRK-PCX-001', 'BAT-YTZ5S-001',
    'FIL-WAV-001', 'FIL-XMA-001', 'SPK-NGK-001',
    'LED-OSR-001', 'BLT-PCX-001', 'BLT-AER-001'
]
for code in codes:
    product = env['product.product'].search([('default_code', '=', code)], limit=1)
    if product:
        product.is_storable = True
        quant = env['stock.quant'].search([('product_id', '=', product.id), ('location_id', '=', location.id)])
        if not quant:
            quant = env['stock.quant'].create({
                'product_id': product.id,
                'location_id': location.id,
            })
        quant.inventory_quantity = 50
        quant.action_apply_inventory()
        print('Updated bulk product:', code)
env.cr.commit()
print('Bulk stock update finished.')
