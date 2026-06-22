# -*- coding: utf-8 -*-
"""
store_accounting.py
─────────────────────────────────────────────────────────────────────────────
ระบบบัญชีร้านอาหลั่ย
  1. StoreIncomeExpense  — บันทึกรายรับ-รายจ่ายร้าน
  2. EmployeeSalaryPayment — บันทึกการจ่ายเงินเดือนพนักงาน
─────────────────────────────────────────────────────────────────────────────
"""
import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. รายรับ-รายจ่ายร้าน
# ═══════════════════════════════════════════════════════════════════════════════
class StoreIncomeExpense(models.Model):
    _name        = "store.income.expense"
    _description = "บันทึกรายรับ-รายจ่ายร้าน"
    _inherit     = ["mail.thread"]
    _order       = "transaction_date desc, id desc"
    _rec_name    = "name"

    # ─── ประเภทธุรกรรม ──────────────────────────────────────────────────────
    TRANSACTION_TYPE = [
        ('income',  'รายรับ (Income)'),
        ('expense', 'รายจ่าย (Expense)'),
    ]

    # ─── หมวดหมู่รายรับ ──────────────────────────────────────────────────────
    INCOME_CATEGORY = [
        ('sales_pos',    '💵 ยอดขาย POS'),
        ('sales_online', '🌐 ยอดขายออนไลน์'),
        ('sales_direct', '🤝 ยอดขายตรง'),
        ('service',      '🔧 ค่าบริการซ่อม'),
        ('other_income', '📥 รายรับอื่นๆ'),
    ]

    # ─── หมวดหมู่รายจ่าย ─────────────────────────────────────────────────────
    EXPENSE_CATEGORY = [
        ('purchase_parts',  '🔩 ซื้ออะไหล่/สินค้า'),
        ('salary',          '👥 เงินเดือนพนักงาน'),
        ('rent',            '🏠 ค่าเช่าสถานที่'),
        ('utilities',       '💡 ค่าสาธารณูปโภค'),
        ('marketing',       '📢 ค่าโฆษณา/การตลาด'),
        ('transport',       '🚛 ค่าขนส่ง/จัดส่ง'),
        ('maintenance',     '🛠️ ค่าซ่อมบำรุง'),
        ('other_expense',   '📤 รายจ่ายอื่นๆ'),
    ]

    # ─── สถานะ ───────────────────────────────────────────────────────────────
    STATE = [
        ('draft',     'ร่าง'),
        ('confirmed', 'ยืนยัน'),
        ('cancelled', 'ยกเลิก'),
    ]

    name             = fields.Char(string="รายละเอียด", required=True)
    transaction_type = fields.Selection(
        TRANSACTION_TYPE, string="ประเภท", required=True, default='income',
    )
    income_category  = fields.Selection(
        INCOME_CATEGORY, string="หมวดหมู่รายรับ",
        invisible="transaction_type != 'income'",
    )
    expense_category = fields.Selection(
        EXPENSE_CATEGORY, string="หมวดหมู่รายจ่าย",
        invisible="transaction_type != 'expense'",
    )
    transaction_date = fields.Date(
        string="วันที่", required=True, default=fields.Date.today, index=True,
    )
    amount           = fields.Monetary(
        string="จำนวนเงิน (บาท)", required=True, currency_field="currency_id",
    )
    currency_id      = fields.Many2one(
        "res.currency", string="สกุลเงิน",
        default=lambda self: self.env.company.currency_id,
    )
    reference        = fields.Char(string="เลขอ้างอิง/ใบเสร็จ")
    partner_id       = fields.Many2one(
        "res.partner", string="คู่ค้า/ลูกค้า/ซัพพลายเออร์",
    )
    account_move_id  = fields.Many2one(
        "account.move", string="บัญชีที่เชื่อมโยง",
        readonly=True, help="รายการบัญชีที่สร้างอัตโนมัติจาก Odoo Accounting",
    )
    note             = fields.Text(string="หมายเหตุ")
    state            = fields.Selection(
        STATE, string="สถานะ", default='draft', required=True, index=True,
    )
    company_id       = fields.Many2one(
        "res.company", string="บริษัท",
        default=lambda self: self.env.company,
    )
    created_by       = fields.Many2one(
        "res.users", string="บันทึกโดย",
        default=lambda self: self.env.user, readonly=True,
    )

    # ─── Computed ────────────────────────────────────────────────────────────
    category_display = fields.Char(
        string="หมวดหมู่", compute="_compute_category_display", store=True,
    )

    @api.depends("transaction_type", "income_category", "expense_category")
    def _compute_category_display(self):
        inc_map = dict(self.INCOME_CATEGORY)
        exp_map = dict(self.EXPENSE_CATEGORY)
        for rec in self:
            if rec.transaction_type == "income":
                rec.category_display = inc_map.get(rec.income_category, "ไม่ระบุ")
            else:
                rec.category_display = exp_map.get(rec.expense_category, "ไม่ระบุ")

    # ─── Constraints ─────────────────────────────────────────────────────────
    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError("จำนวนเงินต้องมากกว่า 0 บาท")

    # ─── Actions ─────────────────────────────────────────────────────────────
    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("รายการนี้ไม่อยู่ในสถานะร่าง")
            rec.state = "confirmed"

    def action_cancel(self):
        for rec in self:
            if rec.state == "cancelled":
                raise UserError("รายการนี้ถูกยกเลิกแล้ว")
            rec.state = "cancelled"

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = "draft"

    @api.model
    def _get_monthly_summary(self, year=None, month=None):
        """คืน dict สรุปรายรับ-รายจ่ายของเดือนที่ระบุ"""
        today = date.today()
        year  = year  or today.year
        month = month or today.month
        domain = [
            ("transaction_date", ">=", date(year, month, 1)),
            ("state", "=", "confirmed"),
        ]
        records = self.search(domain)
        income  = sum(r.amount for r in records if r.transaction_type == "income")
        expense = sum(r.amount for r in records if r.transaction_type == "expense")
        return {"income": income, "expense": expense, "net": income - expense}


# ═══════════════════════════════════════════════════════════════════════════════
#  2. การจ่ายเงินเดือนพนักงาน
# ═══════════════════════════════════════════════════════════════════════════════
class EmployeeSalaryPayment(models.Model):
    _name        = "employee.salary.payment"
    _description = "บันทึกการจ่ายเงินเดือนพนักงาน"
    _inherit     = ["mail.thread"]
    _order       = "payment_date desc, id desc"
    _rec_name    = "display_name"

    # ─── สถานะ ───────────────────────────────────────────────────────────────
    STATE = [
        ('draft',     '📝 ร่าง'),
        ('confirmed', '✅ ยืนยัน'),
        ('paid',      '💰 จ่ายแล้ว'),
        ('cancelled', '❌ ยกเลิก'),
    ]

    PAYMENT_METHOD = [
        ('cash',          '💵 เงินสด'),
        ('bank_transfer', '🏦 โอนธนาคาร'),
        ('cheque',        '📄 เช็ค'),
        ('promptpay',     '📱 พร้อมเพย์'),
    ]

    SALARY_TYPE = [
        ('monthly',  '📅 รายเดือน'),
        ('daily',    '📆 รายวัน'),
        ('hourly',   '⏱️ รายชั่วโมง'),
        ('bonus',    '🎁 โบนัส'),
        ('ot',       '🌙 ค่าล่วงเวลา (OT)'),
        ('deduct',   '✂️ หักเงิน'),
    ]

    employee_id     = fields.Many2one(
        "hr.employee", string="พนักงาน", required=True,
        ondelete="restrict", index=True,
    )
    payment_date    = fields.Date(
        string="วันที่จ่าย", required=True, default=fields.Date.today, index=True,
    )
    period_month    = fields.Selection(
        [(str(i), m) for i, m in enumerate([
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
            "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
            "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
        ], 1)],
        string="เดือนที่จ่าย",
        default=lambda self: str(date.today().month),
    )
    period_year     = fields.Integer(
        string="ปีที่จ่าย", default=lambda self: date.today().year,
    )
    salary_type     = fields.Selection(
        SALARY_TYPE, string="ประเภท", required=True, default="monthly",
    )
    base_salary     = fields.Monetary(
        string="เงินเดือนพื้นฐาน (บาท)", currency_field="currency_id",
    )
    ot_hours        = fields.Float(
        string="ชั่วโมง OT", digits=(16, 2), default=0.0,
    )
    ot_rate_per_hour = fields.Monetary(
        string="อัตรา OT ต่อชั่วโมง", currency_field="currency_id",
    )
    ot_amount       = fields.Monetary(
        string="ค่า OT รวม", compute="_compute_ot_amount",
        store=True, currency_field="currency_id",
    )
    bonus_amount    = fields.Monetary(
        string="โบนัส/เงินพิเศษ (บาท)", currency_field="currency_id", default=0.0,
    )
    deduction_amount = fields.Monetary(
        string="หักเงิน (บาท)", currency_field="currency_id", default=0.0,
    )
    deduction_reason = fields.Char(string="เหตุผลหัก")
    total_amount    = fields.Monetary(
        string="ยอดสุทธิ (บาท)", compute="_compute_total", store=True,
        currency_field="currency_id",
    )
    currency_id     = fields.Many2one(
        "res.currency", string="สกุลเงิน",
        default=lambda self: self.env.company.currency_id,
    )
    payment_method  = fields.Selection(
        PAYMENT_METHOD, string="ช่องทางจ่าย", required=True, default="bank_transfer",
    )
    bank_account    = fields.Char(string="เลขบัญชีธนาคาร")
    reference       = fields.Char(string="เลขอ้างอิง/สลิปโอน")
    state           = fields.Selection(
        STATE, string="สถานะ", default="draft", required=True, index=True,
    )
    note            = fields.Text(string="หมายเหตุเพิ่มเติม")
    company_id      = fields.Many2one(
        "res.company", default=lambda self: self.env.company,
    )
    approved_by     = fields.Many2one(
        "res.users", string="อนุมัติโดย", readonly=True,
    )
    paid_by         = fields.Many2one(
        "res.users", string="จ่ายโดย", readonly=True,
    )
    display_name    = fields.Char(compute="_compute_display_name", store=True)

    # ─── Attendance summary (read-only) ──────────────────────────────────────
    attendance_days  = fields.Float(
        string="วันทำงาน (วัน)", digits=(16, 1),
        compute="_compute_attendance_summary", store=False,
    )
    attendance_ot    = fields.Float(
        string="OT จากระบบ (ชม.)", digits=(16, 2),
        compute="_compute_attendance_summary", store=False,
    )

    # ─── SQL Constraints ──────────────────────────────────────────────────────
    _sql_constraints = [
        (
            "unique_employee_period_type",
            "UNIQUE(employee_id, period_year, period_month, salary_type)",
            "มีรายการจ่ายเงินเดือนประเภทนี้ของพนักงานคนนี้ในเดือนนี้แล้ว",
        )
    ]

    # ─── Computed ────────────────────────────────────────────────────────────
    @api.depends("employee_id", "period_month", "period_year", "salary_type")
    def _compute_display_name(self):
        month_map = {
            "1": "ม.ค.", "2": "ก.พ.", "3": "มี.ค.", "4": "เม.ย.",
            "5": "พ.ค.", "6": "มิ.ย.", "7": "ก.ค.", "8": "ส.ค.",
            "9": "ก.ย.", "10": "ต.ค.", "11": "พ.ย.", "12": "ธ.ค.",
        }
        type_map = dict(self.SALARY_TYPE)
        for rec in self:
            emp   = rec.employee_id.name or "?"
            month = month_map.get(str(rec.period_month), "?")
            year  = rec.period_year or "?"
            stype = type_map.get(rec.salary_type, "?")
            rec.display_name = f"{emp} — {month} {year} ({stype})"

    @api.depends("ot_hours", "ot_rate_per_hour")
    def _compute_ot_amount(self):
        for rec in self:
            rec.ot_amount = rec.ot_hours * rec.ot_rate_per_hour

    @api.depends("base_salary", "ot_amount", "bonus_amount", "deduction_amount")
    def _compute_total(self):
        for rec in self:
            rec.total_amount = (
                rec.base_salary + rec.ot_amount + rec.bonus_amount - rec.deduction_amount
            )

    def _compute_attendance_summary(self):
        """ดึงข้อมูลจาก hr.attendance.custom สำหรับแสดงสรุปเดือนนั้น"""
        Att = self.env["hr.attendance.custom"]
        for rec in self:
            if not rec.employee_id or not rec.period_month or not rec.period_year:
                rec.attendance_days = 0.0
                rec.attendance_ot   = 0.0
                continue
            month = int(rec.period_month)
            year  = int(rec.period_year)
            try:
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                d_from = date(year, month, 1)
                d_to   = date(year, month, last_day)
            except Exception:
                rec.attendance_days = 0.0
                rec.attendance_ot   = 0.0
                continue
            records = Att.search([
                ("employee_id", "=", rec.employee_id.id),
                ("work_date", ">=", d_from),
                ("work_date", "<=", d_to),
            ])
            rec.attendance_days = len(records)
            rec.attendance_ot   = sum(r.ot_hours for r in records)

    @api.onchange("employee_id", "period_month", "period_year")
    def _onchange_employee_details(self):
        if self.employee_id:
            self.base_salary = self.employee_id.custom_base_salary
            self.ot_rate_per_hour = self.employee_id.custom_ot_rate
            self.salary_type = self.employee_id.custom_salary_type or "monthly"
            
            if self.period_month and self.period_year:
                # ดึง OT จาก Attendance อัตโนมัติ
                Att = self.env["hr.attendance.custom"]
                month = int(self.period_month)
                year = int(self.period_year)
                from calendar import monthrange
                try:
                    last_day = monthrange(year, month)[1]
                    d_from = date(year, month, 1)
                    d_to = date(year, month, last_day)
                    records = Att.search([
                        ("employee_id", "=", self.employee_id.id),
                        ("work_date", ">=", d_from),
                        ("work_date", "<=", d_to),
                    ])
                    self.ot_hours = sum(r.ot_hours for r in records)
                    
                    # ถ้าเป็นแบบรายวัน ให้คำนวณฐานเงินเดือน = จำนวนวันทำงาน * อัตราต่อวัน
                    if self.salary_type == 'daily':
                        work_days = len(records)
                        self.base_salary = self.employee_id.custom_base_salary * work_days
                    elif self.salary_type == 'hourly':
                        total_worked_hours = sum(r.worked_hours for r in records)
                        self.base_salary = self.employee_id.custom_base_salary * total_worked_hours
                except Exception:
                    self.ot_hours = 0.0

    # ─── Constraints ─────────────────────────────────────────────────────────
    @api.constrains("base_salary", "total_amount")
    def _check_amounts(self):
        for rec in self:
            if rec.base_salary < 0:
                raise ValidationError("เงินเดือนพื้นฐานต้องไม่ติดลบ")
            if rec.deduction_amount < 0:
                raise ValidationError("จำนวนหักเงินต้องไม่ติดลบ")

    # ─── Actions ─────────────────────────────────────────────────────────────
    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError("รายการต้องอยู่ในสถานะร่างจึงจะยืนยันได้")
            rec.write({"state": "confirmed", "approved_by": self.env.user.id})
        return True

    def action_mark_paid(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError("ต้องยืนยันรายการก่อนจึงจะบันทึกการจ่ายได้")
            rec.write({"state": "paid", "paid_by": self.env.user.id})
            # สร้างรายการรายจ่ายอัตโนมัติ
            self.env["store.income.expense"].create({
                "name": f"เงินเดือน {rec.employee_id.name} ({rec.display_name})",
                "transaction_type": "expense",
                "expense_category": "salary",
                "transaction_date": rec.payment_date,
                "amount": rec.total_amount,
                "partner_id": rec.employee_id.address_home_id.id if rec.employee_id.address_home_id else False,
                "reference": rec.reference,
                "note": f"จ่ายเงินเดือนอัตโนมัติ — {rec.display_name}",
                "state": "confirmed",
            })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == "paid":
                raise UserError("ไม่สามารถยกเลิกรายการที่จ่ายแล้ว กรุณาติดต่อผู้จัดการ")
            rec.state = "cancelled"

    def action_reset_draft(self):
        for rec in self:
            if rec.state == "paid":
                raise UserError("ไม่สามารถรีเซ็ตรายการที่จ่ายแล้ว")
            rec.state = "draft"

    def action_open_payslip_import(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '📥 ดึงเงินเดือนจาก HR Payslip',
            'res_model': 'store.payslip.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_year': self.period_year,
                'default_month': self.period_month,
                'default_payment_date': self.payment_date,
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  3. สรุปรายได้ประจำวัน — Daily P&L Summary
#     คำนวณ: รายรับ - รายจ่ายทั้งหมด = กำไรสุทธิ
# ═══════════════════════════════════════════════════════════════════════════════
class StoreDailySummary(models.Model):
    _name        = "store.daily.summary"
    _description = "สรุปรายรับ-รายจ่าย-กำไรสุทธิประจำวัน"
    _order       = "summary_date desc"
    _rec_name    = "summary_date"

    summary_date = fields.Date(
        string="วันที่", required=True, default=fields.Date.today, index=True,
    )
    currency_id  = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id,
    )
    company_id   = fields.Many2one(
        "res.company", default=lambda self: self.env.company,
    )
    note         = fields.Text(string="หมายเหตุ")

    # ─── รายรับ ──────────────────────────────────────────────────────────────
    income_sales    = fields.Monetary(
        string="ยอดขาย (POS/ออนไลน์/ตรง)", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    income_service  = fields.Monetary(
        string="ค่าบริการซ่อม", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    income_other    = fields.Monetary(
        string="รายรับอื่นๆ", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    total_income    = fields.Monetary(
        string="รายรับรวม (บาท)", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )

    # ─── รายจ่าย ─────────────────────────────────────────────────────────────
    expense_purchase  = fields.Monetary(
        string="ค่าสินค้า/อะไหล่", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    expense_salary    = fields.Monetary(
        string="เงินเดือน/ค่าแรง", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    expense_rent      = fields.Monetary(
        string="ค่าเช่า", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    expense_utilities = fields.Monetary(
        string="ค่าสาธารณูปโภค", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    expense_other     = fields.Monetary(
        string="รายจ่ายอื่นๆ", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    total_expense     = fields.Monetary(
        string="รายจ่ายรวม (บาท)", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )

    # ─── กำไร ────────────────────────────────────────────────────────────────
    gross_profit  = fields.Monetary(
        string="กำไรขั้นต้น (รายรับ - ต้นทุนสินค้า)", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    net_profit    = fields.Monetary(
        string="กำไรสุทธิ (บาท)", currency_field="currency_id",
        compute="_compute_totals", store=True,
        help="รายรับรวม − รายจ่ายทั้งหมด = กำไรสุทธิ",
    )
    profit_margin = fields.Float(
        string="% กำไรสุทธิ", digits=(5, 2),
        compute="_compute_totals", store=True,
    )
    transaction_count = fields.Integer(
        string="จำนวนรายการ", compute="_compute_totals", store=True,
    )

    # ─── SQL unique constraint ───────────────────────────────────────────────
    _sql_constraints = [
        ("unique_summary_date", "UNIQUE(summary_date, company_id)",
         "มีสรุปประจำวันนี้แล้ว (1 วัน = 1 สรุป)"),
    ]

    # ─── Computed ────────────────────────────────────────────────────────────
    @api.depends("summary_date")
    def _compute_totals(self):
        """
        รวมรายรับ-รายจ่ายจาก 5 แหล่ง:
          1. POS Orders    (ยอดขายหน้าร้าน)
          2. Account Move  (ใบแจ้งหนี้ลูกค้า/หลังร้าน)
          3. Purchase Order (ค่าซื้อสินค้า)
          4. Salary Payment (เงินเดือนพนักงาน)
          5. Manual IE     (รายการบันทึกมือ)
        """
        for rec in self:
            if not rec.summary_date:
                self._zero_all(rec)
                continue

            d_str  = str(rec.summary_date)
            d_from = fields.Datetime.to_datetime(d_str + " 00:00:00")
            d_to   = fields.Datetime.to_datetime(d_str + " 23:59:59")

            # ── 1. POS Orders (ยอดขายหน้าร้าน) ──────────────────────────────
            pos_orders = self.env["pos.order"].sudo().search([
                ("date_order", ">=", d_from),
                ("date_order", "<=", d_to),
                ("state", "in", ["done", "invoiced", "paid"]),
            ])
            income_pos = sum(o.amount_total for o in pos_orders if o.amount_total > 0)

            # ── 2. Invoice (ใบแจ้งหนี้ลูกค้า/หลังร้าน) ─────────────────────
            invoices = self.env["account.move"].sudo().search([
                ("move_type", "=", "out_invoice"),
                ("invoice_date", "=", rec.summary_date),
                ("state", "=", "posted"),
            ])
            income_invoice = sum(m.amount_total for m in invoices)

            # ── 3. Purchase Orders (ค่าซื้อสินค้า) ──────────────────────────
            purchases = self.env["purchase.order"].sudo().search([
                ("date_approve", ">=", d_from),
                ("date_approve", "<=", d_to),
                ("state", "in", ["purchase", "done"]),
            ])
            expense_purchase_po = sum(p.amount_total for p in purchases)

            # ── 4. Salary Payments (เงินเดือนพนักงาน) ───────────────────────
            salaries = self.env["employee.salary.payment"].sudo().search([
                ("payment_date", "=", rec.summary_date),
                ("state", "=", "paid"),
            ])
            expense_salary_paid = sum(s.net_salary if hasattr(s, 'net_salary') else s.base_salary
                                      for s in salaries)

            # ── 5. Manual store.income.expense ───────────────────────────────
            manual_ie = self.env["store.income.expense"].search([
                ("transaction_date", "=", rec.summary_date),
                ("state", "=", "confirmed"),
            ])
            manual_inc = manual_ie.filtered(lambda r: r.transaction_type == "income")
            manual_exp = manual_ie.filtered(lambda r: r.transaction_type == "expense")

            # ── รวมรายรับ ────────────────────────────────────────────────────
            rec.income_sales   = income_pos + sum(r.amount for r in manual_inc
                                                  if r.income_category in ("sales_pos", "sales_online", "sales_direct"))
            rec.income_service = income_invoice + sum(r.amount for r in manual_inc
                                                      if r.income_category == "service")
            rec.income_other   = sum(r.amount for r in manual_inc
                                     if r.income_category not in ("sales_pos", "sales_online",
                                                                    "sales_direct", "service"))
            rec.total_income   = rec.income_sales + rec.income_service + rec.income_other

            # ── รวมรายจ่าย ──────────────────────────────────────────────────
            rec.expense_purchase  = expense_purchase_po + sum(
                r.amount for r in manual_exp if r.expense_category == "purchase_parts")
            rec.expense_salary    = expense_salary_paid + sum(
                r.amount for r in manual_exp if r.expense_category == "salary")
            rec.expense_rent      = sum(r.amount for r in manual_exp if r.expense_category == "rent")
            rec.expense_utilities = sum(r.amount for r in manual_exp if r.expense_category == "utilities")
            rec.expense_other     = sum(r.amount for r in manual_exp
                                        if r.expense_category not in
                                        ("purchase_parts", "salary", "rent", "utilities"))
            rec.total_expense = (rec.expense_purchase + rec.expense_salary +
                                  rec.expense_rent + rec.expense_utilities + rec.expense_other)

            # ── transaction_count: รวมทุกแหล่ง ─────────────────────────────
            rec.transaction_count = len(pos_orders) + len(invoices) + len(purchases) + len(salaries) + len(manual_ie)

            # ── กำไร ────────────────────────────────────────────────────────
            rec.gross_profit  = rec.total_income - rec.expense_purchase
            rec.net_profit    = rec.total_income - rec.total_expense
            if rec.total_income:
                rec.profit_margin = round((rec.net_profit / rec.total_income) * 100, 2)
            else:
                rec.profit_margin = 0.0

    @staticmethod
    def _zero_all(rec):
        rec.income_sales = rec.income_service = rec.income_other = rec.total_income = 0.0
        rec.expense_purchase = rec.expense_salary = rec.expense_rent = 0.0
        rec.expense_utilities = rec.expense_other = rec.total_expense = 0.0
        rec.gross_profit = rec.net_profit = rec.profit_margin = 0.0
        rec.transaction_count = 0

    # ─── Actions ─────────────────────────────────────────────────────────────
    def action_refresh(self):
        """บังคับ recompute ใหม่"""
        self._compute_totals()
        return True

    def action_view_transactions(self):
        """เปิดดูรายการรายรับ-รายจ่ายของวันนั้น"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"รายการ {self.summary_date}",
            "res_model": "store.income.expense",
            "view_mode": "list,form",
            "domain": [("transaction_date", "=", self.summary_date)],
            "context": {"default_transaction_date": str(self.summary_date)},
        }

    @api.model
    def action_generate_today(self):
        """สร้างหรืออัปเดตสรุปวันนี้"""
        today = date.today()
        rec = self.search([("summary_date", "=", today)], limit=1)
        if not rec:
            rec = self.create({"summary_date": today})
        else:
            rec._compute_totals()
        return {
            "type": "ir.actions.act_window",
            "name": "สรุปรายรับ-รายจ่ายวันนี้",
            "res_model": "store.daily.summary",
            "res_id": rec.id,
            "view_mode": "form",
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  4. Wizard: ดึงยอดขาย POS → store.income.expense + store.daily.summary
#     บัญชีสามารถ sync ข้อมูลจาก POS ได้เองโดยไม่ต้องเป็น POS cashier
# ═══════════════════════════════════════════════════════════════════════════════
class StorePOSSyncWizard(models.TransientModel):
    """
    Wizard ดึงยอดขายจาก POS เข้าระบบบัญชีร้าน
    ─────────────────────────────────────────────────────────────────────
    หมายเหตุ: Daily Summary จะ compute จาก POS โดยตรงอัตโนมัติ
    Wizard นี้ใช้สำหรับ sync ข้อมูลเก่า/ย้อนหลังเท่านั้น
    """
    _name        = "store.pos.sync.wizard"
    _description = "Wizard ดึงยอดขาย POS → ระบบบัญชี"

    date_from = fields.Date(
        string="จากวันที่", required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="ถึงวันที่", required=True,
        default=fields.Date.today,
    )
    pos_config_ids = fields.Many2many(
        "pos.config", string="ร้าน POS (ว่าง = ทั้งหมด)",
        help="เลือกเฉพาะบางร้าน หรือเว้นว่างเพื่อดึงทุกร้าน",
    )
    group_by = fields.Selection(
        [("day", "รวมต่อวัน (1 วัน = 1 รายการ)"),
         ("session", "รวมต่อ Session POS"),
         ("order", "แยกต่อ Order (ละเอียดสุด)")],
        string="การจัดกลุ่ม", required=True, default="day",
    )
    overwrite = fields.Boolean(
        string="เขียนทับรายการที่มีแล้ว",
        default=False,
        help="ถ้าติ๊ก จะ update จำนวนเงินของรายการที่มีอยู่แล้ว"
             "ถ้าไม่ติ๊ก จะข้ามรายการที่ซ้ำ",
    )
    update_daily_summary = fields.Boolean(
        string="อัปเดตสรุปประจำวันอัตโนมัติ",
        default=True,
    )

    # ─── helpers ─────────────────────────────────────────────────────────────
    def _build_pos_domain(self):
        domain = [
            ("date_order", ">=", fields.Datetime.to_datetime(str(self.date_from) + " 00:00:00")),
            ("date_order", "<=", fields.Datetime.to_datetime(str(self.date_to)   + " 23:59:59")),
            ("state", "in", ["done", "invoiced", "paid"]),
        ]
        if self.pos_config_ids:
            domain.append(("config_id", "in", self.pos_config_ids.ids))
        return domain

    # ─── main action ─────────────────────────────────────────────────────────
    def action_sync(self):
        self.ensure_one()
        orders = self.env["pos.order"].sudo().search(self._build_pos_domain())

        if not orders:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบข้อมูล POS",
                    "message": f"ไม่พบ POS Order ที่ done/paid ในช่วง {self.date_from} – {self.date_to}",
                    "sticky": False,
                    "type": "warning",
                },
            }

        IE = self.env["store.income.expense"]
        created = updated = skipped = 0
        daily_totals = {}
        session_totals = {}

        if self.group_by == "day":
            for order in orders:
                d = fields.Date.to_date(order.date_order)
                if d not in daily_totals:
                    daily_totals[d] = {"amount": 0.0, "count": 0}
                daily_totals[d]["amount"] += order.amount_total
                daily_totals[d]["count"]  += 1

            for day, data in daily_totals.items():
                if data["amount"] <= 0:
                    skipped += 1
                    continue
                ref   = f"POS-SYNC-{day}"
                label = f"ยอดขาย POS รวม {data['count']} order — {day}"
                existing = IE.search([
                    ("reference", "=", ref),
                    ("transaction_date", "=", day),
                ], limit=1)
                if existing:
                    if self.overwrite:
                        existing.write({"amount": data["amount"], "name": label})
                        updated += 1
                    else:
                        skipped += 1
                else:
                    IE.create({
                        "name": label,
                        "transaction_type": "income",
                        "income_category": "sales_pos",
                        "transaction_date": day,
                        "amount": data["amount"],
                        "reference": ref,
                        "note": f"Sync จาก POS อัตโนมัติ ({data['count']} orders)",
                        "state": "confirmed",
                    })
                    created += 1

        elif self.group_by == "session":
            for order in orders:
                sid   = order.session_id.id
                d     = fields.Date.to_date(order.date_order)
                sname = order.session_id.name or f"Session-{sid}"
                key   = (sid, d)
                if key not in session_totals:
                    session_totals[key] = {"amount": 0.0, "count": 0, "name": sname}
                session_totals[key]["amount"] += order.amount_total
                session_totals[key]["count"]  += 1

            for (sid, day), data in session_totals.items():
                if data["amount"] <= 0:
                    skipped += 1
                    continue
                ref   = f"POS-SES-{sid}-{day}"
                label = f"ยอดขาย POS Session {data['name']} — {day}"
                existing = IE.search([("reference", "=", ref)], limit=1)
                if existing:
                    if self.overwrite:
                        existing.write({"amount": data["amount"]})
                        updated += 1
                    else:
                        skipped += 1
                else:
                    IE.create({
                        "name": label,
                        "transaction_type": "income",
                        "income_category": "sales_pos",
                        "transaction_date": day,
                        "amount": data["amount"],
                        "reference": ref,
                        "note": f"Session: {data['name']} ({data['count']} orders)",
                        "state": "confirmed",
                    })
                    created += 1

        else:  # order-level
            for order in orders:
                if order.amount_total <= 0:
                    skipped += 1
                    continue
                d   = fields.Date.to_date(order.date_order)
                ref = f"POS-ORD-{order.name}"
                existing = IE.search([("reference", "=", ref)], limit=1)
                if existing:
                    if self.overwrite:
                        existing.write({"amount": order.amount_total})
                        updated += 1
                    else:
                        skipped += 1
                else:
                    IE.create({
                        "name": f"ยอดขาย POS Order {order.name}",
                        "transaction_type": "income",
                        "income_category": "sales_pos",
                        "transaction_date": d,
                        "amount": order.amount_total,
                        "reference": ref,
                        "partner_id": order.partner_id.id if order.partner_id else False,
                        "note": f"Order: {order.name} | {order.session_id.name}",
                        "state": "confirmed",
                    })
                    created += 1

        # อัปเดต daily summary
        if self.group_by == "day":
            affected_dates = set(daily_totals.keys())
        elif self.group_by == "session":
            affected_dates = {day for (_, day) in session_totals.keys()}
        else:
            affected_dates = {fields.Date.to_date(o.date_order) for o in orders}

        if self.update_daily_summary:
            Summary = self.env["store.daily.summary"]
            for d in sorted(affected_dates):
                existing_summary = Summary.search([("summary_date", "=", d)], limit=1)
                if existing_summary:
                    existing_summary._compute_totals()
                else:
                    Summary.create({"summary_date": d})

        return {
            "type": "ir.actions.act_window",
            "name": "📊 รายรับจาก POS",
            "res_model": "store.income.expense",
            "view_mode": "list,form",
            "domain": [
                ("income_category", "=", "sales_pos"),
                ("transaction_date", ">=", str(self.date_from)),
                ("transaction_date", "<=", str(self.date_to)),
            ],
            "context": {},
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  5. Wizard: ดึงสลิปเงินเดือนจาก HR Payslip → employee.salary.payment
# ═══════════════════════════════════════════════════════════════════════════════
class StorePayslipImportWizard(models.TransientModel):
    """
    Wizard สำหรับดึงข้อมูลจาก hr.payslip (Done) เข้า employee.salary.payment
    ─────────────────────────────────────────────────────────────────────────
    ดึงฟิลด์จาก hr.payslip:
      - employee_id       → employee_id
      - wage (contract)   → base_salary
      - net (NET line)    → total_amount / ใช้คำนวณ
      - gross (GROSS)     → base + OT
      - deduction         → deduction_amount
    """
    _name        = "store.payslip.import.wizard"
    _description = "Wizard ดึงสลิปเงินเดือน HR → ระบบบัญชีร้าน"

    year = fields.Integer(
        string="ปี (ค.ศ.)", required=True,
        default=lambda self: date.today().year,
    )
    month = fields.Selection(
        [(str(i), m) for i, m in enumerate([
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน",
            "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม",
            "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
        ], 1)],
        string="เดือน", required=True,
        default=lambda self: str(date.today().month),
    )
    overwrite = fields.Boolean(
        string="เขียนทับรายการที่มีแล้ว",
        default=False,
        help="ถ้าติ๊ก จะ update รายการที่มีอยู่แล้วในเดือนนั้น",
    )
    payment_date = fields.Date(
        string="วันที่จ่าย", required=True,
        default=fields.Date.today,
    )
    state_filter = fields.Selection(
        [("done", "เฉพาะที่ Done แล้ว"),
         ("verify", "รวมที่รอยืนยัน (verify)"),
         ("all", "ทุกสถานะ (ยกเว้น draft)")],
        string="กรองสถานะ Payslip", required=True, default="done",
    )

    def _get_payslip_domain(self):
        m = int(self.month)
        y = self.year
        from calendar import monthrange
        last = monthrange(y, m)[1]
        d_from = date(y, m, 1)
        d_to   = date(y, m, last)

        state_map = {
            "done":   [("state", "=", "done")],
            "verify": [("state", "in", ["done", "verify"])],
            "all":    [("state", "!=", "draft")],
        }
        return [
            ("date_from", ">=", str(d_from)),
            ("date_to",   "<=", str(d_to)),
        ] + state_map.get(self.state_filter, [("state", "=", "done")])

    def action_import(self):
        self.ensure_one()

        # ตรวจสอบว่า hr_payroll module ติดตั้งอยู่ไหม (ถ้าไม่ติด จะ fallback ไปคำนวณจากข้อมูลพนักงาน + Attendance)
        if "hr.payslip" not in self.env:
            employees = self.env["hr.employee"].search([("active", "=", True)])
            if not employees:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "ไม่พบข้อมูลพนักงาน",
                        "message": "ไม่พบพนักงานที่เปิดใช้งานในระบบ",
                        "sticky": False,
                        "type": "warning",
                    },
                }

            SP = self.env["employee.salary.payment"]
            Att = self.env["hr.attendance.custom"]
            m = int(self.month)
            y = self.year
            from calendar import monthrange
            last = monthrange(y, m)[1]
            d_from = date(y, m, 1)
            d_to   = date(y, m, last)

            created = updated = skipped = 0

            for emp in employees:
                # ค้นหาประวัติลงเวลาของพนักงานคนนี้
                attendance_records = Att.search([
                    ("employee_id", "=", emp.id),
                    ("work_date", ">=", d_from),
                    ("work_date", "<=", d_to),
                ])
                work_days = len(attendance_records)
                ot_hours = sum(r.ot_hours for r in attendance_records)

                base_salary = emp.custom_base_salary
                # ถ้าเป็นพนักงานรายวัน ฐานเงินเดือน = อัตราต่อวัน * จำนวนวันทำงาน
                if emp.custom_salary_type == 'daily':
                    base_salary = emp.custom_base_salary * work_days
                elif emp.custom_salary_type == 'hourly':
                    total_worked_hours = sum(r.worked_hours for r in attendance_records)
                    base_salary = emp.custom_base_salary * total_worked_hours

                ot_amount = ot_hours * emp.custom_ot_rate
                total_amount = base_salary + ot_amount

                existing = SP.search([
                    ("employee_id",  "=", emp.id),
                    ("period_month", "=", str(m)),
                    ("period_year",  "=", y),
                ], limit=1)

                vals = {
                    "employee_id":      emp.id,
                    "payment_date":     self.payment_date,
                    "period_month":     str(m),
                    "period_year":      y,
                    "salary_type":      emp.custom_salary_type or "monthly",
                    "base_salary":      base_salary,
                    "ot_hours":         ot_hours,
                    "ot_rate_per_hour": emp.custom_ot_rate,
                    "ot_amount":        ot_amount,
                    "bonus_amount":     0.0,
                    "deduction_amount": 0.0,
                    "note":             f"คำนวณอัตโนมัติจากข้อมูลพนักงาน (เวลาทำงาน {work_days} วัน, OT {ot_hours:.2f} ชม.)",
                    "state":            "draft",
                }

                if existing:
                    if self.overwrite:
                        existing.write(vals)
                        updated += 1
                    else:
                        skipped += 1
                else:
                    SP.create(vals)
                    created += 1

            return {
                "type": "ir.actions.act_window",
                "name": "💸 จ่ายเงินเดือนพนักงาน",
                "res_model": "employee.salary.payment",
                "view_mode": "list,form",
                "domain": [
                    ("period_month", "=", str(m)),
                    ("period_year",  "=", y),
                ],
                "context": {
                    "default_period_month": str(m),
                    "default_period_year":  y,
                },
            }

        # --- Odoo Enterprise hr_payroll fallback ---
        try:
            Payslip = self.env["hr.payslip"].sudo()
        except KeyError:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบโมดูล HR Payroll",
                    "message": "กรุณาติดตั้งโมดูล hr_payroll ก่อนใช้ฟีเจอร์นี้",
                    "sticky": True,
                    "type": "warning",
                },
            }

        SP = self.env["employee.salary.payment"]

        payslips = Payslip.search(self._get_payslip_domain())
        if not payslips:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ไม่พบสลิปเงินเดือน",
                    "message": f"ไม่พบ Payslip ในเดือนที่เลือก (สถานะ: {self.state_filter})",
                    "sticky": False,
                    "type": "warning",
                },
            }

        created = updated = skipped = 0

        for slip in payslips:
            # --- ดึงค่าจาก payslip lines ---
            def get_line(code):
                """ดึงค่าจาก salary rule code (BASIC, GROSS, NET, OT, DEDUCT ฯลฯ)"""
                for ln in slip.line_ids:
                    if ln.code == code:
                        return ln.total or 0.0
                return 0.0

            base_salary    = get_line("BASIC") or (slip.contract_id.wage if slip.contract_id else 0.0)
            gross          = get_line("GROSS") or base_salary
            net_salary     = get_line("NET")   or gross
            ot_amount      = get_line("OT")    or 0.0
            deduction      = max(0.0, gross - net_salary)   # รายหัก = gross - net

            emp = slip.employee_id

            existing = SP.search([
                ("employee_id",  "=", emp.id),
                ("period_month", "=", str(int(self.month))),
                ("period_year",  "=", self.year),
                ("salary_type",  "=", "monthly"),
            ], limit=1)

            vals = {
                "employee_id":      emp.id,
                "payment_date":     self.payment_date,
                "period_month":     str(int(self.month)),
                "period_year":      self.year,
                "salary_type":      "monthly",
                "base_salary":      base_salary,
                "ot_amount":        ot_amount,
                "bonus_amount":     0.0,
                "deduction_amount": deduction,
                "note":             f"นำเข้าจาก HR Payslip: {slip.name or slip.number or ''}",
                "state":            "draft",
            }

            if existing:
                if self.overwrite:
                    existing.write(vals)
                    updated += 1
                else:
                    skipped += 1
            else:
                SP.create(vals)
                created += 1

        return {
            "type": "ir.actions.act_window",
            "name": "💸 จ่ายเงินเดือนพนักงาน",
            "res_model": "employee.salary.payment",
            "view_mode": "list,form",
            "domain": [
                ("period_month", "=", str(int(self.month))),
                ("period_year",  "=", self.year),
            ],
            "context": {
                "default_period_month": str(int(self.month)),
                "default_period_year":  self.year,
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  6. เพิ่มข้อมูลเงินเดือนให้กับ พนักงาน (hr.employee)
# ═══════════════════════════════════════════════════════════════════════════════
class HrEmployee(models.Model):
    _inherit = "hr.employee"

    custom_base_salary = fields.Float(
        string="เงินเดือนพื้นฐาน/วัน/ชั่วโมง (บาท)", default=0.0,
        help="ฐานเงินเดือนรายเดือน หรือ อัตราเงินเดือนรายวัน ของพนักงาน",
    )
    custom_ot_rate = fields.Float(
        string="อัตรา OT (ต่อชั่วโมง)", default=0.0,
        help="อัตราค่าแรงล่วงเวลาต่อชั่วโมง",
    )
    custom_salary_type = fields.Selection(
        [("monthly", "รายเดือน"), ("daily", "รายวัน"), ("hourly", "รายชั่วโมง")],
        string="ประเภทการจ้างงาน", default="monthly",
    )
