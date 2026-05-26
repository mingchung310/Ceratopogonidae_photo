"""
RAW 圖片處理流程
================
資料夾結構：
    RAW image/<標本ID>/photo.jpg   →   images/<標本ID>/photo.png

步驟：
  1. 掃描 RAW image/ 下每個子資料夾（子資料夾名稱 = 標本編號，如 Cer7）
  2. 對每張圖片：
       a. 計算感知雜湊，與 images/ 中所有圖片比對（重複則跳過）
       b. 壓縮成 PNG，檔案大小 ≤ 600 KB
       c. 存到 images/<標本ID>/
  3. 自動執行 build.ps1 更新 manifest.json 與 data.js

用法：
  python process_raw.py           正常執行
  python process_raw.py --dry-run 預覽（不寫入檔案）
"""

import pathlib, io, sys, subprocess
from PIL import Image

# ── 設定 ────────────────────────────────────────────────
BASE     = pathlib.Path(__file__).parent
RAW_DIR  = BASE / "RAW image"
IMG_DIR  = BASE / "images"
BUILD_PS = BASE / "build.ps1"

SKIP_FILES = {"IMG_7000.JPG"}        # 比例尺參考圖，跳過
MAX_BYTES  = 600 * 1024              # 600 KB
RAW_EXTS   = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

DRY_RUN = "--dry-run" in sys.argv

# ── 感知雜湊（64-bit average hash）─────────────────────
def phash(img: Image.Image) -> int:
    small = img.convert("L").resize((8, 8), Image.LANCZOS)
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    return int("".join("1" if p > avg else "0" for p in pixels), 2)

def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")

def load_existing_hashes() -> dict:
    """讀取 images/ 中所有 PNG 的感知雜湊"""
    hashes = {}
    for p in IMG_DIR.rglob("*.png"):
        try:
            hashes[p] = phash(Image.open(p))
        except Exception:
            pass
    return hashes

# ── PNG 壓縮，確保 ≤ 600 KB ─────────────────────────
def compress_to_limit(img: Image.Image) -> bytes:
    img = img.convert("RGB")
    w, h = img.size
    while True:
        buf = io.BytesIO()
        try:
            q = img.quantize(256, method=Image.Quantize.FASTOCTREE)
            q.save(buf, "PNG", optimize=True)
        except Exception:
            img.save(buf, "PNG", optimize=True)
        if buf.tell() <= MAX_BYTES or w <= 800:
            return buf.getvalue()
        # 縮小 10%
        w, h = round(w * 0.9), round(h * 0.9)
        img = img.resize((w, h), Image.LANCZOS)

# ══════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════

print("=" * 56)
print("  RAW 圖片處理流程" + ("  [DRY-RUN 預覽模式]" if DRY_RUN else ""))
print("=" * 56)

# 掃描既有圖片雜湊
print("\n掃描 images/ 既有圖片雜湊值…")
existing_hashes = load_existing_hashes()
print(f"  找到 {len(existing_hashes)} 張既有圖片")

# 收集 RAW 子資料夾中的圖片
raw_images = []
for folder in sorted(RAW_DIR.iterdir()):
    if not folder.is_dir() or folder.name == "output":
        continue
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in RAW_EXTS and p.name not in SKIP_FILES:
            raw_images.append((folder.name, p))

if not raw_images:
    print("\n⚠ 沒有找到要處理的圖片。")
    print(f"  請將圖片放在 RAW image/<標本ID>/ 子資料夾中，例如：")
    print(f"  RAW image\\Cer7\\photo.jpg")
    sys.exit(0)

print(f"\n找到 {len(raw_images)} 張 RAW 圖片，開始處理…\n")

ok_count = dup_count = skip_count = err_count = 0

for specimen_id, raw_path in raw_images:
    out_folder = IMG_DIR / specimen_id
    out_name   = raw_path.stem + ".png"
    out_path   = out_folder / out_name
    tag        = f"{specimen_id}/{out_name}"

    # 已存在則跳過
    if out_path.exists():
        print(f"  SKIP  {tag}  (已存在)")
        skip_count += 1
        continue

    # 讀取圖片
    try:
        img = Image.open(raw_path)
        new_h = phash(img)
    except Exception as e:
        print(f"  ERR   {raw_path.name}: {e}")
        err_count += 1
        continue

    # 重複偵測
    dup_path = None
    for ex_path, ex_h in existing_hashes.items():
        if hamming(new_h, ex_h) < 5:
            dup_path = ex_path
            break
    if dup_path:
        print(f"  DUP   {tag}")
        print(f"        ≈ {dup_path.relative_to(BASE)}")
        dup_count += 1
        continue

    # 壓縮與儲存
    if not DRY_RUN:
        try:
            out_folder.mkdir(parents=True, exist_ok=True)
            data = compress_to_limit(img)
            out_path.write_bytes(data)
            existing_hashes[out_path] = new_h
            size_kb = len(data) / 1024
            print(f"  OK    {tag}  ({size_kb:.0f} KB)")
        except Exception as e:
            print(f"  ERR   {tag}: {e}")
            err_count += 1
            continue
    else:
        orig_kb = raw_path.stat().st_size / 1024
        print(f"  [DRY] {tag}  (原始 {orig_kb:.0f} KB)")
    ok_count += 1

# 結果摘要
print()
print("─" * 56)
print(f"  新增 {ok_count}  |  重複跳過 {dup_count}  |  已存在跳過 {skip_count}  |  錯誤 {err_count}")
print("─" * 56)

# 自動更新 manifest.json 與 data.js
if not DRY_RUN and ok_count > 0:
    print("\n執行 build.ps1 更新 manifest.json 與 data.js…")
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BUILD_PS)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
        print("\n完成！請執行 git add / commit / push 推上 GitHub。")
    else:
        print(f"  build.ps1 失敗：{result.stderr}")
elif DRY_RUN:
    print("\n[DRY-RUN] 未寫入任何檔案。移除 --dry-run 參數後重新執行。")
else:
    print("\n沒有新圖片需要處理。")
