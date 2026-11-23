# 執行 HR Agent

首次安裝 Python / Node.js / PostgreSQL、建立資料庫、設定 `.env` 及資料備份，請先閱讀 [README](../README.md)。以下命令均從專案根目錄執行；Windows 使用 PowerShell。

## 本機後端

已安裝後端依賴並確保 PostgreSQL 正在運行後：

```powershell
$env:PYTHONPATH = "$PWD;$PWD/backend"
./.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
```

`--env-file .env` 會在載入程式前讀取聊天模型和資料庫設定。

## 本機前端

另開 PowerShell，從專案根目錄執行：

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

依賴未變動時可略過 `npm.cmd ci`。前端位於 http://localhost:5173，API 文件位於 http://localhost:8000/docs。

## MCP 伺服器

需要使用獨立 MCP 工具時，先安裝其依賴，再載入 `.env` 並執行伺服器：

```powershell
./.venv/Scripts/python.exe -m pip install -r mcp-server/requirements.txt
$env:PYTHONPATH = "$PWD"
./.venv/Scripts/python.exe -c "from dotenv import load_dotenv; load_dotenv('.env'); import runpy; runpy.run_path('mcp-server/server.py', run_name='__main__')"
```

MCP 使用標準輸入／輸出通訊。一般網頁聊天只需要前後端及 PostgreSQL。

## Docker Compose

使用 Docker 時請先啟動 Docker Desktop，並確保本機同名服務沒有佔用相關連接埠：

```powershell
docker compose up --build -d
docker compose logs -f backend
```

停止容器使用 `docker compose down`。

## 本地 embedding 檢索測試

檢索使用 CPU 上的 `intfloat/multilingual-e5-small`。首次使用會下載約 471 MB 權重及 tokenizer，快取位於 `data/models/`；Compose 會保留既有 `./data` 掛載。

E5 分別以 `passage: ` 和 `query: ` 編碼文件及問題，保留原文及來源檔名。向量儲存於 `hr_handbook_multilingual_e5_small_v1` 集合。

```powershell
./.venv/Scripts/python.exe -m pip install pytest
$env:RUN_EMBEDDING_INTEGRATION = "1"
./.venv/Scripts/python.exe -m pytest tests/test_rag.py tests/test_rag_integration.py -q
```

已驗證共 22 項。測試使用臨時索引，不需要聊天 API Key、PostgreSQL 或 Docker。模型完整下載後，可先設定 `$env:HF_HUB_OFFLINE = "1"` 驗證離線檢索。

混合語言檢索驗證的是預設前三條召回，不保證相關的跨語言片段一定排第一。知識文件變動後，需要按 README 的步驟重建索引。

## Golden / DeepEval

Golden 及 DeepEval 共用 29 個港雀科技虛構公司個案，已對應目前香港示範知識文件。歷史 22/28 成績不代表目前版本的成績；詳細背景與操作見 [EVALS.md](EVALS.md)。

使用 Docker 執行提示注入個案：

```powershell
docker compose --profile evals run --rm evals --filter prompt_injection
```

報告位於 `evals/results/`，可在前端「評估結果」頁查看。聊天及模型評分會使用 API；DeepEval 評分模型可能需要另行設定。

## 疑難排解

| 情況 | 檢查方式 |
|---|---|
| 找不到 `shared` 或 `agent` | 在專案根目錄執行，並按上面的命令設定 `PYTHONPATH` |
| `OPENAI_API_KEY is required` | 檢查 `.env` 是否已填密鑰，並以 `--env-file .env` 啟動後端 |
| 連不到資料庫 | 檢查 PostgreSQL 服務及 `.env` 的 `DATABASE_URL`，確認帳戶和資料庫已建立 |
| 首次搜尋需較長時間 | 首次需要下載 embedding 模型，並建立向量索引 |
| 新文件未出現在回答中 | 重建索引後重新啟動後端及 MCP 程序 |
| 評估頁沒有報告 | 執行評估後重新整理頁面；啟動應用程式不會自動產生本機評估報告 |
| 連接埠已被佔用 | 避免同時啟動本機及 Docker 的相同服務；檢查 5432、8000、5173 |
