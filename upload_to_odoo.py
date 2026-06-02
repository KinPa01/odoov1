# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
Upload Images to Odoo (retry for already-copied files)
"""

import base64
import xmlrpc.client
from pathlib import Path

ODOO_URL      = "http://localhost:8044"
ODOO_DB       = "ran_ahlai_prod"
ODOO_USER     = "admin"
ODOO_PASSWORD = "admin"

OUTPUT_DIR = Path(__file__).parent / "product_images"

# (product_id, filename)
IMAGES_TO_UPLOAD = [
    (9,  "product_9_ยางนอก_Michelin_City_Grip_909014.png"),
    (11, "product_11_ผาเบรกหนา_NMAX.png"),
    (13, "product_13_แบตเตอร_YUASA_YTZ5S.png"),
    (15, "product_15_กรองอากาศ_Yamaha_XMAX_300.png"),
    (17, "product_17_หลอดไฟหนา_Osram_LED.png"),
    (19, "product_19_สายพานขบเคลอน_Yamaha_Aerox_155.png"),
    (20, "product_20_โชคอพหนา_Honda_City.png"),
    (21, "product_21_โชคอพหลง_Toyota_Revo.png"),
    (22, "product_22_นำมนเบรก_DOT_3.png"),
    (23, "product_23_นำมนเกยร_CVT.png"),
    (24, "product_24_จานเบรกหนา_Mitsubishi_Triton.png"),
    (25, "product_25_กามเบรกหลง_Nissan_Navara.png"),
    (26, "product_26_กรองแอร_Honda_Jazz.png"),
    (27, "product_27_กรองดเซล_Isuzu_D-Max.png"),
    (28, "product_28_แบตเตอร_GS_35Ah.png"),
    (29, "product_29_แบตเตอร_FB_65Ah.png"),
    (30, "product_30_หลอดไฟหนา_H4_Philips.png"),
]

def main():
    print("=" * 60)
    print("  Upload Images to Odoo")
    print("=" * 60)

    # Connect Odoo
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            print("[ERROR] Login Odoo ล้มเหลว")
            return
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        print(f"[ODOO] เชื่อมต่อสำเร็จ uid={uid}\n")
    except Exception as e:
        print(f"[ERROR] เชื่อมต่อ Odoo ไม่ได้: {e}")
        return

    success = 0
    fail = 0

    for idx, (pid, fname) in enumerate(IMAGES_TO_UPLOAD, 1):
        fpath = OUTPUT_DIR / fname
        print(f"[{idx}/{len(IMAGES_TO_UPLOAD)}] product_id={pid}: {fname}")

        if not fpath.exists():
            print(f"  [SKIP] ไม่พบไฟล์: {fpath}")
            fail += 1
            continue

        try:
            # อ่านรูปเป็น base64
            with open(fpath, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            # หา product_tmpl_id จาก product.product id
            prod_records = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                "product.product", "search_read",
                [[ ["id", "=", pid] ]],
                {"fields": ["product_tmpl_id"], "limit": 1}
            )

            if not prod_records:
                print(f"  [WARN] ไม่พบ product id={pid} ใน Odoo")
                fail += 1
                continue

            tmpl_id = prod_records[0]["product_tmpl_id"][0]
            tmpl_name = prod_records[0]["product_tmpl_id"][1]

            # Write image
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                "product.template", "write",
                [[tmpl_id], {"image_1920": img_b64}]
            )
            print(f"  [OK] upload สำเร็จ → template_id={tmpl_id} ({tmpl_name})")
            success += 1

        except Exception as e:
            print(f"  [ERROR] {e}")
            fail += 1

    print(f"\n{'='*60}")
    print(f"  สำเร็จ: {success}/{len(IMAGES_TO_UPLOAD)} รูป")
    print(f"  ล้มเหลว: {fail} รูป")
    print("=" * 60)

if __name__ == "__main__":
    main()
