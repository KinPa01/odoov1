order = env['sale.order'].search([('state','in',['draft','sale'])], limit=1, order='id desc')
if order:
    print(f"Test order: {order.name}")
    carriers = env['delivery.carrier'].search([('website_published','=',True)])
    from odoo.addons.website_sale.controllers.delivery import Delivery
    for c in carriers:
        print(f"--- {c.name} ---")
        try:
            rate = Delivery._get_rate(c, order, is_express_checkout_flow=True)
            print(f"  _get_rate: {rate}")
        except Exception as e:
            print(f"  _get_rate ERROR: {e}")
