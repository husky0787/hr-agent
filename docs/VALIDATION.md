# 聊天及文件版本驗證紀錄

日期：2026-11-24（香港時間）；分支：`codex/xai-api`。

## 自動檢查

- 乾淨 Python 環境：`data/runtime-venv`，沒有安裝 `torch`、`sentence_transformers` 或 `psycopg`。
- 後端：47 passed、7 個真實 API 測試預設跳過、14 subtests passed。
- 前端：13 passed；TypeScript／Vite 正式建置成功，JS 約 402 kB。
- Lint 成功，只有既有 ThemeContext fast-refresh 警告。
- 根目錄及 VPS Compose 的無資料庫配置結構驗證通過。Docker daemon 未運行，未聲稱已完成映像建置或容器啟動測試。

## 真實供應商

- GPT 主服務 `gpt-6.1-sol`：正常回答 25 天年假並引用僱員手冊。
- 模擬主服務故障後，實際 xAI `grok-4.3` 接手，同一問題及來源仍正確。
- 兩個並行 GPT 問題均成功；正在運行的 FastAPI 再次並行測試亦返回兩個 HTTP 200。
- Jina v4：三組中英政策查詢 top-3 命中，以及 2048 維／正規化檢查均通過。首輪 6 passed、1 個連線逾時；加入總時間預算內的一次連線重試後，只重跑失敗個案，1 passed、6 deselected。
- 這是少量供應商及檢索 smoke test，不是完整 29 題 Golden／DeepEval 品質分數。

## 瀏覽器

- 桌面完整問答、年假答案及可點擊來源通過。
- 文件可從獨立清單或答案引用開啟；閱讀原文不需要聊天模型。
- 390 × 844 手機版清單、閱讀視窗和關閉後草稿／歷史保留通過，頁面沒有水平溢出。
- 真實瀏覽器曾出現一次 Jina 連線逾時，介面正確保留問題及文件閱讀；重試後成功。免費上游 API 的延遲及可用性仍是外部限制。
- 本機截圖位於忽略提交的 `data/chat-document-desktop.jpg` 及 `data/chat-document-mobile.jpg`。

## 資源量測

Windows、Python 3.10，乾淨環境的單一測試程序：載入應用程式約 72 MiB，建立／載入索引後約 129 MiB，問答及並行測試約 134 MiB；未載入本地模型或資料庫 driver。

已運行的 Uvicorn 程序在另一輪兩個並行請求測試中，耗時 3.22 秒、CPU 累計約 0.281 秒、當時 working set 約 59 MiB。Windows 會修剪 working set，因此不同時點數值不同；這些本機量測不能當作 Railway 帳單或容器記憶體保證。

原始摘要在忽略提交的 `data/api-smoke.json` 及 `data/server-load-smoke.json`。舊 PostgreSQL 資料及 E5 快取沒有刪除，亦不在新 Web 執行路徑。

## 主題辨識及中文引用更新

- 更新後後端：62 passed、7 個真實 API 測試預設跳過、14 subtests passed；前端：14 passed。正式建置及 lint 通過，只有原有 ThemeContext 警告。
- 40 個文件二級章節全部有同義詞，並逐一驗證完整標題可被辨識。涵蓋繁／簡／英文、混合語言、重複主題、英文單字邊界及「侍產假／產假」重疊。
- 回歸語料刻意令年假排名跌出舊 top-3；分項搜尋仍按序取回年假、醫療保險登記、健康津貼，沒有混入病假的 12 天。
- 真實 Jina 通過四個多主題問題：繁中、英文、中英混合福利，以及 VPN／2FA／密碼管理。前三種福利問法重用同一組主題向量；整輪只有兩個查詢 embedding 批次，每批三條，沒有文件重新 embedding。
- 真實 GPT 回答原本出錯的三項福利問題，包含年假 25 天、入職 30 天內登記醫療保險、每年 HKD 2,000 健康津貼及正確申請安排。引用使用「僱員手冊／福利及開支報銷指南」，API citations 保留可閱讀原文的內部檔名。
- 重現命令：`python scripts/smoke_topics.py --chat`（會使用設定的 API）；原始結果在忽略提交的 `data/topic-smoke.json`。
- 更新後的實際網頁通過同一三主題問題；中文引用按鈕可開啟僱員手冊原文，標題及說明不再顯示技術檔名。截圖：`data/topic-chat.jpg`。後端已重新啟動套用更新。
