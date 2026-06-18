# 種級代表照（species_photos）

「分類與鑑定」頁的「種級代表照」會自動讀取這個資料夾的照片。
把每個物種的代表照放進對應的物種子資料夾即可，網站會自動顯示（缺的會顯示佔位）。

## 怎麼放

每個物種一個子資料夾，**檔名固定**為下列 7 個部位（副檔名 `.jpg` 或 `.png` 皆可）：

| 檔名（不含副檔名） | 部位   |
|--------------------|--------|
| `body`             | 全身照 |
| `wing`             | 翅膀   |
| `head`             | 頭部   |
| `spermatheca`      | 儲精囊 |
| `palp`             | 小顎鬚 |
| `antenna`          | 觸角   |
| `hindleg`          | 後足   |

例：荒川庫蠓的翅膀照 → `species_photos/arakawae/wing.jpg`

## 物種清單從資料庫自動同步

物種清單（`species_plate.js`）與本資料夾的物種子資料夾，由
`gen_species_plate.py` **依資料庫（data.js）的所有種名自動產生**：

- 用維護工具按「同步 Google Sheets」時會**一併重新同步**（更新清單、補齊缺少的資料夾）。
- 也可單獨執行：`python gen_species_plate.py`
- 對照表（id / 學名 / 中文名）直接看 `species_plate.js`。
- 資料夾 id 由種小名產生（例 `Culicoides arakawae` → `arakawae`）。

> 要新增物種：在 Google Sheets 填入該標本（含 Genus / Species / 中文名），
> 再同步即可，不需手動建資料夾。

> 照片建議先縮到適合網頁的大小（寬約 800–1200 px、數百 KB）。
