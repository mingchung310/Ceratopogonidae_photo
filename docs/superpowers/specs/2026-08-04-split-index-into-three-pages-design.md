# 拆分 index.html 成三個獨立頁面

## 背景與目的

目前 `index.html`（1670 行）用單一檔案 + JS 分頁（`switchTab()`）實作「認識庫蠓／分類與鑑定／標本影像」三個分頁，三頁的 CSS、JS、內容全部塞在同一個檔案裡。使用者反映檔案太大不好管理，希望把三個分頁拆成三個獨立檔案，之後要改某一頁內容時，直接開對應檔案改就好，不用在 1670 行的大檔案裡找。

單純的檔案管理需求，不追求 SEO、不追求分頁單獨分享（雖然會是附帶效果）。

## 現況結構（拆分前）

| 區塊 | 行號 | 內容 |
|---|---|---|
| `<head>` + `<style>` | 1–772 | 共用 CSS，含 header/nav、page-hero、taxon-tree、feature-grid、plate-parts（種級代表照＋燈箱）、grid/card、modal、cmp-window（比對浮動視窗）、footer 等所有樣式 |
| `<header>` + nav | 775–786 | 站名 + 三個 `.tab-btn` 按鈕，`data-tab` 對應分頁 id |
| `#page-intro` | 792–908 | 認識庫蠓：純靜態文字/圖片，無資料依賴 |
| `#page-taxonomy` | 911–1027 | 分類與鑑定：分類研究史／分類位置／屬級特徵／亞屬概況（靜態）＋ `<iframe src="key.html">`（互動檢索）＋ 種級代表照（`#plate-root`，JS 渲染） |
| `#page-specimens` | 1033–1090 | 標本影像：篩選器 UI + `#grid` 容器，實際內容由 JS 動態渲染 |
| `<footer>` | 1096–1101 | 版權 + 「最後更新」時間（`lastupdated.js` 提供） |
| `<script>` 區塊 | 1106–1668 | `switchTab()`／分頁初始化、種級代表照渲染＋燈箱（`renderPlate`/`plateZoom`/`plateImgErr`）、key.html iframe 高度同步（`measureKeyFrame`/`armKeyFrameFallback`/`showKeyFrameFallback`/`reloadKeyFrame`）、標本影像的全部邏輯（CSV 解析、`transformRow`、篩選、`renderGrid`、`openWindow`/比對浮動視窗、拖曳等） |

三個外部 script：`data.js`（標本資料，僅 specimens 用）、`species_plate.js`（種級代表照清單，僅 taxonomy 用）、`lastupdated.js`（最後更新日期，footer 共用）。

**重要限制**：本專案刻意不用 `fetch()` 讀本機檔案（`data.js` 把 CSV 內容包成 JS 變數就是為了這個），因為 `file://` 開啟時瀏覽器會擋 CORS。`CLAUDE.md` 明確記載「雙擊 index.html 離線預覽」是支援的使用情境，拆分後必須維持這個能力。

## 設計方案

拆成三個**真正獨立**的靜態頁面，用一般 `<a href>` 連結互相切換（整頁重新載入，不再是 SPA 瞬間切換——這是拆檔案必然的取捨，使用者已確認可接受）。

### 檔案配置

- **`index.html`**：只保留「認識庫蠓」內容，繼續當作網站首頁（GitHub Pages 根網址行為不變）
- **`taxonomy.html`**：「分類與鑑定」內容
- **`specimens.html`**：「標本影像」內容
- **`style.css`**：把現有 `<style>` 內全部 CSS 原樣抽出來，三頁共用一份 `<link rel="stylesheet" href="style.css">`。不按頁面拆分 CSS（header/footer/tab-nav 樣式三頁都要用，拆開只會增加維護負擔，換不到什麼好處）

### 共用的頭尾（每個檔案各自完整複製，不做 include/模板機制）

每個檔案各自是完整的 `<!DOCTYPE html>` 文件，維持一致的 `<head>`（meta/title/`<link rel="stylesheet">`）與 `<header>`／`<footer>`：

- `<header>` 的導覽列從 `.tab-btn` 按鈕改成 `<a class="tab-btn">` 連結，`href` 指到對應檔案；每個檔案裡手動把自己那個連結加上 `active` class（純靜態標記，不需要 JS 判斷目前頁面）
- 站名 `庫蠓標本影像` 從 `onclick="switchTab('intro')"` 改成 `<a href="index.html">`
- `<footer>` 三頁都保留（含「最後更新」），因為原本就是三頁共用內容

不引入共用 header/footer 的 JS include 或建置期拼接機制——三份小重複（各約 15 行 header + 6 行 footer）比多一層「這個檔案是不是自動產生」的心智負擔更划算，且完全不影響 `file://` 離線開啟。

### 各檔案的 JS／外部資料依賴

| 檔案 | 需要的 `<script src>` | 需要保留的行內 JS |
|---|---|---|
| `index.html` | `lastupdated.js` | 只留 footer 更新日期那段（原第 1663–1666 行） |
| `taxonomy.html` | `species_plate.js`、`lastupdated.js` | `renderPlate`／`plateImgErr`／`plateZoom`（種級代表照 + 燈箱）、`measureKeyFrame`／`armKeyFrameFallback`／`showKeyFrameFallback`／`reloadKeyFrame`／`message` 監聽（key.html iframe 高度同步）＋ footer 更新日期段；頁面載入後直接呼叫一次 `renderPlate()`（原本靠 `switchTab` 觸發，現在頁面一載入就在可視狀態，不需要延遲三次量測那套邏輯，改成 `DOMContentLoaded` 時呼叫一次 `measureKeyFrame` 即可） |
| `specimens.html` | `data.js`、`lastupdated.js` | `parseCSV`／`transformRow`／篩選相關函式／`renderGrid`／`openWindow`／比對浮動視窗（`tileWindows`／`_updateCmpToolbar`／`_makeDraggable` 等）＋ footer 更新日期段 |

移除：`switchTab()`、`TABS` 常數、`history.replaceState` 分頁 hash 邏輯、`_initTab` 判斷——這些都是 SPA 分頁專屬，拆頁後不需要。

### 行為變化（已與使用者確認可接受）

- 切換分頁變成整頁重新載入（不再是原本的瞬間切換）
- 可以直接分享/收藏個別頁面網址（例如 `.../specimens.html`）
- 舊有的 `index.html#specimens` 這類 hash 網址不再會自動跳到標本影像頁（因為 hash 路由邏輯移除了）——目前沒有找到任何地方對外發布過這種帶 hash 的連結，風險低

### 文件更新

`CLAUDE.md`「資料夾結構」與「關鍵腳本說明」提到 `index.html` 是「網站本體」的敘述要更新，反映新的 `index.html` / `taxonomy.html` / `specimens.html` / `style.css` 四檔結構。

## 測試計畫

用 `.claude/launch.json` 的 `static`（`python -m http.server`）開三個頁面分別檢查：

1. `index.html`：內容完整、導覽列三個連結都能點、footer 顯示最後更新時間
2. `taxonomy.html`：分類內容顯示正常、key.html iframe 正常載入且高度自動貼合、種級代表照能渲染、點圖能放大燈箱
3. `specimens.html`：篩選器（含這幾輪改過的「翅斑型態」）正常運作、卡片渲染、開比對浮動視窗（含這幾輪改過的上限 4 個、固定 2×2 平鋪、單一視窗滿版）都要重新驗證一次，因為是从同一份 script 搬過去，功能邏輯不變，但要確認搬移過程沒有漏掉任何函式或事件綁定
4. 額外用 `file://` 直接雙擊 `specimens.html` 測一次，確認離線開啟仍然正常（`data.js` 走 `<script src>` 不受 CORS 影響）

## 範圍外

- 不改變任何頁面的視覺樣式或既有功能邏輯（純粹搬移檔案位置）
- 不新增建置腳本來產生這三個 HTML（純手動拆分、之後手動各自維護）
- 不處理 `maintenance_tool.py`「預覽網站」按鈕（它開 `index.html`，拆分後依然能正常開啟首頁，行為沒有壞掉，不需要改）
