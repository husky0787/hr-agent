# 執行聊天與文件閱讀 Demo

先按 [README](../README.md) 安裝依賴及填好 GPT、xAI 和 Jina Key。本版不用 PostgreSQL、MCP、PyTorch 或本地 embedding 模型。

## Windows 本機

專案根目錄，第一個 PowerShell：

```powershell
$env:PYTHONPATH = "$PWD;$PWD/backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

第二個 PowerShell：

```powershell
cd frontend
npm.cmd run dev
```

[前端](http://localhost:5173) · [API 文件](http://localhost:8000/docs)。`.env` 自動讀取，環境變數優先；修改後重啟後端。

## Linux／容器

```bash
PYTHONPATH=.:backend python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Dockerfile 支援平台注入的 `PORT`。本機 Compose：

```bash
docker compose up --build -d
docker compose logs -f backend
docker compose down
```

只有前端及後端。持久資料目錄為 `/app/data`，Chroma manifest 在其 `chroma/` 子目錄。首次問答才建立索引，文件閱讀不等待索引。

## 疑難排解

| 情況 | 檢查 |
| --- | --- |
| 聊天 API Key 未設定 | 分開填 `OPENAI_API_KEY` 及 `XAI_API_KEY`；GPT Key 不可填成 xAI Key |
| GPT 每次失敗 | 查日誌的供應商及錯誤類別；預設 60 秒冷卻後由下一個問題探測恢復 |
| 搜尋 API Key 未設定 | 填 `EMBEDDING_API_KEY`、Jina 網址及模型；同名欄位只留一份 |
| 首次回答較慢 | 等待 Jina 建立文件索引；沒有下載本地模型 |
| 重啟後總要重建索引 | 確認 `DATA_DIR` 指向持久磁碟，包含 Chroma 和 manifest |
| 新文件不在清單 | 更新 `shared/documents.py` 白名單及標題後重啟 |
| 修改政策後搜尋失敗 | 重建未成功時不沿用舊政策；恢復 Jina 後重試，原文閱讀仍可用 |
| 前端跨來源失敗 | `VITE_API_URL` 是公開後端 HTTPS 地址；`CORS_ORIGINS` 是前端來源 |
| 連接埠被佔用 | 停止佔用 8000／5173 的舊實例，避免本機與 Compose 同時啟動 |

離線及真實 API 測試見 [EVALS](EVALS.md)。
