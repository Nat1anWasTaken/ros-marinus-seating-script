# ros-marinus-seating-script

因為懶得手動調整座位，寫了一個腳本來自動調整座位。

# 功能

本腳本會自動處理音樂會或類似活動的座位分配。它會：

1. 從 `available-seats.jsonc` 讀取可用的座位區塊和座位。
2. 從 `audiences.csv` 讀取觀眾的劃位請求，並依照時間戳記排序。
3. 根據請求時間的先後順序，為觀眾分配座位。
4. 在終端機印出劃位結果。
5. 將劃位結果（包括未成功劃位的請求）匯出成一個新的 CSV 檔案。

# 依賴套件

本腳本需要 `commentjson` 套件來讀取 `available-seats.jsonc` 檔案（因其支援 JSONC 格式中的註解）。

在執行腳本前，請先安裝此套件：

```bash
pip install commentjson
```

# 輸入檔案

腳本需要以下兩個檔案才能運作，且必須放在與 `main.py` 相同的目錄下：

## 1. `available-seats.jsonc`

此檔案定義了可用的座位區塊及各區塊中的座位。它是一個 JSONC 檔案（JSON with Comments）。

**格式範例：**

```jsonc
{
  "block-1": [
    // 第一區塊
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5"
  ],
  "block-2": [
    // 第二區塊
    "C1",
    "C2",
    "C3",
    "D1",
    "D2",
    "D3"
  ]
  // 可以有更多區塊...
}
```

- 區塊名稱（例如 `"block-1"`）應包含一個數字，腳本會依照此數字順序處理區塊。
- 每個區塊的值是一個包含座位號碼字串的列表。

## 2. `audiences.csv`

此檔案包含了觀眾的劃位請求。它是一個 CSV 檔案，第一列是標頭。

**必要欄位順序與說明：**

1.  **時間戳記 (Allocation Time)**：請求提交的時間，格式為 `YYYY/MM/DD AM/PM HH:MM:SS` (例如 `2025/5/14 下午 5:51:07`)。這是排序請求的主要依據。
2.  **您的身份 (Your Identity)**：此欄位目前未使用，但應存在。
3.  **團員姓名 (Member Name)**：索票團員的姓名。
4.  **持票人姓名 (Ticket Holder Name)**：實際持票人的姓名。如果此欄位為空，則會使用「團員姓名」。
5.  **可複製內容 (Copiable)**：此欄位目前未使用，但應存在。
6.  **樂器別 (Instrument)**：此欄位目前未使用，但應存在。
7.  **張數 (Number of Tickets)**：需要的票券數量。如果為空或 0，該請求將被忽略。
8.  **領票方式 (Pickup Method)**：領票方式的說明。

**CSV 範例：**

```csv
時間戳記,您的身份,團員姓名,持票人姓名,可複製內容,樂器別,張數,領票方式
2025/5/14 下午 5:51:07,團員,王小明,王大明,是,小提琴,2,現場領票
2025/5/14 上午 10:22:15,親友,陳小華,,否,長笛,1,親友代領
```

- 腳本會使用 `utf-8-sig` 編碼讀取此檔案，以處理潛在的 BOM (Byte Order Mark)。
- 如果某列的欄位數不足，或「張數」無法轉換為數字，該列將被跳過並顯示警告。

# 使用方法

```bash
python main.py
```

執行後，腳本會：

1.  提示 `available-seats.jsonc` 和 `audiences.csv` 的讀取情況。
2.  顯示座位分配的過程。
3.  在終端機印出詳細的劃位結果，包括每個區塊的劃位情況以及無法劃位的請求。
4.  最後，會提示您輸入一個檔名，以將結果匯出成 CSV 檔案。若未輸入檔名，則會跳過匯出步驟。如果輸入的檔名不以 `.csv` 結尾，腳本會自動添加。

# 輸出

## 1. 終端機輸出

腳本會在終端機中詳細列出每個區塊的座位分配情況：

```
--- Seating Assignment Results ---

Block 1 ======
A1: Member: 王小明, Ticket Holder: 王大明, Pickup: 現場領票, Time: 2025/05/14 17:51:07
A2: Member: 王小明, Ticket Holder: 王大明, Pickup: 現場領票, Time: 2025/05/14 17:51:07
...

--- Requests That Could Not Be Seated ---
- Ticket Holder: 陳小華, Tickets: 1, Time: 2025/05/14 10:22:15 (Original CSV Row: 3)
```

## 2. CSV 檔案匯出

腳本會將劃位結果（包括成功劃位和未成功劃位的請求）儲存到您指定的 CSV 檔案中。
匯出的 CSV 檔案包含以下欄位：

- `Block`：座位所在的區塊。
- `Seat Number`：座位號碼。
- `Member Name`：索票團員姓名。
- `Ticket Holder Name`：持票人姓名。
- `Number of Tickets`：該請求的總票數（注意：此欄位在匯出的 CSV 中，對於已劃位的項目，目前腳本邏輯可能未直接填入原始請求的票數，而是反映單一座位的資訊。對於未劃位的請求，則顯示原始請求的票數）。
- `Pickup Method`：領票方式。
- `Allocation Time`：原始請求的時間戳記。

對於未能成功劃位的請求，`Block` 和 `Seat Number` 欄位會是空的，但其他資訊會被記錄下來。
