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

## 物種資料夾對照

| 資料夾         | 學名                      | 中文名   |
|----------------|---------------------------|----------|
| `actoni`       | *Culicoides actoni*       | 阿氏庫蠓 |
| `arakawae`     | *Culicoides arakawae*     | 荒川庫蠓 |
| `homotomus`    | *Culicoides homotomus*    | 原野庫蠓 |
| `jacobsoni`    | *Culicoides jacobsoni*    | 雅氏庫蠓 |
| `lungchiensis` | *Culicoides lungchiensis* | 龍溪庫蠓 |
| `palpifer`     | *Culicoides palpifer*     | 帶鬚庫蠓 |
| `oxystoma`     | *Culicoides oxystoma*     | 嗜牛庫蠓 |
| `sumatrae`     | *Culicoides sumatrae*     | 蘇島庫蠓 |
| `tainanus`     | *Culicoides tainanus*     | 台南庫蠓 |

## 要新增一個物種？

1. 在這裡新增一個物種子資料夾（資料夾名用英文 id，例如 `orientalis`）。
2. 在 `index.html` 的 `PLATE_SPECIES` 陣列加一行：`{ id:'orientalis', sci:'Culicoides orientalis', zh:'東方庫蠓' }`。
3. 把照片依上表檔名放進新資料夾。

> 照片建議先縮到適合網頁的大小（寬約 800–1200 px、數百 KB）。
