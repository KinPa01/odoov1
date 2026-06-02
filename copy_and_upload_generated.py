# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
Copy Generated Images → product_images/ + Upload to Odoo
=========================================================
- Copy รูปที่ AI สร้างจาก artifact directory → product_images/
- Upload เข้า Odoo ผ่าน XML-RPC
- Update image_progress.json
"""

import json
import os
import shutil
import base64
import xmlrpc.client
from pathlib import Path
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================
ODOO_URL      = "http://localhost:8044"
ODOO_DB       = "ran_ahlai_prod"
ODOO_USER     = "admin"
ODOO_PASSWORD = "admin"

PROGRESS_FILE = Path(__file__).parent / "image_progress.json"
OUTPUT_DIR    = Path(__file__).parent / "product_images"
OUTPUT_DIR.mkdir(exist_ok=True)

# Artifact directory ที่ AI สร้างรูปไว้
ARTIFACT_DIR = Path(r"C:\Users\autod\.gemini\antigravity-ide\brain\e1990bae-5b41-4110-a88e-e2fceb9a2470")

# mapping: product_id → (artifact filename pattern, target filename)
GENERATED_IMAGES = [
    # (product_id, product_name, artifact_file, target_filename)
    (9,  "ยางนอก Michelin City Grip 90/90-14",    "product_9_motorcycle_tire_9090_14_1779896611084.png",       "product_9_ยางนอก_Michelin_City_Grip_909014.png"),
    (11, "ผ้าเบรกหน้า NMAX",                      "product_11_brake_pads_nmax_front_1779896631486.png",        "product_11_ผาเบรกหนา_NMAX.png"),
    (13, "แบตเตอรี่ YUASA YTZ5S",                 "product_13_battery_yuasa_ytz5s_1779896653758.png",          "product_13_แบตเตอร_YUASA_YTZ5S.png"),
    (15, "กรองอากาศ Yamaha XMAX 300",              "product_15_air_filter_yamaha_xmax300_1779896676256.png",    "product_15_กรองอากาศ_Yamaha_XMAX_300.png"),
    (17, "หลอดไฟหน้า Osram LED",                  "product_17_led_headlight_bulb_osram_1779896697790.png",     "product_17_หลอดไฟหนา_Osram_LED.png"),
    (19, "สายพานขับเคลื่อน Yamaha Aerox 155",      "product_19_drive_belt_yamaha_aerox155_1779896717436.png",   "product_19_สายพานขบเคลอน_Yamaha_Aerox_155.png"),
    (20, "โช้คอัพหน้า Honda City",                 "product_20_front_shock_absorber_honda_city_1779896737060.png", "product_20_โชคอพหนา_Honda_City.png"),
    (21, "โช้คอัพหลัง Toyota Revo",                "product_21_rear_shock_absorber_toyota_revo_1779896760005.png", "product_21_โชคอพหลง_Toyota_Revo.png"),
    (22, "น้ำมันเบรก DOT 3",                       "product_22_brake_fluid_dot3_1779896781902.png",             "product_22_นำมนเบรก_DOT_3.png"),
    (23, "น้ำมันเกียร์ CVT",                       "product_23_cvt_gear_oil_1779896803220.png",                 "product_23_นำมนเกยร_CVT.png"),
    (24, "จานเบรกหน้า Mitsubishi Triton",          "product_24_front_brake_disc_triton_1779896825015.png",      "product_24_จานเบรกหนา_Mitsubishi_Triton.png"),
    (25, "ก้ามเบรกหลัง Nissan Navara",             "product_25_brake_shoe_nissan_navara_1779896845965.png",     "product_25_กามเบรกหลง_Nissan_Navara.png"),
    (26, "กรองแอร์ Honda Jazz",                    "product_26_cabin_air_filter_honda_jazz_1779896869452.png",  "product_26_กรองแอร_Honda_Jazz.png"),
    (27, "กรองดีเซล Isuzu D-Max",                  "product_27_diesel_fuel_filter_isuzu_dmax_1779896889413.png","product_27_กรองดเซล_Isuzu_D-Max.png"),
    (28, "แบตเตอรี่ GS 35Ah",                      "product_28_car_battery_gs_35ah_1779896907581.png",          "product_28_แบตเตอร_GS_35Ah.png"),
    (29, "แบตเตอรี่ FB 65Ah",                      "product_29_car_battery_fb_65ah_1779896927691.png",          "product_29_แบตเตอร_FB_65Ah.png"),
    (30, "หลอดไฟหน้า H4 Philips",                  "product_30_h4_halogen_bulb_philips_1779896949461.png",      "product_30_หลอดไฟหนา_H4_Philips.png"),
]

# =========================================================
def load_progress():
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_progress(data):
    data["done"] = sum(1 for p in data["products"] if p["status"] == "done")
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def mark_done(data, product_id, image_file):
    for p in data["products"]:
        if p["id"] == product_id:
            p["status"] = "done"
            p["image_file"] = image_file
            p["updated_at"] = datetime.now().isoformat()
            break
    save_progress(data)

def connect_odoo():
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            print("[ERROR] Login Odoo ล้มเหลว")
            return None, None
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        print(f"[ODOO] เชื่อมต่อสำเร็จ uid={uid}")
        return uid, models
    except Exception as e:
        print(f"[WARN] ไม่สามารถเชื่อมต่อ Odoo: {e}")
        return None, None

def upload_image_to_odoo(uid, models, product_id, image_path):
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        prod_records = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.product", "search_read",
            [[[["id", "=", product_id]]]],
            {"fields": ["product_tmpl_id"], "limit": 1}
        )
        if not prod_records:
            print(f"  [WARN] ไม่พบ product id={product_id} ใน Odoo")
            return False

        tmpl_id = prod_records[0]["product_tmpl_id"][0]
        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.template", "write",
            [[tmpl_id], {"image_1920": img_b64}]
        )
        return True
    except Exception as e:
        print(f"  [ERROR] upload: {e}")
        return False

def main():
    print("=" * 60)
    print("  Copy & Upload Generated Images → Odoo")
    print("=" * 60)

    data = load_progress()
    uid, models = connect_odoo()

    success_count = 0
    fail_count = 0

    for idx, (pid, pname, artifact_file, target_file) in enumerate(GENERATED_IMAGES, 1):
        src = ARTIFACT_DIR / artifact_file
        dst = OUTPUT_DIR / target_file

        print(f"\n[{idx}/{len(GENERATED_IMAGES)}] ID {pid}: {pname}")

        # ตรวจสอบไฟล์ต้นทาง
        if not src.exists():
            print(f"  [SKIP] ไม่พบไฟล์: {src}")
            fail_count += 1
            continue

        # Copy ไฟล์
        try:
            shutil.copy2(src, dst)
            print(f"  [OK] copy → {target_file} ({src.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"  [ERROR] copy ล้มเหลว: {e}")
            fail_count += 1
            continue

        # Upload เข้า Odoo
        uploaded = False
        if uid and models:
            uploaded = upload_image_to_odoo(uid, models, pid, dst)
            if uploaded:
                print(f"  [OK] upload เข้า Odoo สำเร็จ (product_id={pid})")
            else:
                print(f"  [WARN] upload ล้มเหลว (รูปอยู่ใน product_images/ แล้ว)")

        # Update progress
        mark_done(data, pid, target_file)
        data = load_progress()  # reload
        done_now = data["done"]
        total    = data["total"]
        print(f"  [Progress] {done_now}/{total} ({done_now/total*100:.1f}%)")
        success_count += 1

    # สรุป
    print("\n" + "=" * 60)
    print(f"  สำเร็จ: {success_count} รูป")
    print(f"  ล้มเหลว: {fail_count} รูป")
    data = load_progress()
    print(f"  Progress รวม: {data['done']}/{data['total']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
