from odoo.addons.website_sale.controllers.delivery import Delivery

order = env['sale.order'].search([('state','in',['draft','sale'])], limit=1, order='id desc')
if order:
    print(f"Test order: {order.name}")
    print("Simulating _get_delivery_methods_express_checkout:")
    res = Delivery._get_delivery_methods_express_checkout(order)
    print(res)
    for k, v in res.items():
        print(f"  {k.name}: {v}")
