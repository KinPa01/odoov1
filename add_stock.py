env = env
Product = env['product.product']
Quant = env['stock.quant']

# Get all products
products = Product.search([('is_storable', '=', True)])
if not products:
    products = Product.search([('type', '=', 'product')])
if not products:
    products = Product.search([])

if products:
    location = env.ref('stock.stock_location_stock')
    for product in products:
        quant = Quant.search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id)
        ], limit=1)
        
        if not quant:
            quant = Quant.create({
                'product_id': product.id,
                'location_id': location.id,
                'inventory_quantity': 100.0,
            })
        else:
            quant.inventory_quantity = 100.0
            
        quant.action_apply_inventory()
        print(f"Added 100 units of {product.name} to {location.name}")
    
    env.cr.commit()
    print("Successfully added 100 stock to all products!")
else:
    print("No products found at all.")
