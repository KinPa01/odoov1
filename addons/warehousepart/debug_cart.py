orders = env['sale.order'].search([('state', 'in', ['draft']), ('partner_id', '=', 3)])
print(f"Draft orders for Administrator: {len(orders)}")
for o in orders:
    print(f"Order: {o.name}")
    print(f"  amount_total: {o.amount_total}")
    for line in o.order_line:
        print(f"  - {line.product_id.name}: {line.product_uom_qty} @ {line.price_unit}")
    
    methods = o._get_delivery_methods()
    print(f"  delivery methods: {methods.mapped('name')}")
