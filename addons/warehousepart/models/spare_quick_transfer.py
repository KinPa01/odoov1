# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SpareQuickTransfer(models.TransientModel):
    _name = 'spare.quick.transfer'
    _description = 'Wizard สำหรับโอนย้ายอะไหล่ด่วน'

    def _default_location_src(self):
        # พยายามหา Internal Location ตัวแรกเป็นค่าเริ่มต้น
        return self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)

    location_src_id = fields.Many2one(
        'stock.location',
        string='คลังต้นทาง',
        required=True,
        domain=[('usage', '=', 'internal')],
        default=_default_location_src
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='คลังปลายทาง',
        required=True,
        domain=[('usage', '=', 'internal')]
    )
    line_ids = fields.One2many(
        'spare.quick.transfer.line',
        'transfer_id',
        string='รายการสินค้า'
    )

    def action_transfer(self):
        self.ensure_one()
        
        if self.location_src_id == self.location_dest_id:
            raise UserError(_("คลังต้นทางและปลายทางต้องไม่เป็นคลังเดียวกัน!"))
            
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มรายการสินค้าที่ต้องการโอนย้าย"))

        # 1. หา Picking Type สำหรับการโอนย้ายภายใน
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not picking_type:
            raise UserError(_("ไม่พบประเภทการทำรายการแบบ 'การโอนย้ายภายใน' (Internal Transfer) ในระบบ"))

        # 2. สร้างใบเบิก/โอนย้าย (stock.picking)
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': 'โอนย้ายด่วน (Quick Transfer)',
            'company_id': self.env.company.id,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # 3. สร้างรายการสินค้า (stock.move)
        for line in self.line_ids:
            if line.qty <= 0:
                raise UserError(_("จำนวนสินค้า %s ต้องมากกว่า 0") % line.product_id.display_name)
                
            # ตรวจสอบว่าสต็อกมีพอหรือไม่ (เตือนเบาๆ หรือ ปล่อยให้ Odoo ตรวจ)
            # เราให้ Odoo ตรวจสอบผ่าน Reservation ดีกว่า
            
            move_vals = {
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'product_uom_qty': line.qty,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
            }
            self.env['stock.move'].create(move_vals)

        # 4. ยืนยันใบโอนย้าย และตรวจสอบสต็อก (Mark as To Do / Ready)
        picking.action_confirm()
        picking.action_assign()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('สร้างใบโอนย้ายสำเร็จ!'),
                'message': _('สร้างใบโอนย้าย %s แล้ว กรุณาตรวจสอบและยืนยันในเมนูโอนย้ายภายใน') % picking.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class SpareQuickTransferLine(models.TransientModel):
    _name = 'spare.quick.transfer.line'
    _description = 'รายการสินค้าที่ต้องการโอนย้าย'

    transfer_id = fields.Many2one('spare.quick.transfer', required=True)
    product_id = fields.Many2one(
        'product.product',
        string='สินค้า (อะไหล่)',
        required=True,
        domain=[('is_storable', '=', True)]
    )
    qty = fields.Float(string='จำนวนที่ย้าย', required=True, default=1.0)
    available_qty = fields.Float(
        string='มีในคลังต้นทาง',
        compute='_compute_available_qty'
    )

    @api.depends('product_id', 'transfer_id.location_src_id')
    def _compute_available_qty(self):
        for line in self:
            if line.product_id and line.transfer_id.location_src_id:
                # หาจำนวนในคลังต้นทางเฉพาะจุด
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.transfer_id.location_src_id.id)
                ])
                line.available_qty = sum(quants.mapped('quantity'))
            else:
                line.available_qty = 0.0
