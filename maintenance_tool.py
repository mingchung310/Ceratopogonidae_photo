#!/usr/bin/env python3
"""
蠓科標本影像維護工具
  - 同步 Google Sheets / 本地 CSV
  - 選取資料夾新增圖片（重複偵測、壓縮 ≤200KB）
  - 自動更新 manifest.json + data.js
  - 上傳至 GitHub
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pathlib, io, subprocess, threading, json, webbrowser
from PIL import Image

BASE      = pathlib.Path(__file__).parent
IMG_DIR   = BASE / "images"
BUILD_PS  = BASE / "build.ps1"
MAX_BYTES = 200 * 1024
IMG_EXTS  = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# ── 影像工具 ─────────────────────────────────────────────────────────────────

def phash(img: Image.Image) -> int:
    small  = img.convert("L").resize((8, 8), Image.LANCZOS)
    pixels = list(small.getdata())
    avg    = sum(pixels) / len(pixels)
    return int("".join("1" if p > avg else "0" for p in pixels), 2)

def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")

def existing_hashes(spec_id: str) -> dict:
    folder = IMG_DIR / spec_id
    hashes: dict = {}
    if folder.exists():
        for p in sorted(folder.glob("*.png")):
            try:
                hashes[p] = phash(Image.open(p))
            except Exception:
                pass
    return hashes

def compress(img: Image.Image) -> bytes:
    img  = img.convert("RGB")
    w, h = img.size
    buf  = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    if buf.tell() <= MAX_BYTES:
        return buf.getvalue()
    while True:
        buf = io.BytesIO()
        try:
            q = img.quantize(256, method=Image.Quantize.FASTOCTREE)
            q.save(buf, "PNG", optimize=True)
        except Exception:
            img.save(buf, "PNG", optimize=True)
        if buf.tell() <= MAX_BYTES or w <= 800:
            return buf.getvalue()
        w, h = round(w * 0.9), round(h * 0.9)
        img  = img.resize((w, h), Image.LANCZOS)

# ── GUI ──────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("蠓科標本影像維護工具")
        self.minsize(660, 600)
        self._selected_files: list[pathlib.Path] = []
        self._build_ui()

    # ── 版面配置 ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = dict(padx=10, pady=5)

        # ── 區塊 1：資料同步 ──────────────────────────────────────────────
        sync = ttk.LabelFrame(self, text=" 資料同步 ", padding=8)
        sync.pack(fill="x", **PAD)

        ttk.Button(sync, text="同步 Google Sheets", width=20,
                   command=lambda: self._bg(self._sync_sheets)
                   ).pack(side="left", padx=4)
        ttk.Button(sync, text="使用本地 CSV", width=14,
                   command=lambda: self._bg(self._sync_local)
                   ).pack(side="left", padx=4)
        ttk.Button(sync, text="推送資料更新", width=14,
                   command=lambda: self._bg(self._push_data)
                   ).pack(side="left", padx=4)
        ttk.Button(sync, text="預覽網站", width=10,
                   command=self._preview
                   ).pack(side="right", padx=4)

        # ── 區塊 2：新增圖片 ──────────────────────────────────────────────
        img_frame = ttk.LabelFrame(self, text=" 新增圖片 ", padding=8)
        img_frame.pack(fill="both", expand=True, **PAD)

        row1 = ttk.Frame(img_frame)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="標本 ID：").pack(side="left")
        self.spec_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.spec_var, width=10).pack(side="left", padx=4)
        ttk.Label(row1, text="（如 Cer55）", foreground="gray").pack(side="left")
        ttk.Button(row1, text="選取圖片資料夾", command=self._pick_folder
                   ).pack(side="right")

        self.folder_lbl = ttk.Label(img_frame, text="尚未選取資料夾", foreground="gray")
        self.folder_lbl.pack(anchor="w", pady=2)

        list_row = ttk.Frame(img_frame)
        list_row.pack(fill="both", expand=True, pady=4)
        self.listbox = tk.Listbox(list_row, height=7, selectmode="browse")
        sb = ttk.Scrollbar(list_row, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        btn_row = ttk.Frame(img_frame)
        btn_row.pack(fill="x", pady=4)
        self.proc_btn = ttk.Button(btn_row, text="壓縮並加入 images/",
                                   state="disabled",
                                   command=lambda: self._bg(self._process_images))
        self.proc_btn.pack(side="left", padx=4)
        self.push_btn = ttk.Button(btn_row, text="上傳至 GitHub",
                                   state="disabled",
                                   command=lambda: self._bg(self._push_images))
        self.push_btn.pack(side="left", padx=4)

        # ── 區塊 3：執行日誌 ──────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self, text=" 執行日誌 ", padding=6)
        log_frame.pack(fill="both", expand=True, **PAD)
        self.log = scrolledtext.ScrolledText(
            log_frame, height=9, state="disabled",
            font=("Consolas", 9), wrap="word"
        )
        self.log.pack(fill="both", expand=True)
        ttk.Button(self, text="清除日誌", command=self._clear_log
                   ).pack(anchor="e", padx=10, pady=2)

    # ── 工具方法 ─────────────────────────────────────────────────────────────

    def _bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _log(self, msg: str):
        def _do():
            self.log.config(state="normal")
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _set_btn(self, btn, state):
        self.after(0, lambda: btn.config(state=state))

    def _run_build_ps(self) -> bool:
        r = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BUILD_PS)],
            capture_output=True, text=True, cwd=str(BASE)
        )
        for line in r.stdout.strip().splitlines():
            self._log(f"  {line}")
        if r.returncode != 0:
            self._log(f"  [錯誤] {r.stderr.strip()}")
        return r.returncode == 0

    def _run_git(self, *args) -> bool:
        r = subprocess.run(
            ["git"] + list(args), capture_output=True, text=True, cwd=str(BASE)
        )
        for line in (r.stdout + r.stderr).strip().splitlines():
            self._log(f"  {line}")
        return r.returncode == 0

    # ── 資料同步 ─────────────────────────────────────────────────────────────

    def _sync_sheets(self):
        self._log("\n▶ 同步 Google Sheets …")
        ok = self._run_build_ps()
        self._log("✓ 同步完成" if ok else "✗ 同步失敗，請確認網路連線")

    def _sync_local(self):
        self._log("\n▶ 使用本地 CSV 更新 data.js …")
        csv_list = list(BASE.glob("*.csv"))
        if not csv_list:
            self._log("  [錯誤] 找不到 .csv 檔案")
            return
        csv_path = csv_list[0]
        self._log(f"  來源：{csv_path.name}")
        try:
            csv_raw = csv_path.read_text(encoding="utf-8-sig")
            mf_path  = BASE / "manifest.json"
            manifest = json.loads(mf_path.read_text(encoding="utf-8")) if mf_path.exists() else {}
            data_js  = (
                "// Auto-generated by build.ps1 - do not edit manually\n"
                f"window.EMBEDDED_DATA = {{"
                f" csv: {json.dumps(csv_raw)},"
                f" manifest: {json.dumps(manifest)} }};"
            )
            (BASE / "data.js").write_text(data_js, encoding="utf-8")
            self._log("✓ data.js 已更新（離線模式）")
        except Exception as e:
            self._log(f"  [錯誤] {e}")

    def _push_data(self):
        self._log("\n▶ 推送資料更新至 GitHub …")
        self._run_git("add", "data.js", "manifest.json")
        committed = self._run_git("commit", "-m", "更新資料")
        if not committed:
            self._log("  （沒有需要 commit 的變更）")
            return
        ok = self._run_git("push")
        self._log("✓ 推送完成" if ok else "✗ push 失敗，請確認 git 設定與網路連線")

    def _preview(self):
        webbrowser.open((BASE / "index.html").as_uri())
        self._log("▶ 開啟 index.html")

    # ── 新增圖片 ─────────────────────────────────────────────────────────────

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="選取包含照片的資料夾")
        if not folder:
            return
        folder = pathlib.Path(folder)
        files  = sorted(f for f in folder.iterdir() if f.suffix.lower() in IMG_EXTS)
        if not files:
            messagebox.showwarning("無圖片", "資料夾中找不到 JPG / PNG / TIF 圖片")
            return

        self._selected_files = files

        # 若資料夾名稱像是標本 ID（例如 Cer55），自動填入
        if folder.name.startswith("Cer") and not self.spec_var.get():
            self.spec_var.set(folder.name)

        self.folder_lbl.config(
            text=f"{folder}  （{len(files)} 張）", foreground="black"
        )
        self.listbox.delete(0, "end")
        for f in files:
            self.listbox.insert("end", f.name)
        self._set_btn(self.proc_btn, "normal")
        self._log(f"▶ 已選取：{folder}（{len(files)} 張圖片）")

    def _process_images(self):
        spec_id = self.spec_var.get().strip()
        if not spec_id:
            self.after(0, lambda: messagebox.showerror(
                "缺少標本 ID", "請在上方輸入標本 ID（例如 Cer55）"))
            return
        if not self._selected_files:
            return

        self._log(f"\n── 處理標本 {spec_id} {'─'*30}")
        self._set_btn(self.proc_btn, "disabled")

        hashes     = existing_hashes(spec_id)
        out_folder = IMG_DIR / spec_id
        ok = dup = skip = err = 0

        for raw in self._selected_files:
            out_name = raw.stem + ".png"
            out_path = out_folder / out_name
            tag      = f"{spec_id}/{out_name}"

            # 已存在 → 跳過
            if out_path.exists():
                self._log(f"  SKIP  {tag}  （已存在）")
                skip += 1
                continue

            # 讀取圖片
            try:
                img = Image.open(raw)
                h   = phash(img)
            except Exception as e:
                self._log(f"  ERR   {raw.name}: {e}")
                err += 1
                continue

            # 重複偵測
            dup_of = next((p for p, dh in hashes.items() if hamming(h, dh) < 5), None)
            if dup_of:
                self._log(f"  DUP   {tag}  （≈ {dup_of.name}）")
                dup += 1
                continue

            # 壓縮並儲存
            try:
                out_folder.mkdir(parents=True, exist_ok=True)
                data = compress(img)
                out_path.write_bytes(data)
                hashes[out_path] = h
                self._log(f"  OK    {tag}  （{len(data)//1024} KB）")
                ok += 1
            except Exception as e:
                self._log(f"  ERR   {tag}: {e}")
                err += 1

        self._log(f"\n  新增 {ok}  |  重複跳過 {dup}  |  已存在跳過 {skip}  |  錯誤 {err}")

        if ok > 0:
            self._log("\n  更新 manifest.json 與 data.js …")
            self._run_build_ps()
            self._log("✓ 完成！請點「上傳至 GitHub」推送。")
            self._set_btn(self.push_btn, "normal")

        self._set_btn(self.proc_btn, "normal")

    def _push_images(self):
        spec_id = self.spec_var.get().strip() or "update"
        self._log(f"\n── 上傳至 GitHub（{spec_id}）{'─'*25}")
        self._set_btn(self.push_btn, "disabled")

        self._run_git("add", "images/", "manifest.json", "data.js")
        committed = self._run_git("commit", "-m", f"新增標本 {spec_id}")
        if not committed:
            self._log("  [提示] commit 失敗（可能沒有新增內容）")
            self._set_btn(self.push_btn, "normal")
            return

        ok = self._run_git("push")
        if ok:
            self._log("✓ 已上傳！網站約 1～2 分鐘後更新。")
        else:
            self._log("✗ push 失敗，請確認 git 設定與網路連線")
            self._set_btn(self.push_btn, "normal")


if __name__ == "__main__":
    app = App()
    app.mainloop()
