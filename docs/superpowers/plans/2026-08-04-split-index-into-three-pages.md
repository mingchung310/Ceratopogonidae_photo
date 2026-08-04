# 拆分 index.html 成三個獨立頁面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把目前 1670 行的 `index.html`（SPA 式三分頁）拆成三個獨立靜態頁面 `index.html`（認識庫蠓）、`taxonomy.html`（分類與鑑定）、`specimens.html`（標本影像），並抽出共用的 `style.css`，讓每個分頁的內容各自成為單一檔案、方便日後個別維護。

**Architecture:** 純粹的內容搬移（不改任何視覺樣式或功能邏輯）。三個檔案都是完整獨立的 HTML 文件，共用同一份 `style.css`；導覽列從 JS 分頁按鈕改成一般 `<a href>` 連結（整頁跳轉取代原本的 SPA 瞬間切換）。`data.js`／`species_plate.js`／`lastupdated.js` 三個既有外部 script 依各頁實際需求分別引用，不需要修改內容。

**Tech Stack:** 純 HTML/CSS/原生 JS 靜態網站，無建置工具、無測試框架、用 `.claude/launch.json` 的 `static`（`python -m http.server 8123`）本機預覽。

## Global Constraints

- 不改變任何頁面現有的視覺樣式或功能邏輯，純粹搬移程式碼位置（來自 spec `docs/superpowers/specs/2026-08-04-split-index-into-three-pages-design.md` 的「範圍外」）
- 必須維持 `file://` 直接雙擊開啟仍可離線正常運作（`data.js` 走 `<script src>`，不可改用 `fetch()` 讀本機檔案）
- Task 1–3 執行期間**不可修改** `index.html`（後續任務要從原始 `index.html` 讀取內容），直到 Task 4 才整個改寫它
- 三個檔案都要能用 `python -m http.server 8123`（即 `.claude/launch.json` 的 `static` 設定）在瀏覽器中正常開啟

---

## Task 1: 抽出共用 CSS 到 style.css

**Files:**
- Create: `E:\2. Ceratopogonidae_photo_web\style.css`
- Read only: `E:\2. Ceratopogonidae_photo_web\index.html:9-771`（CSS 內容，不含 `<style>`/`</style>` 標籤本身）

**Interfaces:**
- Produces：`style.css`，供 Task 2／3／4 的三個 HTML 檔用 `<link rel="stylesheet" href="style.css">` 引用

- [ ] **Step 1: 把 `index.html` 第 9–771 行的 CSS 內容原樣複製到新檔案 `style.css`**

用 Read 工具讀出 `index.html` 第 9–771 行（不含第 8 行 `<style>` 與第 772 行 `</style>`），逐字複製到新檔案 `style.css` 開頭（不需要任何 `<style>` 包裝標籤，純 CSS 檔）。

- [ ] **Step 2: 修改 `.tab-btn` 規則，讓它同時支援 `<a>` 標籤（原本是 `<button>` 專用樣式）**

在 `style.css` 裡找到這段（原 `index.html:68-79`）：

```css
    .tab-btn {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--muted);
      padding: 0 1rem;
      height: 56px;
      font-size: 0.92rem;
      cursor: pointer;
      white-space: nowrap;
      font-family: inherit;
      transition: color 0.2s, border-color 0.2s;
    }
```

改成（新增 `text-decoration: none`、`display: flex`、`align-items: center`，因為拆分後 `.tab-btn` 會用在 `<a>` 標籤上，`<a>` 預設不會像 `<button>` 一樣自動置中文字、也會有底線，需要補上）：

```css
    .tab-btn {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--muted);
      padding: 0 1rem;
      height: 56px;
      font-size: 0.92rem;
      cursor: pointer;
      white-space: nowrap;
      font-family: inherit;
      text-decoration: none;
      display: flex;
      align-items: center;
      transition: color 0.2s, border-color 0.2s;
    }
```

- [ ] **Step 3: 確認檔案行數與內容完整**

Run: `wc -l "E:/2. Ceratopogonidae_photo_web/style.css"`
Expected: 約 763 行左右（771-9+1=763，加上 Step 2 新增的 3 行約 766 行）

Run（確認沒有殘留 HTML 標籤）:
```bash
grep -n "<style>\|</style>\|<html\|<body" "E:/2. Ceratopogonidae_photo_web/style.css"
```
Expected: 沒有任何輸出（no matches）

- [ ] **Step 4: Commit**

```bash
git add style.css
git commit -m "新增共用 style.css（從 index.html 抽出）"
```

---

## Task 2: 建立 specimens.html（標本影像頁）

**Files:**
- Create: `E:\2. Ceratopogonidae_photo_web\specimens.html`
- Read only: `E:\2. Ceratopogonidae_photo_web\index.html`（第 1033–1090 行為頁面內容，第 1268–1654 行為對應 JS，見下方 Step 說明）

**Interfaces:**
- Consumes：`style.css`（Task 1 產出）
- Produces：`specimens.html`，之後 Task 4 改寫 `index.html` 時，其導覽列會連到這個檔名

- [ ] **Step 1: 建立檔案骨架（head + header + footer + script 標籤）**

建立 `specimens.html`，內容如下（`<head>` 沿用原本 `index.html:1-7` 的 meta 設定，`<title>` 加上頁面名稱後綴方便分辨瀏覽器分頁；header 的三個連結中「標本影像」標成 `active`）：

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="noindex, nofollow" />
  <title>標本影像｜庫蠓標本影像：臺灣大學昆蟲學系寄生蟲實驗室</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>

<!-- ── Header ─────────────────────────────────────────────────────── -->
<header>
  <div class="header-inner">
    <a class="site-title" href="index.html">庫蠓標本影像</a>
    <nav class="tab-nav">
      <a class="tab-btn" href="index.html">認識庫蠓</a>
      <a class="tab-btn" href="taxonomy.html">分類與鑑定</a>
      <a class="tab-btn active" href="specimens.html">標本影像</a>
    </nav>
  </div>
</header>

<!-- PAGE-CONTENT-PLACEHOLDER -->

<!-- ── Footer ──────────────────────────────────────────────────────── -->
<footer>
  庫蠓標本影像 © 臺灣大學昆蟲學系寄生蟲實驗室 · 持續收錄中
  <div class="foot-meta">
    <span id="foot-updated-wrap" hidden>最後更新：<b id="foot-updated"></b></span>
  </div>
</footer>

<script src="data.js"></script>
<script src="lastupdated.js"></script>
<script>
'use strict';

<!-- SCRIPT-PLACEHOLDER -->

// ── 頁尾最後更新日期：由 lastupdated.js（推送時自動產生）提供 ──────────
//    純本機同源檔，不對外發送任何請求，離線亦可顯示。
if (window.LAST_UPDATED) {
  document.getElementById('foot-updated').textContent = window.LAST_UPDATED;
  document.getElementById('foot-updated-wrap').hidden = false;
}
</script>
</body>
</html>
```

- [ ] **Step 2: 把 `index.html` 第 1033–1090 行的頁面內容，取代掉 `<!-- PAGE-CONTENT-PLACEHOLDER -->`**

用 Read 工具讀出目前（未修改過的）`index.html` 第 1033–1090 行（`<div class="page" id="page-specimens">` 開始，到 `</div><!-- /page-specimens -->` 結束），把 `class="page"` 改成 `class="page active"`（因為現在每個檔案只有一個 page，永遠顯示），逐字複製取代 `specimens.html` 裡的 `<!-- PAGE-CONTENT-PLACEHOLDER -->`。

- [ ] **Step 3: 把 `index.html` 第 1268–1654 行的 JS，取代掉 `<!-- SCRIPT-PLACEHOLDER -->`**

用 Read 工具讀出目前（未修改過的）`index.html` 第 1268–1654 行（從 `function parseCSV(text) {` 開始，到 `dataReady.then(...).catch(...)` 那段結束，即「初始分頁切換」註解之前），逐字複製取代 `specimens.html` 裡的 `<!-- SCRIPT-PLACEHOLDER -->`（把 HTML 註解標記整行移除）。

- [ ] **Step 4: 用瀏覽器驗證頁面可正常運作**

啟動本機伺服器：
```bash
cd "E:/2. Ceratopogonidae_photo_web" && python -m http.server 8123
```

用瀏覽器工具開啟 `http://localhost:8123/specimens.html`，檢查：
1. 開發者主控台沒有 JS 錯誤（`read_console_messages`）
2. 篩選器（屬／亞屬／翅斑型態／種／全部性別／有全身照）都能顯示選項、切換後卡片列表會跟著篩選
3. 點一張標本卡片，會跳出比對浮動視窗，圖片與縮圖正常顯示
4. 連續點 5 張卡片，第 5 個視窗被擋下（上限 4 個）
5. 點「⊞ 並排平鋪」，視窗排成 2×2（開 1 個視窗時應滿版）
6. 頁尾顯示「最後更新：」日期
7. 導覽列「標本影像」呈現 active 樣式（金色底線），點「認識庫蠓」／「分類與鑑定」能跳轉（此時目標檔案還不存在會 404，屬預期，Task 3／4 完成後才會通)

Expected: 上述 1–6 都正常；第 7 點的 404 在這個 Task 屬於已知、之後會修好

- [ ] **Step 5: Commit**

```bash
git add specimens.html
git commit -m "新增 specimens.html（標本影像頁拆分自 index.html）"
```

---

## Task 3: 建立 taxonomy.html（分類與鑑定頁）

**Files:**
- Create: `E:\2. Ceratopogonidae_photo_web\taxonomy.html`
- Read only: `E:\2. Ceratopogonidae_photo_web\index.html`（第 911–1027 行為頁面內容，第 1137–1203 行與第 1212–1260 行為對應 JS，見下方 Step 說明）

**Interfaces:**
- Consumes：`style.css`（Task 1 產出）、`key.html`（既有檔案，不需修改，用 iframe 嵌入）、`species_plate.js`（既有檔案）
- Produces：`taxonomy.html`

- [ ] **Step 1: 建立檔案骨架（head + header + footer + script 標籤）**

建立 `taxonomy.html`：

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="noindex, nofollow" />
  <title>分類與鑑定｜庫蠓標本影像：臺灣大學昆蟲學系寄生蟲實驗室</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>

<!-- ── Header ─────────────────────────────────────────────────────── -->
<header>
  <div class="header-inner">
    <a class="site-title" href="index.html">庫蠓標本影像</a>
    <nav class="tab-nav">
      <a class="tab-btn" href="index.html">認識庫蠓</a>
      <a class="tab-btn active" href="taxonomy.html">分類與鑑定</a>
      <a class="tab-btn" href="specimens.html">標本影像</a>
    </nav>
  </div>
</header>

<!-- PAGE-CONTENT-PLACEHOLDER -->

<!-- ── Footer ──────────────────────────────────────────────────────── -->
<footer>
  庫蠓標本影像 © 臺灣大學昆蟲學系寄生蟲實驗室 · 持續收錄中
  <div class="foot-meta">
    <span id="foot-updated-wrap" hidden>最後更新：<b id="foot-updated"></b></span>
  </div>
</footer>

<script src="species_plate.js"></script>
<script src="lastupdated.js"></script>
<script>
'use strict';

<!-- SCRIPT-PLACEHOLDER -->

renderPlate();
armKeyFrameFallback();

// ── 頁尾最後更新日期：由 lastupdated.js（推送時自動產生）提供 ──────────
//    純本機同源檔，不對外發送任何請求，離線亦可顯示。
if (window.LAST_UPDATED) {
  document.getElementById('foot-updated').textContent = window.LAST_UPDATED;
  document.getElementById('foot-updated-wrap').hidden = false;
}
</script>
</body>
</html>
```

（註：原本 `renderPlate()` 和 `armKeyFrameFallback()` 分別由 `switchTab('taxonomy')` 觸發、和在 script 載入時直接呼叫；拆成獨立頁後，頁面一載入就是可視狀態，所以在 script 最後直接呼叫 `renderPlate()` 一次即可，不需要原本「切換分頁時才渲染」的延遲邏輯。）

- [ ] **Step 2: 把 `index.html` 第 911–1027 行的頁面內容，取代掉 `<!-- PAGE-CONTENT-PLACEHOLDER -->`**

用 Read 工具讀出目前（未修改過的）`index.html` 第 911–1027 行（`<div class="page" id="page-taxonomy">` 開始，到 `</div><!-- /page-taxonomy -->` 結束），把 `class="page"` 改成 `class="page active"`，逐字複製取代 `taxonomy.html` 裡的 `<!-- PAGE-CONTENT-PLACEHOLDER -->`。

- [ ] **Step 3: 把 `index.html` 第 1137–1203 行與第 1212–1260 行的 JS，依序取代掉 `<!-- SCRIPT-PLACEHOLDER -->`**

用 Read 工具依序讀出目前（未修改過的）`index.html`：
1. 第 1137–1203 行（`const PLATE_SPECIES = [...]` 開始，到 `function plateZoom(img) { ... }` 結束）
2. 第 1212–1260 行（`//  互動檢索 iframe（key.html）自動調整高度` 註解開始，到 `function reloadKeyFrame(btn) { ... }` 結束，但**不含**最後一行 `armKeyFrameFallback();`——這行已經在骨架的 script 尾端呼叫過了，避免重複呼叫）

把這兩段依原順序（先 1137–1203，再 1212–1259）逐字複製，取代 `taxonomy.html` 裡的 `<!-- SCRIPT-PLACEHOLDER -->`。

- [ ] **Step 4: 用瀏覽器驗證頁面可正常運作**

確認 `python -m http.server 8123` 仍在執行（若已停止，於 `E:/2. Ceratopogonidae_photo_web` 目錄重新啟動）。

用瀏覽器工具開啟 `http://localhost:8123/taxonomy.html`，檢查：
1. 開發者主控台沒有 JS 錯誤
2. 分類研究史／分類位置／屬級特徵／亞屬概況等靜態內容正常顯示
3. `key.html` 的互動檢索表 iframe 正常載入、高度自動貼合（沒有內部捲軸、沒有大片空白）
4. 「種級代表照」區塊有渲染出物種列表與圖片
5. 點一張代表照圖片，會彈出全螢幕燈箱；點燈箱背景會關閉
6. 頁尾顯示「最後更新：」日期
7. 導覽列「分類與鑑定」呈現 active 樣式

Expected: 上述都正常

- [ ] **Step 5: Commit**

```bash
git add taxonomy.html
git commit -m "新增 taxonomy.html（分類與鑑定頁拆分自 index.html）"
```

---

## Task 4: 改寫 index.html 為純「認識庫蠓」頁

**Files:**
- Modify: `E:\2. Ceratopogonidae_photo_web\index.html`（整個檔案改寫）

**Interfaces:**
- Consumes：`style.css`（Task 1）；連到 `taxonomy.html`（Task 3）、`specimens.html`（Task 2）
- Produces：新版 `index.html`，GitHub Pages 根網址（`https://mingchung310.github.io/Ceratopogonidae_photo/`）行為不變（預設顯示認識庫蠓頁）

- [ ] **Step 1: 讀出目前 `index.html` 第 792–905 行（page-intro 內容）**

在**改寫檔案之前**，先用 Read 工具讀出目前（未修改過的）`index.html` 第 792–905 行（`<div class="page active" id="page-intro">` 開始，到 `</div><!-- /page-intro -->` 結束）並記下內容——這段已經是 `class="page active"`，不需要再修改 class。

- [ ] **Step 2: 用新內容整個覆寫 `index.html`**

把整個 `index.html` 改寫成：

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="robots" content="noindex, nofollow" />
  <title>庫蠓標本影像：臺灣大學昆蟲學系寄生蟲實驗室</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>

<!-- ── Header ─────────────────────────────────────────────────────── -->
<header>
  <div class="header-inner">
    <a class="site-title" href="index.html">庫蠓標本影像</a>
    <nav class="tab-nav">
      <a class="tab-btn active" href="index.html">認識庫蠓</a>
      <a class="tab-btn" href="taxonomy.html">分類與鑑定</a>
      <a class="tab-btn" href="specimens.html">標本影像</a>
    </nav>
  </div>
</header>

<!-- PAGE-CONTENT-PLACEHOLDER -->

<!-- ── Footer ──────────────────────────────────────────────────────── -->
<footer>
  庫蠓標本影像 © 臺灣大學昆蟲學系寄生蟲實驗室 · 持續收錄中
  <div class="foot-meta">
    <span id="foot-updated-wrap" hidden>最後更新：<b id="foot-updated"></b></span>
  </div>
</footer>

<script src="lastupdated.js"></script>
<script>
'use strict';

// ── 頁尾最後更新日期：由 lastupdated.js（推送時自動產生）提供 ──────────
//    純本機同源檔，不對外發送任何請求，離線亦可顯示。
if (window.LAST_UPDATED) {
  document.getElementById('foot-updated').textContent = window.LAST_UPDATED;
  document.getElementById('foot-updated-wrap').hidden = false;
}
</script>
</body>
</html>
```

再把 Step 1 讀到的 page-intro 內容（`<div class="page active" id="page-intro">...</div><!-- /page-intro -->`）貼到 `<!-- PAGE-CONTENT-PLACEHOLDER -->` 的位置。

- [ ] **Step 3: 確認舊有的 SPA 專屬程式碼都已移除**

Run:
```bash
grep -n "switchTab\|data-tab\|TABS = \|_initTab\|page-taxonomy\|page-specimens\|parseCSV\|renderGrid" "E:/2. Ceratopogonidae_photo_web/index.html"
```
Expected: 沒有任何輸出（no matches）——確認 `index.html` 裡不再殘留分類/標本頁的內容或 SPA 分頁邏輯

- [ ] **Step 4: 用瀏覽器驗證頁面可正常運作**

確認 `python -m http.server 8123` 仍在執行。

用瀏覽器工具開啟 `http://localhost:8123/index.html`，檢查：
1. 開發者主控台沒有 JS 錯誤
2. 認識庫蠓的內容（首頁 hero 圖、什麼是庫蠓、形態特徵圖等）正常顯示
3. 導覽列「認識庫蠓」呈現 active 樣式，點「分類與鑑定」「標本影像」能正確跳轉到 `taxonomy.html`／`specimens.html`（此時應該都存在且正常，不再 404）
4. 從 `specimens.html` 或 `taxonomy.html` 點「庫蠓標本影像」站名或「認識庫蠓」，能跳轉回 `index.html`
5. 頁尾顯示「最後更新：」日期

Expected: 上述都正常，三個頁面之間互相跳轉都不再 404

- [ ] **Step 5: 用 `file://` 直接開啟驗證離線可用**

用瀏覽器工具直接開啟本機路徑 `file:///E:/2.%20Ceratopogonidae_photo_web/specimens.html`（離線、不透過 http server），檢查：
1. 開發者主控台沒有 CORS 相關錯誤
2. 標本卡片列表仍然正常渲染（代表 `data.js` 的內嵌資料機制在拆分後依然生效）

Expected: 離線開啟一樣正常，沒有因為 fetch 被 CORS 擋住

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "index.html 改寫為純認識庫蠓頁（三分頁拆分完成）"
```

---

## Task 5: 更新 CLAUDE.md 反映新的檔案結構

**Files:**
- Modify: `E:\2. Ceratopogonidae_photo_web\CLAUDE.md`

**Interfaces:**
- 無程式碼介面，純文件更新

- [ ] **Step 1: 更新「資料夾結構」區塊**

在 `CLAUDE.md` 的資料夾結構樹狀圖裡，找到這行：

```
├── index.html          網站本體（勿手動改 data）
```

改成：

```
├── index.html          網站首頁「認識庫蠓」
├── taxonomy.html       「分類與鑑定」頁（含 key.html 互動檢索 iframe）
├── specimens.html      「標本影像」頁（篩選器、標本卡片、比對浮動視窗）
├── style.css            index.html／taxonomy.html／specimens.html 共用樣式
```

（放在原本 `index.html` 那一行的位置，`key.html` 之前）

- [ ] **Step 2: 更新「情境三：本地預覽網站」區塊**

找到：

```
## 情境三：本地預覽網站

​```powershell
.\build.ps1
# 然後直接雙擊 index.html
​```

或雙擊 `launch.bat`（啟動 localhost:8080）
```

改成：

```
## 情境三：本地預覽網站

​```powershell
.\build.ps1
# 然後直接雙擊 index.html（認識庫蠓）／taxonomy.html（分類與鑑定）／specimens.html（標本影像）
​```

或雙擊 `launch.bat`（啟動 localhost:8080），三個頁面用導覽列互相切換
```

- [ ] **Step 3: 在「注意事項」加一條說明三檔案共用 style.css**

在「注意事項」清單最後加一條：

```
- 網站分成 `index.html`／`taxonomy.html`／`specimens.html` 三個獨立頁面，共用 `style.css`；改樣式只需要改 `style.css`，改某一頁內容只需要改對應的那個檔案
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "更新 CLAUDE.md：反映三頁拆分後的檔案結構"
```

---

## Task 6: 最終整合驗證與推送

**Files:**
- 無新增/修改檔案，純驗證

- [ ] **Step 1: 確認三個頁面在同一次伺服器啟動下互相導覽都正常**

確認 `python -m http.server 8123` 仍在執行（於 `E:/2. Ceratopogonidae_photo_web` 目錄）。

用瀏覽器工具依序操作：
1. 開 `http://localhost:8123/index.html` → 點「分類與鑑定」→ 確認跳到 `taxonomy.html` 且內容正確
2. 在 `taxonomy.html` 點「標本影像」→ 確認跳到 `specimens.html` 且內容正確
3. 在 `specimens.html` 點站名「庫蠓標本影像」→ 確認跳回 `index.html`

Expected: 三個方向的導覽都正確跳轉、內容正常，沒有 404 或 JS 錯誤

- [ ] **Step 2: 確認 `git status` 乾淨、`git log` 顯示本次所有 commit**

Run: `git status`
Expected: `nothing to commit, working tree clean`（`庫蠓比較表.docx` 這種既有未追蹤檔案不算，維持原狀即可）

Run: `git log --oneline -8`
Expected: 依序看到 Task 1–5 的 6 個 commit（style.css → specimens.html → taxonomy.html → index.html 改寫 → CLAUDE.md）

- [ ] **Step 3: 停止本機伺服器**

Run: `pkill -f "http.server 8123"` (或直接停止 Task 工具啟動的 preview server)

- [ ] **Step 4: 詢問使用者是否要 push 到遠端**

不要自動 push。跟使用者確認這幾個 commit 都要推上 GitHub 後，才執行 `git push`（沿用這個專案一直以來的習慣：commit 完先問過使用者才 push）。

---

## Self-Review Notes

- **Spec coverage**：spec 裡的檔案配置（index/taxonomy/specimens.html + style.css）、共用 header/footer 手動複製、各頁 JS/資料依賴表、行為變化（整頁跳轉、無 SPA hash）、CLAUDE.md 更新、測試計畫（http.server 三頁 + file:// 離線）都各自對應到 Task 1–6，無遺漏。
- **Placeholder scan**：所有 Step 都給出完整檔案內容或明確行號＋操作方式，沒有「之後補上」「參考 Task N」這類含糊描述；唯一用「原樣複製第 X–Y 行」的地方，是因為來源內容已存在且經過人工核對行號範圍，屬於機械式搬移而非新邏輯，不算佔位符。
- **Type/命名一致性**：`renderPlate`／`armKeyFrameFallback`／`plateZoom` 等函式名稱、`groupFilter`／`CMP_MAX`／`cmpWindows` 等變數名稱在 Task 2、3 的搬移範圍內原封不動，沒有改名，不會有簽名不一致的問題。
