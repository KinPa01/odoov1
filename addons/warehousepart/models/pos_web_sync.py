# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.order_id.website_id and line.product_id.type == 'product':
                if line.product_id.free_qty < line.product_uom_qty:
                    raise ValidationError(_("ขออภัยครับ สินค้า %s มีไม่เพียงพอในสต๊อก (มีคนสั่งซื้อไปก่อนหน้านี้)") % line.product_id.name)
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'product_uom_qty' in vals:
            for line in self:
                if line.order_id.website_id and line.product_id.type == 'product':
                    if line.product_id.free_qty < line.product_uom_qty:
                        raise ValidationError(_("ขออภัยครับ สินค้า %s มีไม่เพียงพอในสต๊อก (มีคนสั่งซื้อไปก่อนหน้านี้)") % line.product_id.name)
        return res
