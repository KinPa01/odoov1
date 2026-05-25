order = env['sale.order'].search([('state','in',['draft','sale'])], limit=1, order='id desc')
if order:
    print(f"Test order: {order.name}")
    print(f"Available methods via _get_delivery_methods():")
    for dm in order._get_delivery_methods():
        print(f" - {dm.name}")

    print("\nSimulating /shop/delivery_methods controller (without request):")
    from odoo.addons.website_sale.controllers.delivery import Delivery
    d = Delivery()
    try:
        # We can't easily test shop_delivery_methods because it relies on `request.cart`
        pass
    except Exception as e:
        print(e)
    
    # Check if they are available for order
    carriers = env['delivery.carrier'].search([('website_published','=',True)])
    for c in carriers:
        is_avail = c.sudo()._is_available_for_order(order)
        print(f"{c.name}: _is_available_for_order = {is_avail}")
