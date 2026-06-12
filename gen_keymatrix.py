# -*- coding: utf-8 -*-
"""
gen_keymatrix.py — 由「Culicoides 特徵矩陣demo_filled.xlsx」產生 keymatrix.js

keymatrix.js 供 index.html 的「種級互動檢索（特徵矩陣）」使用。
- interactive 特徵：可點選/輸入作為篩選條件（數值 num / 類別 cat）
- reference 特徵：僅作為候選物種並列比較的參考表

用法： python gen_keymatrix.py
輸出： keymatrix.js（自動產生，勿手動修改）
"""
import json
import re
import openpyxl

XLSX = "Culicoides 特徵矩陣demo_filled.xlsx"
OUT  = "keymatrix.js"

# ── 物種 → 中文名 + 代表標本翅照 ────────────────────────────────
SPECIES_META = {
    "actoni":       ("阿氏庫蠓",  "images/Cer17/0.Cer17 Wings.png"),
    "arakawae":     ("荒川庫蠓",  "images/Cer13/0.Cer13 Wings.png"),
    "homotomus":    ("原野庫蠓",  "images/Cer21/0.Cer21 Wings.png"),
    "jacobsoni":    ("雅氏庫蠓",  "images/Cer44/0.Cer44 Wings.png"),
    "lungchiensis": ("龍溪庫蠓",  "images/Cer27/0.Cer27 Wings.png"),
    "palpifer":     ("帶鬚庫蠓",  None),
    "oxystoma":     ("嗜牛庫蠓",  "images/Cer48/0.Cer48 Wings.png"),
    "sumatrae":     ("蘇島庫蠓",  "images/Cer33/0.win_4x.png"),
    "tainanus":     ("台南庫蠓",  "images/Cer7/0.Cer7 Wings.png"),
}

# 表頭物種欄（C.actoni …）對應的 id
HEADER_TO_ID = {
    "C.actoni": "actoni", "C.arakawae": "arakawae", "C.homotomus": "homotomus",
    "C.jacobsoni": "jacobsoni", "C.lungchiensis": "lungchiensis",
    "C.palpifer": "palpifer", "C.oxystoma": "oxystoma",
    "C.sumatrae": "sumatrae", "C.tainanus": "tainanus",
}

NA = {"", "na", "n/a", "－", "-", "nan", "none"}


def is_na(v):
    return v is None or str(v).strip().lower() in NA


def parse_range(raw):
    """'1.27–1.33' / '13–14 mm' / '5' → (min, max)；無法解析回 None"""
    if is_na(raw):
        return None
    s = str(raw)
    # 抓出所有數字（含小數），用任意非數字當分隔
    nums = re.findall(r"\d+(?:\.\d+)?", s)
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return (min(vals), max(vals))


# ── 互動式特徵定義 ──────────────────────────────────────────────
# 依「中文特徵名稱（標本記錄表第2欄）」比對。
# normalizer(raw) → 類別字串；num 特徵不需 normalizer。
NUM_CHARS = {
    "AR 觸角比":        dict(unit="",   step=0.05),
    "PR 觸鬚比":        dict(unit="",   step=0.1),
    "P/H 喙頭比":       dict(unit="",   step=0.05),
    "大顎齒數":         dict(unit="顆", step=1),
    "下顎齒數":         dict(unit="顆", step=1),
    "翅長":             dict(unit="mm", step=0.05),
    "CR 前緣比":        dict(unit="",   step=0.02),
    "後足脛節鬃數目":   dict(unit="根", step=1),
}


def norm_hairs(raw):
    s = str(raw).strip().lower()
    return "有毛 (pilose)" if "pilose" in s else "無毛 (bare)"


def norm_pit(raw):
    s = str(raw).strip()
    return "無" if s.startswith("無") else "有"


def norm_sperm(raw):
    m = re.search(r"\d+", str(raw))
    return (m.group(0) + " 個") if m else str(raw).strip()


def norm_comb_longest(raw):
    s = str(raw).strip()
    if s == "1":
        return "第 1 根最長"
    if s == "2":
        return "第 2 根最長"
    return s


CAT_CHARS = {
    "眼間毛":          norm_hairs,
    "感覺窩":          norm_pit,
    "精囊數目":        norm_sperm,
    "後足脛節鬃最長":  norm_comb_longest,
}


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["標本記錄表"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    # 物種欄位 index
    sp_cols = {}
    for i, h in enumerate(header):
        if h and str(h).strip() in HEADER_TO_ID:
            sp_cols[HEADER_TO_ID[str(h).strip()]] = i

    species_ids = [HEADER_TO_ID[str(header[i]).strip()]
                   for i in sorted(sp_cols.values())]

    interactive, reference = [], []

    for r in rows[1:]:
        if not r or all(c is None for c in r):
            continue
        region = (r[0] or "").strip()
        name   = (r[1] or "").strip()
        nameEn = (r[2] or "").strip()
        ref    = (r[3] or "").strip()
        if not name:
            continue

        raw_vals = {sid: (None if is_na(r[ci]) else str(r[ci]).strip())
                    for sid, ci in sp_cols.items()}

        if name in NUM_CHARS:
            cfg = NUM_CHARS[name]
            vals = {}
            spread = []
            for sid in species_ids:
                rng = parse_range(raw_vals[sid])
                if rng:
                    vals[sid] = {"min": rng[0], "max": rng[1], "raw": raw_vals[sid]}
                    spread += [rng[0], rng[1]]
                else:
                    vals[sid] = {"min": None, "max": None, "raw": raw_vals[sid]}
            lo, hi = (min(spread), max(spread)) if spread else (0, 1)
            pad = max((hi - lo) * 0.04, cfg["step"] * 0.5)
            interactive.append({
                "id": "n_" + str(len(interactive)),
                "region": region, "name": name.strip(), "nameEn": nameEn,
                "type": "num", "unit": cfg["unit"], "note": ref,
                "min": round(lo, 4), "max": round(hi, 4),
                "pad": round(pad, 4), "values": vals,
            })

        elif name in CAT_CHARS:
            norm = CAT_CHARS[name]
            vals, states = {}, []
            for sid in species_ids:
                if raw_vals[sid] is None:
                    vals[sid] = {"state": None, "raw": None}
                else:
                    st = norm(raw_vals[sid])
                    vals[sid] = {"state": st, "raw": raw_vals[sid]}
                    if st not in states:
                        states.append(st)
            states.sort()
            interactive.append({
                "id": "c_" + str(len(interactive)),
                "region": region, "name": name, "nameEn": nameEn,
                "type": "cat", "note": ref,
                "states": states, "values": vals,
            })

        else:
            reference.append({
                "region": region, "name": name, "nameEn": nameEn,
                "values": raw_vals,
            })

    species = [{
        "id": sid,
        "sci": "Culicoides " + sid,
        "zh": SPECIES_META[sid][0],
        "photo": SPECIES_META[sid][1],
    } for sid in species_ids]

    data = {"species": species, "characters": interactive, "reference": reference}

    body = (
        "// Auto-generated by gen_keymatrix.py - do not edit manually\n"
        "window.KEY_MATRIX = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)

    print(f"{OUT} written: {len(species)} species, "
          f"{len(interactive)} interactive chars, {len(reference)} reference chars")


if __name__ == "__main__":
    main()
