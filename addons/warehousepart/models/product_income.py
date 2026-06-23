# -*- coding: utf-8 -*-
"""
product_income.py
─────────────────────────────────────────────────────────────────────────────
รายได้สุทธิของสินค้า — คำนวณกำไร/ขาดทุนต่อสินค้าแต่ละรายการ
  - ดึงข้อมูลจาก product.template (ราคาขาย + ต้นทุน)
  - สรุปยอดขายจริงจาก account.move.line (ใบแจ้งหนี้ที่ยืนยัน)
─────────────────────────────────────────────────────────────────────────────
"""
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StoreProductIncome(models.Model):
    """
    รายงานรายได้สุทธิสินค้า (read-only computed model)
    แต่ละ record = สินค้า 1 รายการ
    คำนวณจากข้อมูล product.template + ยอดขายจริง
    """
    _name        = "store.product.income"
    _description = "รายได้สุทธิของสินค้าแต่ละรายการ"
    _inherit     = ["mail.thread"]
    _order       = "net_profit desc"
    _rec_name    = "product_name"
    _auto        = True      # สร้างตารางจริงเพื่อให้ filter/sort ได้

    # ─── ข้อมูลสินค้า ──────────────────────────────────────────────────────
    product_id    = fields.Many2one(
        "product.template", string="สินค้า",
        required=True, ondelete="cascade", index=True,
    )
    product_name  = fields.Char(string="ชื่อสินค้า", related="product_id.name", store=True)
    categ_id      = fields.Many2one(
        "product.category", string="หมวดหมู่",
        related="product_id.categ_id", store=True,
    )
    sale_price    = fields.Float(
        string="ราคาขาย (บาท)", related="product_id.list_price", store=True,
    )
    cost_price    = fields.Float(
        string="ต้นทุน (บาท)", related="product_id.standard_price", store=True,
    )
    period_month  = fields.Selection(
        [(str(i), m) for i, m in enumerate([
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
            "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
            "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
        ], 1)],
        string="เดือน",
        default=lambda self: str(fields.Date.today().month),
    )
    period_year   = fields.Integer(
        string="ปี",
        default=lambda self: fields.Date.today().year,
    )

    # ─── ยอดขาย (บันทึกด้วย manual หรือ wizard sync) ────────────────────────
    # ─── ยอดขาย (บันทึกด้วย manual หรือ wizard sync) ────────────────────────
    pos_categ_ids = fields.Many2many(
        "pos.category", string="หมวดหมู่ POS",
        related="product_id.pos_categ_ids", readonly=True,
    )
    qty_sold      = fields.Float(string="จำนวนที่ขาย (ชิ้น)", digits=(16, 2), default=0.0)
    total_revenue = fields.Float(string="รายรับรวม (บาท)", digits=(16, 2), default=0.0)
    total_cost    = fields.Float(string="ต้นทุนรวม (บาท)", compute="_compute_profit", store=True)
    gross_profit  = fields.Float(string="กำไรขั้นต้น (บาท)", compute="_compute_profit", store=True)
    net_profit    = fields.Float(string="รายได้สุทธิ (บาท)", compute="_compute_profit", store=True)
    margin_pct    = fields.Float(string="% กำไร", compute="_compute_profit", store=True, digits=(5, 2))

    qty_available = fields.Float(
        string="คงเหลือคงคลัง", compute="_compute_stock_fields",
        search="_search_qty_available", store=False
    )
    incoming_qty = fields.Float(
        string="กำลังจัดส่งเข้า", compute="_compute_stock_fields",
        search="_search_incoming_qty", store=False
    )
    stock_status = fields.Selection([
        ('critical', '🚨 วิกฤต/ใกล้หมด'),
        ('reorder', '⚠️ ควรสั่งซื้อเพิ่ม'),
        ('sufficient', '✅ พอดี/ปลอดภัย'),
        ('overstock', '📦 สต๊อกบวม'),
    ], string="คำแนะนำเติมสต๊อก", compute="_compute_stock_fields",
       search="_search_stock_status", store=False)

    note          = fields.Text(string="หมายเหตุ")
    company_id    = fields.Many2one("res.company", default=lambda self: self.env.company)

    # ─── Computed ────────────────────────────────────────────────────────────
    @api.depends("product_id", "qty_sold")
    def _compute_stock_fields(self):
        for rec in self:
            if not rec.product_id:
                rec.qty_available = 0.0
                rec.incoming_qty = 0.0
                rec.stock_status = 'sufficient'
                continue
            tmpl = rec.product_id
            rec.qty_available = tmpl.qty_available
            rec.incoming_qty = tmpl.incoming_qty
            
            if rec.qty_available <= 2:
                rec.stock_status = 'critical'
            elif rec.qty_available < rec.qty_sold * 0.5:
                rec.stock_status = 'critical'
            elif rec.qty_available < rec.qty_sold * 1.2:
                rec.stock_status = 'reorder'
            elif rec.qty_available > rec.qty_sold * 3.0 and rec.qty_available > 50:
                rec.stock_status = 'overstock'
            else:
                rec.stock_status = 'sufficient'

    def _search_qty_available(self, operator, value):
        templates = self.env['product.template'].search([('qty_available', operator, value)])
        return [('product_id', 'in', templates.ids)]

    def _search_incoming_qty(self, operator, value):
        templates = self.env['product.template'].search([('incoming_qty', operator, value)])
        return [('product_id', 'in', templates.ids)]

    def _search_stock_status(self, operator, value):
        if operator != '=':
            return []
        
        # ค้นหาแบบ dynamic ใน memory เพื่อเลี่ยงการใช้ SQL query กับ non-stored computed field
        all_records = self.search([])
        matched_ids = []
        for rec in all_records:
            qty_avail = rec.product_id.qty_available
            qty_sold = rec.qty_sold
            status = 'sufficient'
            
            if qty_avail <= 2:
                status = 'critical'
            elif qty_avail < qty_sold * 0.5:
                status = 'critical'
            elif qty_avail < qty_sold * 1.2:
                status = 'reorder'
            elif qty_avail > qty_sold * 3.0 and qty_avail > 50:
                status = 'overstock'
            
            if status == value:
                matched_ids.append(rec.id)
                
        return [('id', 'in', matched_ids)]

    @api.depends("qty_sold", "cost_price", "total_revenue")
    def _compute_profit(self):
        for rec in self:
            rec.total_cost   = rec.qty_sold * rec.cost_price
            rec.gross_profit = rec.total_revenue - rec.total_cost
            rec.net_profit   = rec.gross_profit
            if rec.total_revenue:
                rec.margin_pct = (rec.gross_profit / rec.total_revenue) * 100
            else:
                rec.margin_pct = 0.0

    # ─── Wizard: sync จาก POS / Invoice ──────────────────────────────────────
    def action_sync_from_pos(self):
        """ดึงข้อมูลยอดขายจาก POS orders ของเดือนที่เลือก"""
        self.ensure_one()
        from datetime import date
        from calendar import monthrange
        month = int(self.period_month)
        year  = int(self.period_year)
        d_from = date(year, month, 1)
        d_to   = date(year, month, monthrange(year, month)[1])

        # ค้นหาจาก pos.order.line
        PosLine = self.env["pos.order.line"]
        lines = PosLine.search([
            ("product_id.product_tmpl_id", "=", self.product_id.id),
            ("order_id.date_order", ">=", d_from),
            ("order_id.date_order", "<=", d_to),
            ("order_id.state", "in", ["done", "invoiced"]),
        ])
        if lines:
            self.qty_sold      = sum(l.qty for l in lines)
            self.total_revenue = sum(l.price_subtotal_incl for l in lines)
        return True


class StoreProductIncomeSyncWizard(models.TransientModel):
    """Wizard สร้าง/อัปเดตรายงานรายได้สุทธิสินค้าจาก POS"""
    _name        = "store.product.income.wizard"
    _description = "Wizard Sync รายได้สุทธิสินค้าจาก POS"

    period_month = fields.Selection(
        [(str(i), m) for i, m in enumerate([
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
            "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
            "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
        ], 1)],
        string="เดือน",
        required=True,
        default=lambda self: str(fields.Date.today().month),
    )
    period_year = fields.Integer(
        string="ปี", required=True,
        default=lambda self: fields.Date.today().year,
    )
    overwrite = fields.Boolean(string="เขียนทับข้อมูลเดิม", default=True)

    def action_sync(self):
        """ดึงยอดขายจาก POS แล้วสร้าง/อัปเดต store.product.income"""
        self.ensure_one()
        from datetime import date
        from calendar import monthrange
        month  = int(self.period_month)
        year   = int(self.period_year)
        d_from = date(year, month, 1)
        d_to   = date(year, month, monthrange(year, month)[1])

        PosLine = self.env["pos.order.line"]
        Income  = self.env["store.product.income"]

        # รวมยอดตาม product_tmpl_id
        lines = PosLine.search([
            ("order_id.date_order", ">=", d_from),
            ("order_id.date_order", "<=", d_to),
            ("order_id.state", "in", ["done", "invoiced"]),
        ])

        summary = {}  # {product_tmpl_id: {qty, revenue}}
        for l in lines:
            tmpl_id = l.product_id.product_tmpl_id.id
            if tmpl_id not in summary:
                summary[tmpl_id] = {"qty": 0.0, "revenue": 0.0}
            summary[tmpl_id]["qty"]     += l.qty
            summary[tmpl_id]["revenue"] += l.price_subtotal_incl

        created = updated = 0
        for tmpl_id, data in summary.items():
            existing = Income.search([
                ("product_id", "=", tmpl_id),
                ("period_month", "=", self.period_month),
                ("period_year", "=", self.period_year),
            ], limit=1)
            vals = {
                "qty_sold": data["qty"],
                "total_revenue": data["revenue"],
            }
            if existing:
                if self.overwrite:
                    existing.write(vals)
                    updated += 1
            else:
                Income.create({
                    "product_id": tmpl_id,
                    "period_month": self.period_month,
                    "period_year": self.period_year,
                    **vals,
                })
                created += 1

        return {
            "type": "ir.actions.act_window",
            "name": f"รายได้สุทธิสินค้า — {self.period_month}/{self.period_year}",
            "res_model": "store.product.income",
            "view_mode": "list,form",
            "domain": [
                ("period_month", "=", self.period_month),
                ("period_year", "=", self.period_year),
            ],
            "target": "current",
        }
