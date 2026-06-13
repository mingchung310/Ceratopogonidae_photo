#!/usr/bin/env python3
"""
蠓科標本影像維護工具
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pathlib, io, subprocess, threading, json, sys, datetime
from PIL import Image

BASE         = pathlib.Path(__file__).parent
IMG_DIR      = BASE / "images"
BUILD_PS     = BASE / "build.ps1"
GEN_KEY      = BASE / "gen_keymatrix.py"
MATRIX_XLSX  = BASE / "Culicoides 特徵矩陣.xlsx"
KEYMATRIX_JS = BASE / "keymatrix.js"
MAX_BYTES    = 200 * 1024
IMG_EXTS     = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

# ── 影像工具 ──────────────────────────────────────────────────────────────────

def compress(img):
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

def rebuild_manifest():
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    manifest = {}
    if IMG_DIR.exists():
        for folder in sorted(IMG_DIR.iterdir()):
            if not folder.is_dir():
                continue
            files = [f"images/{folder.name}/{p.name}"
                     for p in sorted(folder.iterdir())
                     if p.suffix.lower() in exts]
            if files:
                manifest[folder.name] = files
    (BASE / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=4), encoding="utf-8"
    )
    return len(manifest)


# ── 檔名衝突對話框 ────────────────────────────────────────────────────────────

class ConflictDialog(tk.Toplevel):
    """
    檔名衝突時彈出，讓使用者選擇處置方式。
    result: ('skip'|'skip_all'|'overwrite'|'overwrite_all'|'rename', new_filename_or_None)
    """
    def __init__(self, parent, spec_id: str, filename: str):
        super().__init__(parent)
        self.result = ('skip', None)
        self.title("檔名衝突")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        ttk.Label(self, text="目標檔案已存在：",
                  font=("", 10, "bold")).pack(padx=24, pady=(18, 4))
        ttk.Label(self, text=f"{spec_id}/{filename}",
                  foreground="#c9a84c").pack(padx=24, pady=(0, 14))

        # ── 改名區 ──────────────────────────────────────────────────────
        rf = ttk.LabelFrame(self, text=" 改名後上傳 ", padding=10)
        rf.pack(fill="x", padx=24, pady=(0, 10))
        ttk.Label(rf, text="新檔名（不含 .png）：").pack(anchor="w")
        self._new_name = tk.StringVar(value=pathlib.Path(filename).stem)
        entry = ttk.Entry(rf, textvariable=self._new_name, width=30)
        entry.pack(fill="x", pady=(4, 6))
        entry.select_range(0, "end")
        entry.focus_set()
        ttk.Button(rf, text="確認改名", command=self._rename).pack(anchor="e")

        # ── 其他選項 ─────────────────────────────────────────────────────
        bf = ttk.Frame(self)
        bf.pack(padx=24, pady=(0, 18))
        ttk.Button(bf, text="覆蓋",      width=10, command=self._overwrite    ).grid(row=0, column=0, padx=4, pady=3)
        ttk.Button(bf, text="覆蓋全部",  width=10, command=self._overwrite_all).grid(row=0, column=1, padx=4, pady=3)
        ttk.Button(bf, text="略過",      width=10, command=self._skip         ).grid(row=1, column=0, padx=4, pady=3)
        ttk.Button(bf, text="略過全部",  width=10, command=self._skip_all     ).grid(row=1, column=1, padx=4, pady=3)

        self.protocol("WM_DELETE_WINDOW", self._skip)
        self.wait_window()

    def _rename(self):
        stem = self._new_name.get().strip()
        if stem:
            self.result = ('rename', stem + '.png')
            self.destroy()

    def _overwrite(self):
        self.result = ('overwrite', None); self.destroy()

    def _overwrite_all(self):
        self.result = ('overwrite_all', None); self.destroy()

    def _skip(self):
        self.result = ('skip', None); self.destroy()

    def _skip_all(self):
        self.result = ('skip_all', None); self.destroy()


# ── GUI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("蠓科標本影像維護工具")
        self.minsize(560, 540)
        self._files:   list[pathlib.Path] = []   # 單一資料夾模式
        self._batches: dict[str, list]    = {}   # 批次模式 {spec_id: [files]}
        self._build_ui()

    def _build_ui(self):
        P = dict(padx=12, pady=6)

        # ── 1. Google Sheets 同步 ────────────────────────────────────────
        f1 = ttk.LabelFrame(self, text=" 1. 同步 Google Sheets ", padding=10)
        f1.pack(fill="x", **P)
        ttk.Label(f1, text="下載最新資料，更新本機離線版 index.html 的顯示內容。",
                  foreground="gray").pack(anchor="w")
        ttk.Button(f1, text="立即同步", width=14,
                   command=lambda: self._bg(self._sync_sheets)
                   ).pack(anchor="w", pady=(8, 0))

        # ── 1b. 同步檢索表特徵矩陣 ────────────────────────────────────────
        fk = ttk.LabelFrame(self, text=" 檢索表：同步特徵矩陣 ", padding=10)
        fk.pack(fill="x", **P)
        ttk.Label(fk,
                  text="改完「Culicoides 特徵矩陣.xlsx」後按此：重建 keymatrix.js\n"
                       "並推送到 GitHub，線上 key.html 的種級矩陣檢索即會更新。",
                  foreground="gray", justify="left").pack(anchor="w")
        ttk.Button(fk, text="重建並推送", width=14,
                   command=lambda: self._bg(self._sync_keymatrix)
                   ).pack(anchor="w", pady=(8, 0))

        # ── 2. 壓縮照片 ──────────────────────────────────────────────────
        f2 = ttk.LabelFrame(self, text=" 2. 壓縮照片並放入 images/ ", padding=10)
        f2.pack(fill="both", expand=True, **P)

        top = ttk.Frame(f2)
        top.pack(fill="x")
        ttk.Label(top, text="目標資料夾：").pack(side="left")
        self.spec_var = tk.StringVar()
        self.spec_entry = ttk.Entry(top, textvariable=self.spec_var, width=10)
        self.spec_entry.pack(side="left", padx=6)
        ttk.Label(top, text="（如 Cer55）", foreground="gray").pack(side="left")
        ttk.Button(top, text="批次（上層資料夾）",
                   command=self._pick_parent).pack(side="right", padx=(4, 0))
        ttk.Button(top, text="選取照片資料夾",
                   command=self._pick_folder).pack(side="right")

        self.folder_lbl = ttk.Label(f2, text="尚未選取", foreground="gray")
        self.folder_lbl.pack(anchor="w", pady=4)

        lf = ttk.Frame(f2)
        lf.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(lf, height=6, activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.compress_btn = ttk.Button(
            f2, text="壓縮並放入 images/", state="disabled",
            command=lambda: self._bg(self._compress))
        self.compress_btn.pack(anchor="w", pady=(8, 0))

        # ── 3. 同步到 GitHub ─────────────────────────────────────────────
        f3 = ttk.LabelFrame(self, text=" 3. 同步 images 到 GitHub ", padding=10)
        f3.pack(fill="x", **P)
        ttk.Label(f3, text="將 images/ 的新增與刪除同步推送到 GitHub。",
                  foreground="gray").pack(anchor="w")
        ttk.Button(f3, text="同步到 GitHub", width=14,
                   command=lambda: self._bg(self._sync_github)
                   ).pack(anchor="w", pady=(8, 0))

        # ── 匯出可攜版 ───────────────────────────────────────────────────
        fe = ttk.LabelFrame(self, text=" 匯出可攜版（搬到離線電腦用）", padding=10)
        fe.pack(fill="x", **P)
        ttk.Label(fe,
                  text="把離線運作所需的檔案整包複製到指定位置（例如隨身碟）。\n"
                       "自動排除 RAW image\\ 等大型/暫存檔，含網站、維護工具與離線備援 CSV。",
                  foreground="gray", justify="left").pack(anchor="w")
        ttk.Button(fe, text="匯出可攜版…", width=14,
                   command=self._export_portable
                   ).pack(anchor="w", pady=(8, 0))

        # ── 進度 ─────────────────────────────────────────────────────────
        pf = ttk.Frame(self)
        pf.pack(fill="x", padx=12, pady=(0, 2))
        self.status_lbl = ttk.Label(pf, text="待命", foreground="gray", font=("", 9))
        self.status_lbl.pack(anchor="w")
        self.progress = ttk.Progressbar(pf, mode="indeterminate")
        self.progress.pack(fill="x", pady=(2, 0))

        # ── 日誌 ─────────────────────────────────────────────────────────
        lf2 = ttk.LabelFrame(self, text=" 執行日誌 ", padding=6)
        lf2.pack(fill="both", expand=True, **P)
        self.log = scrolledtext.ScrolledText(
            lf2, height=7, state="disabled", font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True)
        ttk.Button(self, text="清除日誌", command=self._clear
                   ).pack(anchor="e", padx=12, pady=2)

    # ── 工具 ──────────────────────────────────────────────────────────────────

    def _bg(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _log(self, msg):
        def _():
            self.log.config(state="normal")
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, _)

    def _clear(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _set_state(self, btn, state):
        self.after(0, lambda: btn.config(state=state))

    def _busy(self, msg: str):
        """開始不定進度（跑馬燈）"""
        def _():
            self.status_lbl.config(text=msg, foreground="#c9a84c")
            self.progress.config(mode="indeterminate")
            self.progress.start(12)
        self.after(0, _)

    def _set_progress(self, value: int, total: int, msg: str = ""):
        """切換為確定進度並更新值"""
        pct = round(value / total * 100) if total else 0
        def _():
            self.progress.stop()
            self.progress.config(mode="determinate", maximum=total, value=value)
            label = f"{msg}  {pct}%" if msg else f"{value}/{total}  {pct}%"
            self.status_lbl.config(text=label, foreground="#c9a84c")
        self.after(0, _)

    def _idle(self, msg: str = "待命"):
        """操作結束，重置進度條"""
        def _():
            self.progress.stop()
            self.progress.config(mode="determinate", value=0)
            self.status_lbl.config(text=msg, foreground="gray")
        self.after(0, _)

    def _run_ps(self) -> bool:
        r = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BUILD_PS)],
            capture_output=True, text=True, cwd=str(BASE))
        for line in r.stdout.strip().splitlines():
            self._log(f"  {line}")
        if r.returncode != 0:
            self._log(f"  [錯誤] {r.stderr.strip()}")
        return r.returncode == 0

    def _git(self, *args) -> bool:
        r = subprocess.run(["git"] + list(args), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           cwd=str(BASE))
        out = (r.stdout or "") + (r.stderr or "")
        for line in out.strip().splitlines():
            self._log(f"  {line}")
        return r.returncode == 0

    # ── 1. Google Sheets 同步 ────────────────────────────────────────────────

    def _sync_sheets(self):
        self._busy("同步 Google Sheets 中…")
        self._log("\n▶ 同步 Google Sheets …")
        ok = self._run_ps()
        self._log("✓ 完成，本機離線版已更新" if ok else "✗ 失敗，請確認網路連線")
        self._idle("✓ 同步完成" if ok else "✗ 同步失敗")

    # ── 1b. 同步檢索表特徵矩陣（xlsx → keymatrix.js → GitHub）─────────────────

    def _sync_keymatrix(self):
        result = ["待命"]   # finally 用
        try:
            self._busy("重建 keymatrix.js 中…")
            self._log("\n▶ 同步檢索表特徵矩陣 …")

            if not MATRIX_XLSX.exists():
                self._log(f"  [錯誤] 找不到 {MATRIX_XLSX.name}")
                result[0] = "✗ 找不到 xlsx"
                return

            # 1) 由 xlsx 重建 keymatrix.js
            r = subprocess.run([sys.executable, str(GEN_KEY)],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace", cwd=str(BASE))
            for line in (r.stdout or "").strip().splitlines():
                self._log(f"  {line}")
            if r.returncode != 0:
                self._log(f"  [錯誤] {(r.stderr or '').strip()}")
                self._log("  （xlsx 結構可能有誤，已中止，未推送）")
                result[0] = "✗ 產生失敗"
                return

            # 2) 暫存 keymatrix.js 與 xlsx
            self._busy("提交並推送到 GitHub 中…")
            self._git("add", str(KEYMATRIX_JS.name), str(MATRIX_XLSX.name))

            has_changes = subprocess.run(
                ["git", "diff", "--cached", "--quiet"], cwd=str(BASE)
            ).returncode != 0
            if not has_changes:
                self._log("  沒有需要同步的變更（內容與線上相同）")
                result[0] = "無需同步"
                return

            # 3) commit + push
            if not self._git("commit", "-m", "同步檢索表特徵矩陣 → keymatrix.js"):
                result[0] = "✗ commit 失敗"
                return
            ok = self._git("push")
            self._log("✓ 已推送，線上 key.html 的種級矩陣檢索將更新"
                      if ok else "✗ push 失敗，請確認網路或權限")
            result[0] = "✓ 檢索表已同步" if ok else "✗ push 失敗"

        except Exception as e:
            self._log(f"  [未預期錯誤] {e}")
            result[0] = "✗ 發生錯誤"
        finally:
            self._idle(result[0])

    # ── 2. 壓縮照片 ──────────────────────────────────────────────────────────

    def _pick_folder(self):
        """單一資料夾模式"""
        folder = filedialog.askdirectory(title="選取包含照片的資料夾")
        if not folder:
            return
        folder = pathlib.Path(folder)
        files  = sorted(f for f in folder.iterdir() if f.suffix.lower() in IMG_EXTS)
        if not files:
            messagebox.showwarning("無圖片", "資料夾中找不到 JPG / PNG / TIF 圖片")
            return
        self._files   = files
        self._batches = {}
        if not self.spec_var.get():
            self.spec_var.set(folder.name)
        self.spec_entry.config(state="normal")
        self.folder_lbl.config(
            text=f"{folder.name}/  （{len(files)} 張）", foreground="black")
        self.listbox.delete(0, "end")
        for f in files:
            self.listbox.insert("end", f.name)
        self._set_state(self.compress_btn, "normal")
        self._log(f"▶ 已選取：{folder}（{len(files)} 張）")

    def _pick_parent(self):
        """批次模式：選上層資料夾，每個子資料夾視為一個標本"""
        parent = filedialog.askdirectory(title="選取上層資料夾（每個子資料夾為一個標本）")
        if not parent:
            return
        parent = pathlib.Path(parent)
        batches = {}
        for sub in sorted(parent.iterdir()):
            if not sub.is_dir() or sub.name.lower() == "output":
                continue
            try:
                files = sorted(f for f in sub.iterdir() if f.suffix.lower() in IMG_EXTS)
            except PermissionError:
                continue
            if files:
                batches[sub.name] = files

        if not batches:
            messagebox.showwarning("無子資料夾", "所選資料夾中找不到含圖片的子資料夾")
            return

        self._batches = batches
        self._files   = []
        self.spec_var.set("")
        self.spec_entry.config(state="disabled")   # 批次模式不需輸入 ID

        total = sum(len(v) for v in batches.values())
        self.folder_lbl.config(
            text=f"批次：{parent.name}/  （{len(batches)} 個標本，共 {total} 張）",
            foreground="black")
        self.listbox.delete(0, "end")
        for spec_id, files in batches.items():
            self.listbox.insert("end", f"── {spec_id}/ ──")
            for f in files:
                self.listbox.insert("end", f"   {f.name}")
        self._set_state(self.compress_btn, "normal")
        self._log(f"▶ 批次選取：{parent}（{len(batches)} 個標本，共 {total} 張）")

    # ── 衝突詢問（在主執行緒顯示對話框）────────────────────────────────────────

    def _ask_conflict(self, spec_id: str, filename: str):
        """從背景執行緒呼叫，阻塞直到使用者在對話框做出選擇。"""
        result = [('skip', None)]
        event  = threading.Event()

        def show():
            dlg = ConflictDialog(self, spec_id, filename)
            result[0] = dlg.result
            event.set()

        self.after(0, show)
        event.wait()
        return result[0]

    # ── 壓縮核心（單一標本）────────────────────────────────────────────────────

    def _do_compress_one(self, spec_id: str, files: list, on_progress=None) -> int:
        """壓縮並放入 images/<spec_id>/，回傳新增數量。
        以檔名判斷重複；衝突時彈出對話框讓使用者決定。"""
        self._log(f"\n  ── {spec_id} ──")
        out_folder = IMG_DIR / spec_id
        ok = skip = err = 0

        for i, raw in enumerate(files):
            if on_progress:
                on_progress(spec_id, i)
            out_name = raw.stem + ".png"
            out_path = out_folder / out_name
            tag      = f"{spec_id}/{out_name}"

            # ── 檔名衝突：詢問使用者 ────────────────────────────────────
            if out_path.exists():
                if self._conflict_all == 'skip_all':
                    self._log(f"  SKIP  {tag}（略過全部）")
                    skip += 1
                    continue
                elif self._conflict_all == 'overwrite_all':
                    self._log(f"  OVR   {tag}（覆蓋）")
                    # fall through to compress
                else:
                    action, new_name = self._ask_conflict(spec_id, out_name)
                    if action == 'skip':
                        self._log(f"  SKIP  {tag}（略過）")
                        skip += 1
                        continue
                    elif action == 'skip_all':
                        self._log(f"  SKIP  {tag}（略過）")
                        skip += 1
                        self._conflict_all = 'skip_all'
                        continue
                    elif action == 'rename':
                        out_name = new_name
                        out_path = out_folder / out_name
                        tag      = f"{spec_id}/{out_name}"
                    elif action == 'overwrite':
                        self._log(f"  OVR   {tag}（覆蓋）")
                    elif action == 'overwrite_all':
                        self._log(f"  OVR   {tag}（覆蓋）")
                        self._conflict_all = 'overwrite_all'

            # ── 壓縮並寫入 ──────────────────────────────────────────────
            try:
                img = Image.open(raw)
            except Exception as e:
                self._log(f"  ERR   {raw.name}: {e}")
                err += 1
                continue

            try:
                out_folder.mkdir(parents=True, exist_ok=True)
                data = compress(img)
                out_path.write_bytes(data)
                self._log(f"  OK    {tag}（{len(data)//1024} KB）")
                ok += 1
            except Exception as e:
                self._log(f"  ERR   {tag}: {e}")
                err += 1

        self._log(f"  新增 {ok}  |  略過 {skip}  |  錯誤 {err}")
        return ok

    def _compress(self):
        self._conflict_all = None   # 每次壓縮重置「全部略過/覆蓋」狀態
        self._set_state(self.compress_btn, "disabled")

        if self._batches:
            # ── 批次模式 ────────────────────────────────────────────────
            total_files = sum(len(v) for v in self._batches.values())
            self._log(f"\n▶ 批次壓縮 {len(self._batches)} 個標本（共 {total_files} 張）…")
            done = [0]
            def on_progress(spec_id, i):
                done[0] += 1
                self._set_progress(done[0], total_files,
                                   f"壓縮中：{spec_id}  {done[0]}/{total_files}")
            total_ok = sum(
                self._do_compress_one(spec_id, files, on_progress)
                for spec_id, files in self._batches.items()
            )
        else:
            # ── 單一模式 ────────────────────────────────────────────────
            spec_id = self.spec_var.get().strip()
            if not spec_id:
                self.after(0, lambda: messagebox.showerror(
                    "缺少名稱", "請輸入目標資料夾名稱（例如 Cer55）"))
                self._set_state(self.compress_btn, "normal")
                return
            total_files = len(self._files)
            self._log(f"\n▶ 壓縮照片 → images/{spec_id}/（共 {total_files} 張）")
            done = [0]
            def on_progress(sid, i):
                done[0] += 1
                self._set_progress(done[0], total_files,
                                   f"壓縮中：{sid}  {done[0]}/{total_files}")
            total_ok = self._do_compress_one(spec_id, self._files, on_progress)

        if total_ok > 0:
            n = rebuild_manifest()
            self._log(f"\n  manifest.json 已更新（{n} 個資料夾）")
            self._log("✓ 完成，可前往步驟 3 同步到 GitHub")
            self._idle("✓ 壓縮完成")
        else:
            self._idle("完成（無新增）")

        self._set_state(self.compress_btn, "normal")

    # ── 3. 同步到 GitHub ─────────────────────────────────────────────────────

    def _sync_github(self):
        TOTAL  = 4
        result = ["待命"]   # finally 用

        try:
            # ── 1. 更新 manifest（25%）──────────────────────────────────
            self._set_progress(1, TOTAL, "1/4 更新索引…")
            self._log("\n▶ 同步 images/ 到 GitHub …")
            n = rebuild_manifest()
            self._log(f"  manifest.json 已更新（{n} 個資料夾）")

            # ── 2. 暫存所有變更（50%）──────────────────────────────────
            self._set_progress(2, TOTAL, "2/4 暫存變更…")
            self._log("  暫存 images/ manifest.json data.js …")
            self._git("add", "-A", "images/", "manifest.json", "data.js")

            # 顯示已暫存清單（方便診斷）
            r = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=str(BASE))
            staged_lines = [ln for ln in r.stdout.strip().splitlines()
                            if not ln.startswith("??")]
            if staged_lines:
                self._log("  已暫存的變更：")
                for ln in staged_lines:
                    self._log(f"    {ln}")
            else:
                self._log("  （無暫存變更）")

            # ── 3. 確認並提交（75%）────────────────────────────────────
            self._set_progress(3, TOTAL, "3/4 提交中…")
            self._log("  確認是否有需要提交的內容…")
            has_changes = subprocess.run(
                ["git", "diff", "--cached", "--quiet"], cwd=str(BASE)).returncode != 0
            if not has_changes:
                self._log("  沒有需要同步的變更")
                result[0] = "無需同步"
                return

            if not self._git("commit", "-m", "同步 images 到 GitHub"):
                result[0] = "✗ commit 失敗"
                return

            # ── 4. 推送（時間不定 → 跑馬燈）──────────────────────────
            self._busy("4/4 推送到 GitHub 中…")
            self._log("  推送到 GitHub（視網路速度需數秒）…")
            ok = self._git("push")
            if ok:
                self._log("✓ 同步完成！網站約 1～2 分鐘後更新。")
                result[0] = "✓ 同步完成"
            else:
                self._log("✗ push 失敗，請確認網路與 git 設定")
                result[0] = "✗ push 失敗"

        except Exception as e:
            self._log(f"  [未預期錯誤] {e}")
            result[0] = "✗ 發生錯誤"
        finally:
            self._idle(result[0])   # 無論如何都會重置進度條

    # ── 匯出可攜版 ──────────────────────────────────────────────────────────

    # 不必帶到離線電腦的資料夾／檔案（容量大或可重建）
    EXPORT_EXCLUDE_DIRS  = ["RAW image", "__pycache__", "backups", "dist", "build", ".vs"]
    EXPORT_EXCLUDE_FILES = ["*.exe", "*.spec", "*.pyc", "*.pyo"]

    def _export_portable(self):
        """在主執行緒選目的地，再丟到背景執行緒複製。"""
        dest = filedialog.askdirectory(title="選擇匯出位置（例如隨身碟）")
        if not dest:
            return
        dest = pathlib.Path(dest)
        try:
            dest_r, base_r = dest.resolve(), BASE.resolve()
            if dest_r == base_r or base_r in dest_r.parents:
                messagebox.showerror(
                    "位置錯誤", "請選擇專案資料夾「以外」的位置（例如隨身碟），"
                    "以免複製到自己裡面。")
                return
        except Exception:
            pass
        self._bg(lambda: self._do_export(dest))

    def _do_export(self, dest: pathlib.Path):
        result = ["待命"]
        try:
            self._busy("匯出可攜版中…")
            ts     = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            target = dest / f"Ceratopogonidae_photo_可攜版_{ts}"
            self._log(f"\n▶ 匯出可攜版 → {target}")
            self._log("  複製中（含 images/ 與 .git，視容量需數十秒）…")

            # robocopy：/E 複製含子資料夾；保留 .git 讓日後仍可 pull/push
            cmd = ["robocopy", str(BASE), str(target), "/E",
                   "/NFL", "/NDL", "/NJH", "/NP", "/R:1", "/W:1",
                   "/XD", *self.EXPORT_EXCLUDE_DIRS,
                   "/XF", *self.EXPORT_EXCLUDE_FILES]
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            for line in (r.stdout or "").splitlines():
                if line.strip():
                    self._log("  " + line.rstrip())

            # robocopy 回傳碼 0–7 皆為成功，8 以上才是錯誤
            if r.returncode < 8:
                self._log(f"✓ 匯出完成：{target}")
                self._log("  可把整個資料夾複製到離線電腦，雙擊 啟動維護工具.bat 即可使用；")
                self._log("  雙擊 index.html 可離線瀏覽網站。")
                result[0] = "✓ 匯出完成"
            else:
                self._log(f"  [錯誤] robocopy 回傳碼 {r.returncode}")
                if r.stderr:
                    self._log(f"  {r.stderr.strip()}")
                result[0] = "✗ 匯出失敗"

        except FileNotFoundError:
            self._log("  [錯誤] 找不到 robocopy（Windows 內建工具）")
            result[0] = "✗ 無 robocopy"
        except Exception as e:
            self._log(f"  [未預期錯誤] {e}")
            result[0] = "✗ 發生錯誤"
        finally:
            self._idle(result[0])


if __name__ == "__main__":
    app = App()
    app.mainloop()
