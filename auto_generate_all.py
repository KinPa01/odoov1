# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
Full Auto Image Generator + Uploader for Odoo
==============================================
- อ่านรายชื่อสินค้าจาก image_progress.json
- เจนรูปจาก Pollinations.ai (FLUX model) — ฟรี ไม่มี rate limit เข้มงวด
- อัพโหลดรูปเข้า Odoo ผ่าน XML-RPC ทันที
- อัพเดท progress.json อัตโนมัติ
- ไม่ต้องรับ input จากผู้ใช้เลย (fully automated)

Usage:
    python auto_generate_all.py
"""

import json
import time
import base64
import xmlrpc.client
import re
import urllib.request
import urllib.parse
import urllib.error
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

DELAY_BETWEEN_IMAGES = 4     # วินาทีระหว่างแต่ละรูป
RETRY_WAIT_SECONDS   = 30    # รอกี่วินาทีก่อน retry
MAX_RETRIES          = 5     # retry สูงสุดกี่ครั้ง
UPLOAD_TO_ODOO       = True

# =========================================================
# PROMPT TEMPLATES (high quality descriptions)
# =========================================================
PROMPT_TEMPLATES = {
    "น้ำมันเครื่อง":        "Professional product photography, single generic 4-liter plastic motor oil jug container, clean minimalist white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ผ้าเบรกหน้า":          "Professional product photography, set of four flat automotive front brake pads with steel backplates and friction compound lining, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ผ้าเบรกหลัง":          "Professional product photography, set of four flat automotive rear brake pads with steel backplates and friction compound lining, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ผ้าเบรก":              "Professional product photography, set of flat automotive brake pads with steel backplates, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "จานเบรกหน้า":          "Professional product photography, single steel car front brake disc rotor, ventilated design, shiny silver metal surface, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "จานเบรกหลัง":          "Professional product photography, single steel car rear brake disc rotor, shiny silver metal, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "จานเบรก":              "Professional product photography, single steel car brake disc rotor, shiny silver metal, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ก้ามเบรก":             "Professional product photography, automotive rear drum brake shoes set, curved metal backing with friction lining, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "กรองน้ำมันเครื่อง":    "Professional product photography, cylindrical metal car engine oil filter canister, silver and black housing, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "กรองน้ำมัน":           "Professional product photography, cylindrical metal car oil filter canister, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "กรองอากาศ":            "Professional product photography, rectangular automotive engine air filter panel, yellow pleated paper filter with black rubber border frame, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "กรองแอร์":             "Professional product photography, rectangular white pleated cabin air filter element, thick paper accordion folds, plastic frame, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "กรองดีเซล":            "Professional product photography, cylindrical metal diesel fuel filter cartridge, silver housing with fittings, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "แบตเตอรี่":            "Professional product photography, 12V car battery, rectangular dark plastic case, red positive and black negative terminal posts on top, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ลูกหมากปีกนกบน":       "Professional product photography, automotive steel suspension upper control arm ball joint, threaded metal stud and boot, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ลูกหมากปีกนกล่าง":     "Professional product photography, automotive steel suspension lower control arm ball joint, threaded metal stud and dust boot, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ลูกหมากปีกนก":         "Professional product photography, automotive steel suspension control arm ball joint, threaded metal stud, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ลูกหมากแร็ค":          "Professional product photography, automotive metal steering rack end tie rod with threaded end, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ลูกหมาก":              "Professional product photography, automotive steel suspension ball joint with threaded stud, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ยางนอก":               "Professional product photography, single black rubber motorcycle tire standing upright, detailed tread pattern, white studio background, studio lighting, soft shadow, no vehicle no brand logos, photorealistic",
    "ยางรถยนต์":            "Professional product photography, single black rubber car tire standing upright, detailed tread pattern, white studio background, studio lighting, soft shadow, no vehicle no brand logos, photorealistic",
    "ชุดโซ่สเตอร์":         "Professional product photography, motorcycle drive chain and two steel sprockets kit, chain links visible, laid flat on white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "หัวเทียน":             "Professional product photography, single automotive spark plug, white ceramic insulator, threaded metal shell, copper core, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "หลอดไฟหน้า":           "Professional product photography, single H4 halogen car headlight bulb, glass envelope, metal base connector, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "หลอดไฟ":               "Professional product photography, single automotive light bulb, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "สายพานหน้าเครื่อง":    "Professional product photography, black ribbed rubber car engine serpentine belt, coiled flat oval shape, ribbed inner surface, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "สายพานขับเคลื่อน":     "Professional product photography, black rubber CVT drive belt loop, smooth trapezoidal cross-section, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "สายพาน":               "Professional product photography, black rubber drive belt, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "โช้คอัพหน้า (ข้าง)":   "Professional product photography, single car front suspension shock absorber strut, black cylindrical body, chrome piston rod, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "โช้คอัพหลัง (ข้าง)":   "Professional product photography, single car rear suspension shock absorber, black cylindrical metal body, chrome rod, mounting brackets, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "โช้คอัพหน้า":           "Professional product photography, single car front suspension shock absorber strut, black cylindrical body, chrome piston rod, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "โช้คอัพหลัง":           "Professional product photography, single car rear suspension shock absorber, black cylindrical body, chrome rod, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "โช้คอัพ":              "Professional product photography, single car suspension shock absorber, black cylindrical metal body, chrome rod, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "น้ำมันเบรก":           "Professional product photography, generic 500ml plastic bottle of brake fluid, clean design, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "น้ำมันเกียร์":         "Professional product photography, generic 1-liter plastic bottle of transmission gear oil, clean design, white studio background, studio lighting, soft shadow, no text no brand logos, photorealistic",
    "ลูกปืนล้อหน้า":        "Professional product photography, steel car front wheel hub double-row ball bearing, shiny metal ring with ball bearing raceway, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "ลูกปืนล้อหลัง":        "Professional product photography, steel car rear wheel hub double-row ball bearing, shiny metal ring, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "ลูกปืนล้อ":            "Professional product photography, steel car wheel hub bearing, shiny metal ring, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "ลูกปืน":               "Professional product photography, steel automotive double-row ball bearing ring, shiny metal, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "ปั๊มน้ำ":              "Professional product photography, cast aluminum car engine water pump with impeller, mounting flanges, inlet and outlet ports, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "วาล์วน้ำ":             "Professional product photography, car engine thermostat valve, brass and copper housing with temperature sensor, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "หม้อน้ำ":              "Professional product photography, aluminum car radiator core with black plastic tanks, cooling fins, hose connections, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "ยางปัดน้ำฝน":          "Professional product photography, pair of black rubber windshield wiper blades, curved shape, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
    "ฟิวส์":                "Professional product photography, set of colorful plastic automotive blade fuses, blue 15A fuse in foreground, white studio background, studio lighting, soft shadow, no brand logos, photorealistic",
}

DEFAULT_PROMPT = "Professional product photography, automotive spare part, clean white studio background, soft directional studio lighting, soft shadow, no text no brand logos, photorealistic"

# =========================================================
# HELPERS
# =========================================================
def get_prompt(product_name: str) -> str:
    # จับคู่ keyword ยาวสุดก่อน
    for keyword, template in sorted(PROMPT_TEMPLATES.items(), key=lambda x: len(x[0]), reverse=True):
        if keyword in product_name:
            return template
    return DEFAULT_PROMPT

def safe_filename(name: str, product_id: int) -> str:
    clean = re.sub(r'[^\w\s\-]', '', name, flags=re.UNICODE)
    clean = re.sub(r'\s+', '_', clean.strip())
    return f"product_{product_id}_{clean[:60]}.png"

def load_progress() -> dict:
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_progress(data: dict):
    data["done"] = sum(1 for p in data["products"] if p["status"] == "done")
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def mark_status(data: dict, product_id: int, status: str, image_file: str = None):
    for p in data["products"]:
        if p["id"] == product_id:
            p["status"] = status
            if image_file:
                p["image_file"] = image_file
            p["updated_at"] = datetime.now().isoformat()
            break
    save_progress(data)

# =========================================================
# ODOO
# =========================================================
def connect_odoo():
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            print("[ERROR] Odoo login ล้มเหลว")
            return None, None
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        print(f"[ODOO] เชื่อมต่อสำเร็จ uid={uid}")
        return uid, models
    except Exception as e:
        print(f"[WARN] Odoo ไม่พร้อม: {e} — จะ save รูปเท่านั้น")
        return None, None

def upload_to_odoo(uid, models, product_id: int, image_path: Path) -> bool:
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        prod_records = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.product", "search_read",
            [[ ["id", "=", product_id] ]],
            {"fields": ["product_tmpl_id"], "limit": 1}
        )
        if not prod_records:
            # ลอง search จาก product.template โดยตรง
            tmpl_records = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                "product.template", "search_read",
                [[ ["id", "=", product_id] ]],
                {"fields": ["id", "name"], "limit": 1}
            )
            if tmpl_records:
                tmpl_id = tmpl_records[0]["id"]
            else:
                print(f"  [WARN] ไม่พบ product id={product_id}")
                return False
        else:
            tmpl_id = prod_records[0]["product_tmpl_id"][0]

        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.template", "write",
            [[tmpl_id], {"image_1920": img_b64}]
        )
        return True
    except Exception as e:
        print(f"  [ERROR] upload_to_odoo: {e}")
        return False

# =========================================================
# IMAGE GENERATION (Pollinations.ai)
# =========================================================
def generate_image(prompt: str, output_path: Path, seed: int) -> bool:
    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=512&height=512&nologo=true&private=true&enhance=false&model=flux&seed={seed}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            img_bytes = resp.read()

        if len(img_bytes) < 1000:
            print(f"  [WARN] รูปเล็กเกินไป ({len(img_bytes)} bytes)")
            return False

        with open(output_path, "wb") as f:
            f.write(img_bytes)
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        if e.code in [402, 429]:
            raise Exception(f"RATE_LIMIT: {body[:100]}")
        print(f"  [ERROR] HTTP {e.code}: {body[:200]}")
        return False
    except Exception as e:
        err = str(e)
        if any(t in err for t in ["RATE_LIMIT", "429", "402", "Too Many", "Queue full"]):
            raise Exception(f"RATE_LIMIT: {err}")
        print(f"  [ERROR] generate: {e}")
        return False

# =========================================================
# MAIN
# =========================================================
def main():
    print("=" * 60)
    print("  Full Auto Image Generator + Uploader")
    print("  Mode: ทำงานอัตโนมัติ จนกว่าจะครบทุกชิ้น")
    print("=" * 60)

    data = load_progress()
    total = data["total"]

    # กรองเฉพาะ pending และ failed
    to_process = [p for p in data["products"] if p["status"] in ("pending", "failed")]
    print(f"\n[INFO] สินค้าทั้งหมด: {total}")
    print(f"[INFO] done แล้ว:    {data['done']}")
    print(f"[INFO] ที่จะทำ:      {len(to_process)} รายการ")
    print(f"[INFO] Output dir:   {OUTPUT_DIR}\n")

    if not to_process:
        print("[DONE] ทำครบทุกชิ้นแล้ว!")
        return

    # Connect Odoo
    uid, models = (None, None)
    if UPLOAD_TO_ODOO:
        uid, models = connect_odoo()

    success_total = 0
    fail_total    = 0

    for idx, product in enumerate(to_process, 1):
        pid   = product["id"]
        pname = product["name"]
        fname = safe_filename(pname, pid)
        fpath = OUTPUT_DIR / fname

        print(f"\n[{idx}/{len(to_process)}] ID {pid}: {pname}")

        # ถ้ามีไฟล์อยู่แล้ว — ข้าม generate แต่ยัง upload ใหม่
        if not fpath.exists():
            prompt = get_prompt(pname)
            print(f"  → prompt: {prompt[:90]}...")

            success = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    success = generate_image(prompt, fpath, seed=pid)
                    if success:
                        break
                    else:
                        if attempt < MAX_RETRIES:
                            print(f"  [RETRY {attempt}/{MAX_RETRIES}] รอ {RETRY_WAIT_SECONDS}s...")
                            time.sleep(RETRY_WAIT_SECONDS)
                except Exception as e:
                    if "RATE_LIMIT" in str(e) and attempt < MAX_RETRIES:
                        print(f"  [RATE LIMIT] รอ {RETRY_WAIT_SECONDS}s แล้ว retry ({attempt}/{MAX_RETRIES})...")
                        time.sleep(RETRY_WAIT_SECONDS)
                    else:
                        print(f"  [FAIL] {e}")
                        break

            if not success:
                print(f"  [FAIL] เจนรูปไม่สำเร็จ — ข้าม")
                mark_status(data, pid, "failed")
                data = load_progress()
                fail_total += 1
                time.sleep(DELAY_BETWEEN_IMAGES)
                continue

            size_kb = fpath.stat().st_size // 1024
            print(f"  [OK] เจนรูปสำเร็จ ({size_kb} KB)")

        else:
            print(f"  [SKIP gen] ไฟล์มีอยู่แล้ว ({fpath.stat().st_size // 1024} KB) — upload เลย")

        # Upload เข้า Odoo
        uploaded = False
        if UPLOAD_TO_ODOO and uid and models:
            uploaded = upload_to_odoo(uid, models, pid, fpath)
            if uploaded:
                print(f"  [OK] upload Odoo สำเร็จ")
            else:
                print(f"  [WARN] upload ล้มเหลว (รูปอยู่ใน product_images/ แล้ว)")

        mark_status(data, pid, "done", fname)
        data = load_progress()
        done_now = data["done"]
        pct = done_now / total * 100
        print(f"  [Progress] {done_now}/{total} ({pct:.1f}%)")
        success_total += 1

        # Delay
        if idx < len(to_process):
            time.sleep(DELAY_BETWEEN_IMAGES)

    # สรุปสุดท้าย
    data = load_progress()
    failed = [p for p in data["products"] if p["status"] == "failed"]
    print("\n" + "=" * 60)
    print(f"  DONE! เจนรูปเสร็จสิ้น {data['done']}/{data['total']} สินค้า")
    print(f"  สำเร็จรอบนี้: {success_total}  ล้มเหลว: {fail_total}")
    if failed:
        print(f"  WARNING: ล้มเหลวรวม {len(failed)} สินค้า:")
        for p in failed[:10]:
            print(f"     - [{p['id']}] {p['name']}")
    print("=" * 60)

if __name__ == "__main__":
    main()
