# 美元指數 (DXY) 多週期與跨週期前瞻雙軌通道分析系統

完全依照「集中市場加權指數 (TAIEX)」與「道瓊工業平均指數 (DJI) v2」極簡頂部單列導覽版面建置之美元指數（US Dollar Index, `DXY` / `DX-Y.NYB`）日/周/月 12 期滾動雙軌通道與 11 期次期前瞻預測分析系統。

## 1. 檔案結構說明
- `index.html`：前端單檔互動式儀表板（頂部單列整合標題、`ICE / Yahoo 官方結算`、`⚡ 最新盤後更新` 標籤，以及「🌐 跨週期融合 (日/周/月)」、「📅 日 K 線 (395天+次日)」、「📊 周 K 線 (69週+次週)」、「🗓️ 月 K 線 (26個月+次月)」四大切換按鍵；支援 Y 軸右側 30% 半透明防遮擋動態標籤）。
- `raw_daily.csv`：歷史日 K 資料庫（經 ICE 官方結算、Investing.com 與 Barchart 交叉比對驗證之 395 筆歷史日線 `2025-03-28 ~ 2026-10-16`）。
- `raw_weekly.csv`：歷史周 K 資料庫（69 筆完整週線 `2025-06-27 ~ 2026-10-16`）。
- `raw_monthly.csv`：歷史月 K 資料庫（26 筆完整月線 `2024-09 ~ 2026-10`）。
- `excel_baseline_20261016/`：完整保留 2026/10/16 基準三週期 CSV 備份。
- `update_dxy.py`：每日美股盤後自動抓取引擎（內建 Yahoo Finance 雙主機 CDN `DX-Y.NYB` / `DX=F`、Stooq `dx.f` / `^dxy`、CNBC `.DXY` 三重備援，自動對齊美東交易日、更新日/周/月 CSV 並重新計算注入 `index.html`）。
- `send_email_report.py`：每日盤後自動寄送雙信箱（`hawk82508@gmail.com`、`skfg7381@skl.com.tw`）之二進制 `.html` 報告推播腳本。
- `.github/workflows/daily_update.yml`：GitHub Actions 自動排程設定檔（台灣時間週二至週六清晨 05:30 / UTC 21:30 自動執行）。

## 2. GitHub 與 Netlify 部署步驟
1. 在 GitHub 建立新儲存庫（例如 `dxy-channel-dashboard`），將本套件內所有檔案（含 `.github/workflows/daily_update.yml`）上傳至 `main` 分支。
2. 於 GitHub Repository -> **Settings** -> **Actions** -> **General** -> **Workflow permissions**，勾選 **Read and write permissions** 並儲存。
3. 如需啟用每日盤後自動寄信，請於 **Settings** -> **Secrets and variables** -> **Actions** 新增：
   - `GMAIL_USER`：您的 Gmail 帳號（如 `hawk82508@gmail.com`）
   - `GMAIL_APP_PASSWORD`：16 碼 Google 應用程式專用密碼
4. 登入 Netlify 綁定該 GitHub 儲存庫，每次 GitHub Actions 盤後自動 Commit 後，Netlify 將於 10 秒內自動更新全球線上版網頁。
