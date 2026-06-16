# -*- coding: utf-8 -*-
"""
hr_attendance_custom.py
─────────────────────────────────────────────────────────────────────────────
ระบบลงเวลาเข้า-ออกงาน (Attendance) สำหรับร้านอาหลั่ย
- เวลางานปกติ 08:00–17:00 น. (Asia/Bangkok, UTC+7)
- รองรับ OT: ถ้าออกหลัง 17:00 → คิด OT อัตโนมัติ
- สามารถ generate ข้อมูลสุ่มย้อนหลังได้ผ่าน wizard
─────────────────────────────────────────────────────────────────────────────
"""
import logging
import random
from datetime import date, datetime, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

TZ_BANGKOK = pytz.timezone("Asia/Bangkok")

# ─── ค่าคงที่เวลางาน ────────────────────────────────────────────────────────
WORK_START_H = 8        # 08:00 น.
WORK_END_H   = 17       # 17:00 น.
OT_MAX_H     = 20       # ออกได้ช้าสุด 20:00 น. (OT 3 ชม.)

# สุ่มค่าเบี่ยง (นาที) สำหรับเวลาเข้า-ออก
CHECK_IN_JITTER  = (-10, +30)   # เข้างาน 07:50–08:30
CHECK_OUT_JITTER = (-5,  +15)   # ออกงาน 16:55–17:15  (ปกติ)
OT_JITTER        = (0,   180)   # OT ได้ถึง +180 นาที (17:00–20:00)
OT_PROBABILITY   = 0.25          # 25% โอกาส OT ต่อวัน


def _to_utc(local_dt: datetime) -> datetime:
    """แปลง naive datetime (Bangkok) → naive datetime (UTC) สำหรับบันทึกใน Odoo."""
    aware = TZ_BANGKOK.localize(local_dt)
    return aware.astimezone(pytz.utc).replace(tzinfo=None)


def _random_time(h: int, m: int, jitter_min: tuple) -> tuple:
    """คืน (hour, minute) หลังบวก jitter แบบสุ่ม"""
    total = h * 60 + m + random.randint(*jitter_min)
    total = max(0, min(23 * 60 + 59, total))
    return divmod(total, 60)


# ═══════════════════════════════════════════════════════════════════════════════
#  Model หลัก: Attendance Record
# ═══════════════════════════════════════════════════════════════════════════════
class HrAttendanceCustom(models.Model):
    _name        = "hr.attendance.custom"
    _description = "บันทึกเวลาเข้า-ออกงาน (ร้านอาหลั่ย)"
    _order       = "check_in desc"
    _rec_name    = "display_name"

    # ─── Fields ──────────────────────────────────────────────────────────────
    employee_id = fields.Many2one(
        "hr.employee", string="พนักงาน", required=True, ondelete="cascade", index=True,
    )
    work_date = fields.Date(string="วันที่", required=True, index=True)

    # เวลาทั้งหมดเก็บ UTC (Odoo standard) แสดงผลด้วย computed field
    check_in  = fields.Datetime(string="เวลาเข้างาน (UTC)", required=True)
    check_out = fields.Datetime(string="เวลาออกงาน (UTC)")

    # computed — แสดงเวลาไทย
    check_in_local  = fields.Char(string="เข้างาน (ไทย)",  compute="_compute_local_times", store=False)
    check_out_local = fields.Char(string="ออกงาน (ไทย)",  compute="_compute_local_times", store=False)

    worked_hours = fields.Float(
        string="ชั่วโมงงาน (ปกติ)", compute="_compute_hours", store=True, digits=(16, 2),
    )
    ot_hours = fields.Float(
        string="OT (ชม.)", compute="_compute_hours", store=True, digits=(16, 2),
    )
    total_hours = fields.Float(
        string="รวมทั้งหมด (ชม.)", compute="_compute_hours", store=True, digits=(16, 2),
    )
    is_late = fields.Boolean(
        string="มาสาย?", compute="_compute_hours", store=True,
    )
    late_minutes = fields.Integer(
        string="สายกี่นาที", compute="_compute_hours", store=True,
    )
    note = fields.Char(string="หมายเหตุ")
    is_random = fields.Boolean(
        string="ข้อมูลสุ่ม (Auto)", default=False,
        help="True = ถูกสร้างโดย wizard สุ่มข้อมูล",
    )

    display_name = fields.Char(compute="_compute_display_name", store=True)

    # ─── Constraints ─────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            "unique_employee_date",
            "UNIQUE(employee_id, work_date)",
            "พนักงานคนนี้มีบันทึกวันนี้แล้ว กรุณาแก้ไขแทนการสร้างใหม่",
        )
    ]

    @api.constrains("check_in", "check_out")
    def _check_times(self):
        for rec in self:
            if rec.check_out and rec.check_in and rec.check_out <= rec.check_in:
                raise ValidationError("เวลาออกต้องมาหลังเวลาเข้าเสมอ")

    # ─── Computed ────────────────────────────────────────────────────────────
    @api.depends("employee_id", "work_date")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or "?"
            dt  = rec.work_date.strftime("%d/%m/%Y") if rec.work_date else "?"
            rec.display_name = f"{emp} — {dt}"

    @api.depends("check_in", "check_out")
    def _compute_local_times(self):
        for rec in self:
            if rec.check_in:
                local_in = pytz.utc.localize(rec.check_in).astimezone(TZ_BANGKOK)
                rec.check_in_local = local_in.strftime("%H:%M น.")
            else:
                rec.check_in_local = "-"
            if rec.check_out:
                local_out = pytz.utc.localize(rec.check_out).astimezone(TZ_BANGKOK)
                rec.check_out_local = local_out.strftime("%H:%M น.")
            else:
                rec.check_out_local = "-"

    @api.depends("check_in", "check_out")
    def _compute_hours(self):
        ot_threshold_h = 17   # 17:00 Bangkok → ถ้าออกหลังนี้คือ OT
        late_threshold  = WORK_START_H * 60 + 15  # 08:15 = มาสาย

        for rec in self:
            if not rec.check_in or not rec.check_out:
                rec.worked_hours = rec.ot_hours = rec.total_hours = 0.0
                rec.is_late      = False
                rec.late_minutes = 0
                continue

            ci_bkk = pytz.utc.localize(rec.check_in).astimezone(TZ_BANGKOK)
            co_bkk = pytz.utc.localize(rec.check_out).astimezone(TZ_BANGKOK)

            # ──── มาสาย ────
            ci_total_min = ci_bkk.hour * 60 + ci_bkk.minute
            if ci_total_min > late_threshold:
                rec.is_late      = True
                rec.late_minutes = ci_total_min - (WORK_START_H * 60)
            else:
                rec.is_late      = False
                rec.late_minutes = 0

            # ──── ชั่วโมงรวม ────
            total_delta = (rec.check_out - rec.check_in).total_seconds() / 3600.0
            rec.total_hours = round(total_delta, 2)

            # ──── OT: ส่วนที่เกิน 17:00 ────
            ot_start_local = co_bkk.replace(
                hour=ot_threshold_h, minute=0, second=0, microsecond=0
            )
            if co_bkk > ot_start_local:
                ot_delta = (co_bkk - ot_start_local).total_seconds() / 3600.0
                rec.ot_hours      = round(ot_delta, 2)
                rec.worked_hours  = round(total_delta - ot_delta, 2)
            else:
                rec.ot_hours     = 0.0
                rec.worked_hours = round(total_delta, 2)

    @api.model
    def _setup_demo_groups(self):
        """กำหนด demo users ไป groups โดยใช้ SQL ตรง (รองรับ Odoo 19)
        เรียกจาก employee_data.xml ผ่าน <function> element
        ทำงานทุกครั้งที่ upgrade โมดูล (idempotent ด้วย ON CONFLICT DO NOTHING)
        """
        assignments = [
            ('warehousepart.user_owner',       'warehousepart.group_spare_owner'),
            ('warehousepart.user_accountant',  'warehousepart.group_spare_accountant'),
            ('warehousepart.user_inv_001',     'warehousepart.group_spare_inventory'),
            ('warehousepart.user_inv_002',     'warehousepart.group_spare_inventory'),
            ('warehousepart.user_inv_003',     'warehousepart.group_spare_inventory'),
            ('warehousepart.user_inv_004',     'warehousepart.group_spare_inventory'),
            ('warehousepart.user_inv_005',     'warehousepart.group_spare_inventory'),
            ('warehousepart.user_front_001',   'warehousepart.group_spare_cashier'),
            ('warehousepart.user_front_002',   'warehousepart.group_spare_cashier'),
        ]
        cr = self.env.cr
        for user_xid, group_xid in assignments:
            try:
                user  = self.env.ref(user_xid,  raise_if_not_found=False)
                group = self.env.ref(group_xid, raise_if_not_found=False)
                if user and group:
                    cr.execute(
                        """INSERT INTO res_groups_users_rel (gid, uid)
                           VALUES (%s, %s)
                           ON CONFLICT DO NOTHING""",
                        (group.id, user.id)
                    )
                    _logger.info("RA: assigned %s → %s", user_xid, group_xid)
            except Exception as e:
                _logger.warning("RA: could not assign %s → %s: %s", user_xid, group_xid, e)


# ═══════════════════════════════════════════════════════════════════════════════
#  Wizard: สร้างข้อมูลสุ่มย้อนหลัง
# ═══════════════════════════════════════════════════════════════════════════════
class AttendanceGenerateWizard(models.TransientModel):
    _name        = "hr.attendance.generate.wizard"
    _description = "Wizard สร้างข้อมูลลงเวลาแบบสุ่ม"

    date_from = fields.Date(
        string="วันที่เริ่มต้น", required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30),
    )
    date_to = fields.Date(
        string="วันที่สิ้นสุด", required=True,
        default=fields.Date.today,
    )
    employee_ids = fields.Many2many(
        "hr.employee", string="พนักงาน",
        help="เว้นว่างไว้ = สร้างให้ทุกคน",
    )
    skip_weekends = fields.Boolean(string="ข้ามวันหยุด (เสาร์-อาทิตย์)", default=True)
    ot_probability = fields.Integer(
        string="โอกาส OT (%)", default=int(OT_PROBABILITY * 100),
        help="0–100 กี่เปอร์เซ็นต์ของวันทำงานที่จะมี OT",
    )
    overwrite = fields.Boolean(
        string="เขียนทับข้อมูลเดิม (ถ้ามี)", default=False,
    )
    result_count = fields.Integer(string="จำนวนรายการที่สร้าง", readonly=True)

    def action_generate(self):
        """สร้างข้อมูลลงเวลาสุ่มตามช่วงวันที่และพนักงานที่เลือก"""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise ValidationError("วันที่เริ่มต้นต้องมาก่อนวันที่สิ้นสุด")

        employees = self.employee_ids or self.env["hr.employee"].search([("active", "=", True)])
        if not employees:
            raise ValidationError("ไม่พบพนักงาน กรุณาสร้างพนักงานก่อน")

        ot_prob = max(0, min(100, self.ot_probability)) / 100.0
        Attendance = self.env["hr.attendance.custom"]
        created = 0

        # วนทุกวันในช่วงเวลา
        current = self.date_from
        while current <= self.date_to:
            # ข้ามวันหยุด
            if self.skip_weekends and current.weekday() >= 5:  # 5=Sat, 6=Sun
                current += timedelta(days=1)
                continue

            for emp in employees:
                # ตรวจว่ามีข้อมูลวันนี้แล้วไหม
                existing = Attendance.search([
                    ("employee_id", "=", emp.id),
                    ("work_date", "=", current),
                ], limit=1)

                if existing and not self.overwrite:
                    current += timedelta(days=1)  # skip วันนี้ของคนนี้
                    continue
                if existing and self.overwrite:
                    existing.unlink()

                # ─── สร้างเวลาเข้า ───
                in_h, in_m = _random_time(WORK_START_H, 0, CHECK_IN_JITTER)
                ci_local   = datetime(current.year, current.month, current.day, in_h, in_m, 0)
                ci_utc     = _to_utc(ci_local)

                # ─── สร้างเวลาออก ───
                has_ot = random.random() < ot_prob
                if has_ot:
                    ot_extra_min = random.randint(*OT_JITTER)   # นาที OT
                    out_h, out_m = _random_time(WORK_END_H, 0, (ot_extra_min, ot_extra_min))
                else:
                    out_h, out_m = _random_time(WORK_END_H, 0, CHECK_OUT_JITTER)

                # ตรวจ: ออกต้องหลังเข้า
                out_total = out_h * 60 + out_m
                in_total  = in_h * 60 + in_m
                if out_total <= in_total:
                    out_total = in_total + 480  # ถ้าผิดพลาด บวก 8 ชม.
                    out_h, out_m = divmod(out_total, 60)

                co_local = datetime(current.year, current.month, current.day, out_h, out_m, 0)
                co_utc   = _to_utc(co_local)

                Attendance.create({
                    "employee_id": emp.id,
                    "work_date":   current,
                    "check_in":    ci_utc,
                    "check_out":   co_utc,
                    "is_random":   True,
                    "note":        "สร้างอัตโนมัติ (Auto-generated)" + (" + OT" if has_ot else ""),
                })
                created += 1

            current += timedelta(days=1)

        self.result_count = created
        return {
            "type":    "ir.actions.act_window",
            "name":    f"ผลลัพธ์: สร้างข้อมูลลงเวลา {created} รายการ",
            "res_model": "hr.attendance.custom",
            "view_mode": "list,form",
            "target":  "current",
        }
