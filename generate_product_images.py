# -*- coding: utf-8 -*-
import sys
import io
# Force UTF-8 output so Thai/Unicode prints correctly in PowerShell
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
Auto Product Image Generator for Odoo
======================================
- อ่านรายชื่อสินค้าจาก image_progress.json
- เจนรูปจาก Gemini Imagen API
- อัพโหลดรูปเข้า Odoo ผ่าน XML-RPC
- อัพเดท progress อัตโนมัติ
- handle rate limit ด้วย auto-retry

Usage:
    pip install google-generativeai pillow requests
    python generate_product_images.py
"""

import json
import os
import time
import base64
import xmlrpc.client
import re
import sys
from pathlib import Path
from datetime import datetime

# =========================================================
# CONFIG - แก้ตามระบบของคุณ
# =========================================================
HF_TOKEN = os.environ.get("HF_TOKEN", "")

ODOO_URL      = "http://localhost:8044"
ODOO_DB       = "ran_ahlai_prod"
ODOO_USER     = "admin"
ODOO_PASSWORD = "admin"

PROGRESS_FILE  = Path(__file__).parent / "image_progress.json"
OUTPUT_DIR     = Path(__file__).parent / "product_images"
OUTPUT_DIR.mkdir(exist_ok=True)

# Rate-limit config
DELAY_BETWEEN_IMAGES   = 6    # วินาทีระหว่างแต่ละรูป (ป้องกัน rate limit)
RETRY_WAIT_SECONDS     = 90   # รอกี่วินาทีก่อน retry เมื่อเจอ 429
MAX_RETRIES            = 5    # retry สูงสุดกี่ครั้ง
UPLOAD_TO_ODOO         = True  # ตั้งเป็น False ถ้าต้องการแค่ save ไฟล์โดยไม่ upload

# =========================================================
# PRODUCT-TYPE → PROMPT MAPPING
# =========================================================
PROMPT_TEMPLATES = {
    "น้ำมันเครื่อง":    "Close-up product photo of a generic 4-liter plastic motor oil jug container, simple clean label without text, white studio background, professional commercial photography, no brand logos",
    "ผ้าเบรกหน้า":      "Close-up product photo of a set of four flat automotive front brake pads with steel backplates and friction lining, white studio background, clean professional lighting, no brand logos",
    "ผ้าเบรกหลัง":      "Close-up product photo of a set of four flat automotive rear brake pads with steel backplates and friction lining, white studio background, clean professional lighting, no brand logos",
    "ผ้าเบรก":          "Close-up product photo of a set of flat automotive brake pads, white studio background, clean professional lighting, no brand logos",
    "จานเบรกหน้า":      "Close-up product photo of a single steel car front brake disc rotor, shiny metal surface, white studio background, professional lighting, no brand logos",
    "จานเบรกหลัง":      "Close-up product photo of a single steel car rear brake disc rotor, shiny metal surface, white studio background, professional lighting, no brand logos",
    "จานเบรก":          "Close-up product photo of a single steel car brake disc rotor, shiny metal surface, white studio background, professional lighting, no brand logos",
    "ก้ามเบรก":         "Close-up product photo of automotive brake shoe pads set, curved metal backing, white studio background, professional lighting, no brand logos",
    "กรองน้ำมันเครื่อง": "Close-up product photo of a cylindrical metal car engine oil filter canister, white studio background, professional automotive parts photography, no brand logos",
    "กรองน้ำมัน":       "Close-up product photo of a cylindrical metal car engine oil filter canister, white studio background, professional automotive parts photography, no brand logos",
    "กรองอากาศ":        "Close-up product photo of a rectangular automotive engine air filter panel, yellow pleated paper filter with black rubber border, white studio background, professional automotive parts photography, no brand logos",
    "กรองแอร์":         "Close-up product photo of a rectangular white pleated cabin air filter element for cars, white studio background, professional lighting, no brand logos",
    "กรองดีเซล":        "Close-up product photo of a cylindrical metal diesel fuel filter cartridge for cars, white studio background, professional lighting, no brand logos",
    "แบตเตอรี่":        "Close-up product photo of a rectangular 12V plastic car battery, red positive and black negative terminal posts on top, white studio background, professional lighting, no brand logos",
    "ลูกหมากปีกนกบน":   "Close-up product photo of an automotive steel suspension upper ball joint with threaded metal stud, white studio background, professional lighting, no brand logos",
    "ลูกหมากปีกนกล่าง":   "Close-up product photo of an automotive steel suspension lower ball joint with threaded metal stud, white studio background, professional lighting, no brand logos",
    "ลูกหมากปีกนก":     "Close-up product photo of an automotive steel suspension control arm ball joint with threaded metal stud, white studio background, professional lighting, no brand logos",
    "ลูกหมากแร็ค":      "Close-up product photo of an automotive metal steering rack end tie rod, white studio background, no brand logos",
    "ลูกหมาก":          "Close-up product photo of an automotive steel suspension ball joint with threaded stud, white studio background, professional lighting, no brand logos",
    "ยางนอก":           "Product photo of a single black rubber motorcycle tire standing upright, detailed tread pattern, white studio background, professional lighting, no brand logos, no vehicle",
    "ยางรถยนต์":        "Product photo of a single black rubber car tire standing upright, detailed tread pattern, white studio background, professional lighting, no brand logos, no vehicle",
    "ชุดโซ่สเตอร์":    "Product photo of a motorcycle drive chain and two steel sprockets kit laid flat, white studio background, professional lighting, no brand logos, no vehicle",
    "หัวเทียน":         "Close-up product photo of a single automotive spark plug, white ceramic insulator, threaded metal shell, white studio background, professional lighting, no brand logos",
    "หลอดไฟหน้า":       "Product photo of a single H4 halogen car headlight bulb, metal base and glass envelope, white studio background, professional lighting, no brand logos",
    "หลอดไฟ":           "Product photo of a single automotive light bulb, white studio background, professional lighting, no brand logos",
    "สายพานหน้าเครื่อง": "Close-up product photo of a black ribbed rubber car engine serpentine belt coiled neatly, white studio background, professional lighting, no brand logos",
    "สายพานขับเคลื่อน": "Close-up product photo of a black rubber drive belt loop, white studio background, professional lighting, no brand logos",
    "สายพาน":           "Close-up product photo of a black rubber drive belt loop, white studio background, professional lighting, no brand logos",
    "โช้คอัพหน้า (ข้าง)": "Close-up product photo of a single car front suspension shock absorber strut, black steel cylinder, white studio background, professional lighting, no brand logos",
    "โช้คอัพหลัง (ข้าง)": "Close-up product photo of a single car rear suspension shock absorber strut, black steel cylinder, white studio background, professional lighting, no brand logos",
    "โช้คอัพหน้า":       "Close-up product photo of a single car front suspension shock absorber strut, black steel cylinder, white studio background, professional lighting, no brand logos",
    "โช้คอัพหลัง":       "Close-up product photo of a single car rear suspension shock absorber strut, black steel cylinder, white studio background, professional lighting, no brand logos",
    "โช้คอัพ":          "Close-up product photo of a single car suspension shock absorber strut, black steel cylinder, white studio background, professional lighting, no brand logos",
    "น้ำมันเบรก":       "Close-up product photo of a generic 1-liter plastic bottle of brake fluid, simple label without text, white studio background, professional lighting, no brand logos",
    "น้ำมันเกียร์":     "Close-up product photo of a generic 1-liter plastic bottle of transmission fluid, simple label without text, white studio background, professional lighting, no brand logos",
    "ลูกปืนล้อหน้า":     "Close-up product photo of a steel car front wheel double-row ball bearing ring, white studio background, professional lighting, no brand logos",
    "ลูกปืนล้อหลัง":     "Close-up product photo of a steel car rear wheel double-row ball bearing ring, white studio background, professional lighting, no brand logos",
    "ลูกปืนล้อ":         "Close-up product photo of a steel car wheel double-row ball bearing ring, white studio background, professional lighting, no brand logos",
    "ลูกปืน":           "Close-up product photo of a steel automotive double-row ball bearing ring, white studio background, professional lighting, no brand logos",
    "ปั๊มน้ำ":          "Close-up product photo of a cast aluminum car engine water pump, white studio background, professional lighting, no brand logos",
    "วาล์วน้ำ":         "Close-up product photo of a copper and brass car engine thermostat valve, white studio background, professional lighting, no brand logos",
    "หม้อน้ำ":          "Close-up product photo of an aluminum car engine radiator core with black plastic tanks, white studio background, professional lighting, no brand logos",
    "ยางปัดน้ำฝน":      "Close-up product photo of a pair of black rubber windshield wiper blades, white studio background, professional lighting, no brand logos",
    "ฟิวส์":            "Close-up product photo of a set of colorful plastic automotive blade fuses, white studio background, professional lighting, no brand logos",
    "อะไหล่":           "Close-up product photo of generic metal automotive spare part, white studio background, professional commercial lighting",
}

DEFAULT_PROMPT = "Close-up product photo of automotive spare part '{name}', clean white studio background, professional commercial photography, no brand logos, high quality"


TYPE_TRANSLATIONS = {
    "น้ำมันเครื่อง": "motor oil",
    "ผ้าเบรกหน้า": "front brake pads",
    "ผ้าเบรกหลัง": "rear brake pads",
    "ผ้าเบรก": "brake pads",
    "จานเบรกหน้า": "front brake disc",
    "จานเบรกหลัง": "rear brake disc",
    "จานเบรก": "brake disc",
    "ก้ามเบรก": "brake caliper",
    "กรองน้ำมันเครื่อง": "engine oil filter",
    "กรองน้ำมัน": "oil filter",
    "กรองอากาศ": "engine air filter",
    "กรองแอร์": "cabin air filter",
    "กรองดีเซล": "diesel fuel filter",
    "แบตเตอรี่": "car battery",
    "ลูกหมากปีกนกบน": "upper ball joint",
    "ลูกหมากปีกนกล่าง": "lower ball joint",
    "ลูกหมากปีกนก": "ball joint",
    "ลูกหมากแร็ค": "steering rack end",
    "ลูกหมาก": "suspension ball joint",
    "ยางนอก": "motorcycle tire",
    "ยางรถยนต์": "car tire",
    "ชุดโซ่สเตอร์": "motorcycle chain and sprocket kit",
    "หัวเทียน": "spark plug",
    "หลอดไฟหน้า": "headlight bulb",
    "หลอดไฟ": "light bulb",
    "สายพานหน้าเครื่อง": "serpentine drive belt",
    "สายพานขับเคลื่อน": "drive belt",
    "สายพาน": "drive belt",
    "โช้คอัพหน้า (ข้าง)": "front shock absorber",
    "โช้คอัพหลัง (ข้าง)": "rear shock absorber",
    "โช้คอัพหน้า": "front shock absorber",
    "โช้คอัพหลัง": "rear shock absorber",
    "โช้คอัพ": "shock absorber",
    "น้ำมันเบรก": "brake fluid bottle",
    "น้ำมันเกียร์": "gear oil bottle",
    "ลูกปืนล้อหน้า": "front wheel bearing",
    "ลูกปืนล้อหลัง": "rear wheel bearing",
    "ลูกปืนล้อ": "wheel bearing",
    "ลูกปืน": "bearing",
    "ปั๊มน้ำ": "water pump",
    "วาล์วน้ำ": "thermostat valve",
    "หม้อน้ำ": "engine radiator",
    "ยางปัดน้ำฝน": "wiper blade",
    "ฟิวส์": "automotive fuse",
    "อะไหล่": "spare part"
}

def get_english_name(product_name: str) -> str:
    # 1. ค้นหาคำแปลภาษาไทยที่ตรงกันยาวที่สุดก่อน เพื่อเอาเฉพาะประเภทสินค้าแบบไม่มีแบรนด์
    for thai_type, eng_type in sorted(TYPE_TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        if thai_type in product_name:
            return eng_type
    return "automotive spare part"


def get_prompt(product_name: str) -> str:
    eng_name = get_english_name(product_name)
    for keyword, template in PROMPT_TEMPLATES.items():
        if keyword in product_name:
            return template.format(name=eng_name)
    return DEFAULT_PROMPT.format(name=eng_name)


def safe_filename(name: str, product_id: int) -> str:
    clean = re.sub(r'[^\w\s\-]', '', name, flags=re.UNICODE)
    clean = re.sub(r'\s+', '_', clean.strip())
    return f"product_{product_id}_{clean[:60]}.png"


# =========================================================
# GEMINI IMAGE GENERATION
# =========================================================
def generate_image_hf(prompt: str, output_path: Path, seed: int = None) -> bool:
    """
    เจนรูปด้วย Pollinations.ai (FLUX model)
    ฟรี ไม่ต้องใช้ token รวดเร็ว และไม่มี rate limit เข้มงวด
    """
    import urllib.request
    import urllib.parse
    import urllib.error
    import time

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&nologo=true&private=true&enhance=false&model=flux"
    if seed is not None:
        url += f"&seed={seed}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as response:
            img_bytes = response.read()

        if len(img_bytes) < 1000:
            print(f"  [WARN] รูปเล็กเกินไป ({len(img_bytes)} bytes)")
            return False

        with open(output_path, "wb") as f:
            f.write(img_bytes)
        return True

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        if e.code in [402, 429]:
            raise RateLimitError(body)
        print(f"  [ERROR] HTTP {e.code}: {body[:200]}")
        return False
    except Exception as e:
        err_str = str(e)
        if any(tok in err_str for tok in ["402", "429", "Too Many", "Queue full", "queued"]):
            raise RateLimitError(err_str)
        print(f"  [ERROR] generate_image (Pollinations): {e}")
        return False


class RateLimitError(Exception):
    pass


# =========================================================
# ODOO XML-RPC UPLOAD
# =========================================================
def connect_odoo():
    """เชื่อมต่อ Odoo และ return (uid, models)"""
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            print("[ERROR] Login Odoo ล้มเหลว — ตรวจสอบ URL/DB/USER/PASSWORD")
            return None, None
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        print(f"[ODOO] เชื่อมต่อสำเร็จ uid={uid}")
        return uid, models
    except Exception as e:
        print(f"[WARN] ไม่สามารถเชื่อมต่อ Odoo: {e}")
        print("[WARN] จะ save รูปไฟล์อย่างเดียวโดยไม่ upload")
        return None, None


def upload_image_to_odoo(uid, models, product_id: int, image_path: Path) -> bool:
    """อ่านไฟล์รูปแล้ว upload เป็น base64 เข้า product.template"""
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        # หา product.template id จาก product id
        # (product.product → product_tmpl_id)
        prod_records = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "product.product", "search_read",
            [[["id", "=", product_id]]],
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
        print(f"  [ERROR] upload_image_to_odoo: {e}")
        return False


# =========================================================
# PROGRESS FILE
# =========================================================
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
# INTERACTIVE MODE FUNCTIONS
# =========================================================
def run_single_generation(product, data, uid, models) -> bool:
    pid = product["id"]
    pname = product["name"]
    fname = safe_filename(pname, pid)
    fpath = OUTPUT_DIR / fname

    print(f"\n[เริ่มทำงาน] ID {pid}: {pname}")
    print(f"  -> ไฟล์ภาพ: {fname}")

    # ถ้ามีไฟล์อยู่แล้ว ถามว่าจะเขียนทับไหม หรือข้ามการ generate
    if fpath.exists():
        confirm = input(f"  → ไฟล์ {fname} มีอยู่แล้ว ต้องการเจนรูปทับหรือไม่? (y/n) [Default: n]: ").strip().lower()
        if confirm != 'y':
            print("  → ข้ามการ generate (ใช้ไฟล์เดิมที่มีอยู่)")
        else:
            print("  → กำลังลบรูปเดิมเพื่อเจนใหม่...")
            try:
                fpath.unlink()
            except Exception as e:
                print(f"  [ERROR] ไม่สามารถลบไฟล์เดิมได้: {e}")
                
    if not fpath.exists():
        prompt = get_prompt(pname)
        print(f"  -> prompt: {prompt}")

        # retry loop สำหรับ rate limit
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                success = generate_image_hf(prompt, fpath, pid)
                break
            except RateLimitError as e:
                if attempt < MAX_RETRIES:
                    print(f"  [RATE LIMIT] รอ {RETRY_WAIT_SECONDS}s แล้ว retry ({attempt}/{MAX_RETRIES})...")
                    time.sleep(RETRY_WAIT_SECONDS)
                else:
                    print(f"  [FAIL] หมด retry — ไม่สำเร็จ")
                    mark_status(data, pid, "failed")
                    success = False

        if not success:
            return False

    print("  [OK] เจนรูปสำเร็จ")

    # Upload เข้า Odoo
    uploaded = False
    if UPLOAD_TO_ODOO and uid and models:
        uploaded = upload_image_to_odoo(uid, models, pid, fpath)
        if uploaded:
            print("  [OK] upload เข้า Odoo สำเร็จ")
        else:
            print("  [FAIL] upload ล้มเหลว (รูปบันทึกไว้ใน product_images/ แล้ว)")

    mark_status(data, pid, "done", str(fname))
    
    # สรุปความคืบหน้า
    done_now = data["done"]
    total = data["total"]
    print(f"  [Progress] {done_now}/{total} ({done_now/total*100:.1f}%)")
    return True


def run_interactive(data, uid, models):
    print("\n" + "=" * 60)
    print("  โหมดใส่ทีละอัน (Interactive Mode)")
    print("  - พิมพ์ชื่อสินค้า/คีย์เวิร์ด หรือ ID เพื่อค้นหา")
    print("  - พิมพ์ 'q' หรือ 'exit' เพื่อออกจากโหมดนี้")
    print("=" * 60 + "\n")

    while True:
        # โหลดข้อมูลอัปเดตสุดจากไฟล์เสมอ
        data = load_progress()
        query = input("ค้นหาสินค้า (ชื่อ หรือ ID) > ").strip()
        if not query:
            continue
        if query.lower() in ['q', 'exit', 'quit']:
            print("ออกจากโหมด Interactive Mode")
            break

        # ค้นหาด้วย ID หรือ ชื่อ
        matched = []
        if query.isdigit():
            search_id = int(query)
            matched = [p for p in data["products"] if p["id"] == search_id]
        
        if not matched:
            # ค้นหาด้วยคำค้นหาแบบไม่สนพิมพ์เล็กใหญ่ (case-insensitive substring)
            matched = [p for p in data["products"] if query.lower() in p["name"].lower()]

        if not matched:
            print(f"❌ ไม่พบสินค้าสำหรับคำค้นหา: '{query}'")
            continue

        if len(matched) == 1:
            product = matched[0]
            print(f"\nพบสินค้า 1 รายการ:")
            print(f"  ID:     {product['id']}")
            print(f"  ชื่อ:    {product['name']}")
            print(f"  สถานะ:  {product['status']}")
            if "image_file" in product:
                print(f"  รูปเดิม: {product['image_file']}")
            
            confirm = input("ต้องการเจนรูปสินค้าชิ้นนี้ใช่หรือไม่? (y/n) [Default: y]: ").strip().lower()
            if confirm == '' or confirm == 'y':
                run_single_generation(product, data, uid, models)
        else:
            print(f"\nพบสินค้าที่ตรงกัน {len(matched)} รายการ (แสดงสูงสุด 15 รายการ):")
            # เรียงตาม ID
            matched = sorted(matched, key=lambda x: x["id"])
            for idx, p in enumerate(matched[:15], 1):
                status_str = f"[{p['status'].upper()}]"
                print(f"  {idx}. ID: {p['id']} - {p['name']} {status_str}")
            
            if len(matched) > 15:
                print(f"  ... และสินค้าอื่นๆ อีก {len(matched) - 15} รายการ")
            
            select_input = input("\nใส่ ID สินค้าที่ต้องการเลือก (หรือกด Enter เพื่อค้นหาใหม่): ").strip()
            if not select_input:
                continue
            
            if select_input.isdigit():
                sel_id = int(select_input)
                sel_prod = next((p for p in matched if p["id"] == sel_id), None)
                if sel_prod:
                    run_single_generation(sel_prod, data, uid, models)
                else:
                    print("❌ ID ที่ระบุไม่อยู่ในรายการที่ค้นพบ")
            else:
                print("❌ กรุณาป้อนหมายเลข ID")


# =========================================================
# MAIN
# =========================================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Auto Product Image Generator for Odoo")
    parser.add_argument("--mode", type=int, choices=[1, 2], help="1: Auto mode, 2: Interactive mode")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing image files")
    parser.add_argument("--all", action="store_true", help="Process all products (even done/failed ones)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Auto Product Image Generator for Odoo")
    print("=" * 60)

    # โหลด progress
    data = load_progress()
    total   = data["total"]
    done    = data["done"]

    print(f"\n[INFO] สินค้าทั้งหมด: {total}")
    print(f"[INFO] เสร็จแล้ว:    {done}")
    print(f"[INFO] ค้างอยู่:     {total - done}")
    print(f"[INFO] Output dir:   {OUTPUT_DIR}")
    print(f"[INFO] Odoo upload:  {'เปิด' if UPLOAD_TO_ODOO else 'ปิด'}\n")

    # เชื่อม Odoo
    uid, models = (None, None)
    if UPLOAD_TO_ODOO:
        uid, models = connect_odoo()

    # กำหนดโหมดการทำงาน
    mode = args.mode
    if mode is None:
        print("เลือกโหมดการทำงาน (Select Mode):")
        print("1) เจนรูปสินค้าทั้งหมดแบบอัตโนมัติ (Process automatically)")
        print("2) ค้นหาและเจนรูปสินค้าทีละชิ้น (Interactive: search and generate one by one)")
        choice = ""
        while choice not in ["1", "2"]:
            choice = input("เลือกโหมด (1-2) [Default: 2]: ").strip()
            if choice == "":
                choice = "2"
            mode = int(choice)

    if mode == 2:
        run_interactive(data, uid, models)
    else:
        # โหมดอัตโนมัติ
        overwrite = args.overwrite
        process_all = args.all

        if args.mode is None:
            # ถามผู้ใช้หากไม่ได้ระบุผ่าน CLI
            ovw_choice = input("ต้องการเจนรูปทับไฟล์เดิมที่มีอยู่แล้วหรือไม่? (y/n) [Default: n]: ").strip().lower()
            overwrite = (ovw_choice == 'y')

            all_choice = input("ต้องการทำรายการสินค้าใด? (1: เฉพาะที่ค้างอยู่/pending, 2: ทั้งหมด/all) [Default: 1]: ").strip()
            process_all = (all_choice == '2')

        # กรองรายการสินค้าที่จะทำ
        if process_all:
            products_to_process = data["products"]
        else:
            products_to_process = [p for p in data["products"] if p["status"] != "done"]

        print(f"\n[INFO] เริ่มการทำงานแบบอัตโนมัติ...")
        print(f"[INFO] จำนวนสินค้าที่จะดำเนินการ: {len(products_to_process)} รายการ")
        print(f"[INFO] เจนทับไฟล์เดิม: {'ใช่' if overwrite else 'ไม่ใช่'}\n")

        if not products_to_process:
            print("[DONE] ไม่มีสินค้าที่ต้องดำเนินการ!")
            return

        # วนเจนรูปทีละตัว (โหมดอัตโนมัติ)
        for idx, product in enumerate(products_to_process, 1):
            pid   = product["id"]
            pname = product["name"]
            fname = safe_filename(pname, pid)
            fpath = OUTPUT_DIR / fname

            print(f"\n[{idx}/{len(products_to_process)}] ID {pid}: {pname}")
            print(f"  -> file: {fname}")

            # ถ้ามีไฟล์อยู่แล้ว
            if fpath.exists():
                if not overwrite:
                    print("  → ไฟล์มีอยู่แล้ว, ข้ามการ generate")
                else:
                    print("  → ไฟล์มีอยู่แล้ว, กำลังลบเพื่อเจนใหม่ (Overwrite)...")
                    try:
                        fpath.unlink()
                    except Exception as e:
                        print(f"  [ERROR] ไม่สามารถลบไฟล์เดิมได้: {e}")

            if not fpath.exists():
                prompt = get_prompt(pname)
                print(f"  -> prompt: {prompt[:80]}...")

                # retry loop สำหรับ rate limit
                success = False
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        success = generate_image_hf(prompt, fpath, pid)
                        break
                    except RateLimitError as e:
                        if attempt < MAX_RETRIES:
                            print(f"  [RATE LIMIT] รอ {RETRY_WAIT_SECONDS}s แล้ว retry ({attempt}/{MAX_RETRIES})...")
                            time.sleep(RETRY_WAIT_SECONDS)
                        else:
                            print(f"  [FAIL] หมด retry — ข้ามสินค้านี้")
                            mark_status(data, pid, "failed")
                            success = False

                if not success:
                    if idx < len(products_to_process):
                        time.sleep(DELAY_BETWEEN_IMAGES)
                    continue

            print("  [OK] เจนรูปสำเร็จ")

            # Upload เข้า Odoo
            uploaded = False
            if UPLOAD_TO_ODOO and uid and models:
                uploaded = upload_image_to_odoo(uid, models, pid, fpath)
                if uploaded:
                    print("  [OK] upload เข้า Odoo สำเร็จ")
                else:
                    print("  [FAIL] upload ล้มเหลว (รูปยังอยู่ใน product_images/)")

            mark_status(data, pid, "done", str(fname))

            # สรุปความคืบหน้า
            data = load_progress()
            done_now = data["done"]
            print(f"  [Progress] {done_now}/{total} ({done_now/total*100:.1f}%)")

            # Delay ป้องกัน rate limit
            if idx < len(products_to_process):
                time.sleep(DELAY_BETWEEN_IMAGES)

        # สรุปสุดท้าย
        data = load_progress()
        print("\n" + "=" * 60)
        print(f"  DONE! เจนรูปเสร็จสิ้น {data['done']}/{data['total']} สินค้า")
        failed = [p for p in data["products"] if p["status"] == "failed"]
        if failed:
            print(f"  WARNING: ล้มเหลว {len(failed)} สินค้า:")
            for p in failed:
                print(f"     - [{p['id']}] {p['name']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
