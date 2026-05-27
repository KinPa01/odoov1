from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_received = fields.Boolean(
        string="Customer Received", 
        default=False, 
        help="Indicates if the customer has manually confirmed receipt of the order."
    )
