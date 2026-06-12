# Ceratopogonidae 標本影像網站 — Claude 維護指南

## 專案概覽

臺大寄生蟲實驗室蠓科標本影像網站，靜態網頁部署於 GitHub Pages。

- **網站**：https://mingchung310.github.io/Ceratopogonidae_photo/
- **GitHub**：https://github.com/mingchung310/Ceratopogonidae_photo
- **Google Sheets（標本資料主要來源）**：https://docs.google.com/spreadsheets/d/1n8A-wMmJxdwwFjKDfL1jsj-Llcz3QQDXrHnJ2fNMNJ8

## 維護工具

日常維護使用 `maintenance_tool.py`（GUI）：

```powershell
python maintenance_tool.py
```

功能：
- **同步 Google Sheets** — 即時下載最新資料，更新 `data.js`
- **使用本地 CSV** — 離線時從本地 CSV 更新 `data.js`
- **推送資料更新** — `git add data.js manifest.json` → commit → push
- **新增圖片** — 選取資料夾 → 重複偵測 → 壓縮 → 放入 `images/` → 上傳 GitHub
- **預覽網站** — 直接開啟 `index.html`

> 需要：`pip install pillow`

---

## 資料夾結構

```
Ceratopogonidae_photo_web/
├── index.html          網站本體（勿手動改 data）
├── build.ps1           自動產生 manifest.json + data.js
├── process_raw.py      壓縮圖片並呼叫 build.ps1
├── add_scalebar.py     旋轉 180°、加比例尺（git ignored）
├── manifest.json       圖片索引（自動產生，勿手動改）
├── data.js             離線資料備份（自動產生，勿手動改）
├── 玻片標本清單 (slide mount).csv   本地備份
├── images/             網站圖片（各標本子資料夾，≤200KB PNG）
│   ├── Cer7/
│   └── ...
└── RAW image/          原始照片（git ignored，勿上傳）
    ├── IMG_7000.JPG    比例尺參考圖，勿動
    └── Cer7/
```

## 情境一：新增標本（有新照片）

假設新增 Cer55，步驟如下：

### 1. 對原始照片加比例尺
```powershell
python add_scalebar.py
```
- 輸入：`RAW image\` 根目錄下的 JPG
- 輸出：`RAW image\output\`（已旋轉 180°、右下角加 1mm 比例尺）

### 2. 移至標本子資料夾
```
RAW image\Cer55\wings.jpg
RAW image\Cer55\head.jpg
```
> 子資料夾名稱必須和 Google Sheets 的「Cd+No.」完全一致（大小寫有別）

### 3. 壓縮圖片並更新索引
```powershell
python process_raw.py
```
- 自動壓縮到 ≤200KB PNG → `images\Cer55\`
- 自動呼叫 `build.ps1` → 更新 `manifest.json` 與 `data.js`
- `--dry-run` 可預覽不寫入

### 4. 指定封面圖（可選）
把要當封面的圖改名，在最前面加 `0.`：
```
images\Cer55\0.wings.png   ← 封面
images\Cer55\head.png
```
改完後重新執行 `.\build.ps1`

### 5. 在 Google Sheets 填入標本資料
欄位：Cd、No.、中文名、Genus、Subgenus、Species、Col. Date 等

### 6. 推上 GitHub
```powershell
git add images/ manifest.json data.js
git commit -m "新增標本 Cer55"
git push
```

---

## 情境二：只更新標本資料（不加圖片）

1. 直接在 Google Sheets 修改 → 線上版自動更新
2. 若需同步本地離線版：

```powershell
.\build.ps1
git add data.js
git commit -m "更新資料"
git push
```

---

## 情境三：本地預覽網站

```powershell
.\build.ps1
# 然後直接雙擊 index.html
```

或雙擊 `launch.bat`（啟動 localhost:8080）

---

## 關鍵腳本說明

### `build.ps1`
- 掃描 `images/` → 產生 `manifest.json`
- 從 Google Sheets 下載 CSV（失敗時用本地 CSV）→ 產生 `data.js`

### `process_raw.py`
- 掃描 `RAW image/<標本ID>/` 下所有圖片
- 用感知雜湊偵測重複（跳過相似圖）
- 壓縮到 ≤200KB PNG → `images/<標本ID>/`
- 完成後自動呼叫 `build.ps1`

### `add_scalebar.py`（git ignored）
- 對 `RAW image\` 根目錄的照片：旋轉 180°、加比例尺 → `RAW image\output\`

### `gen_keymatrix.py`
- 讀取 `Culicoides 特徵矩陣demo_filled.xlsx` → 產生 `keymatrix.js`
- `keymatrix.js` 供「分類與鑑定」頁的**種級互動矩陣檢索**使用（multi-access key）
- 特徵分兩類：互動篩選（數值 num／類別 cat）與並列比較參考表（reference）
- 要新增/修改可篩選特徵，編輯 `gen_keymatrix.py` 內的 `NUM_CHARS` / `CAT_CHARS` 後重跑：
  ```powershell
  pip install openpyxl   # 首次
  python gen_keymatrix.py
  ```
- 物種代表翅照對應表在 `SPECIES_META`

---

## 注意事項

- `data.js`、`manifest.json`、`keymatrix.js` 永遠由腳本自動產生，**不要手動修改**
- `RAW image\` 不納入 git（容量大）
- 比例尺參考圖 `RAW image\IMG_7000.JPG` 不要移動或刪除
- 封面圖邏輯：同資料夾內名稱最小的檔案自動為封面；加 `0.` 前綴可強制指定
- 標本編號大小寫需和 Google Sheets 完全一致
