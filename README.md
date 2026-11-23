# HR Agent — 港雀科技入職示範

以虛構公司 **Harbour Finch Labs｜港雀科技** 為背景，用香港繁體中文查詢公司政策、福利及 IT 設定，建立首 30 天入職待辦事項，並安排主管或人力資源部跟進會面。回答會引用知識文件，介面支援串流回覆及入職進度追蹤。

## 目前功能

- **四個 Agent 角色**：流程協調、文件查詢、入職安排及回覆整理；共用所設定的聊天模型，按需要依次執行。
- **四項工具**：搜尋公司文件、建立待辦事項、列出待辦事項及安排跟進會面。
- **本地中英文檢索**：使用 `intfloat/multilingual-e5-small`，在 CPU 上產生向量，以 Chroma 儲存及搜尋。
- **香港繁體中文介面**：聊天提示、文件引用、處理進度、跟進會面及評估頁面；日期按香港時區顯示。點擊回覆下方的文件來源標籤，可在頁面內閱讀文件全文，並保留聊天內容及草稿。
- **PostgreSQL**：儲存入職待辦事項、完成狀態及跟進會面。
- **MCP 伺服器**：提供相同的人事工具供其他 MCP 用戶端使用。
- **提示注入防護**：輸入檢查、輸出檢查、寫入工具限制及伺服器端參數驗證。

## 架構

```mermaid
flowchart LR
    UI[React 前端] --> API[FastAPI REST / SSE]
    API --> Router[流程協調]
    Router --> Research[文件查詢]
    Router --> Workflow[入職安排]
    Research --> RAG[本地 E5 + Chroma]
    Workflow --> DB[(PostgreSQL)]
    Research --> Answer[回覆整理]
    Workflow --> Answer
    Answer --> UI
    MCP[MCP 伺服器] --> RAG
    MCP --> DB
```

文件查詢負責 RAG 檢索；入職安排負責資料庫操作；回覆整理根據取得的資料生成答案。流程協調會決定需要哪些角色，不是每次都執行全部角色。

## 環境設定

首次下載：

```powershell
git clone https://github.com/husky0787/hr-agent.git
cd hr-agent
Copy-Item .env.example .env
```

已有 `.env` 時請保留，避免覆蓋密鑰。編輯 `.env`：

```dotenv
OPENAI_API_KEY=填入你的服務密鑰
OPENAI_BASE_URL=https://share.transmd.cloud/v1
OPENAI_MODEL=gpt-6.1-sol
OPENAI_ACTOR_AUTHORIZATION=local-image-extension

POSTGRES_USER=onboardai
POSTGRES_PASSWORD=onboardai
POSTGRES_DB=onboardai
DATABASE_URL=postgresql://onboardai:onboardai@localhost:5432/onboardai
```

以上聊天設定對應目前使用的代理。使用其他供應商時，請修改地址、模型及所需請求標頭；不需要自訂標頭時，可將 `OPENAI_ACTOR_AUTHORIZATION` 留空。

聊天服務須支援 **Responses API、工具呼叫及結構化輸出**。程式會傳送 `store=False`。API Key 供聊天使用；本地 embedding 不需要 API Key。`review_model`、`wire_api` 及 Codex 功能開關不會由本專案讀取。

## 不用 Docker 啟動：Windows / PowerShell

需要 Python 3.11 或以上、Node.js（本機已使用 24.12.0 驗證）及 PostgreSQL 16。前端和後端分開在兩個終端機執行。

### 1. 首次建立資料庫

安裝 PostgreSQL 16，保留連接埠 `5432`，並記下安裝時設定的 `postgres` 管理員密碼：

```powershell
winget install --exact --id PostgreSQL.PostgreSQL.16 --interactive
```

安裝服務啟動後，建立與上面 `.env` 對應的帳戶及空白資料庫。以下只需首次執行；命令會要求輸入管理員密碼：

```powershell
& "C:/Program Files/PostgreSQL/16/bin/psql.exe" -h localhost -U postgres -c "CREATE USER onboardai WITH PASSWORD 'onboardai';"
& "C:/Program Files/PostgreSQL/16/bin/psql.exe" -h localhost -U postgres -c "CREATE DATABASE onboardai OWNER onboardai;"
```

如已自行建立帳戶或更改密碼，請同步修改 `.env`。後端啟動時會自動建立業務資料表。

### 2. 首次安裝後端依賴

在專案根目錄執行；已有虛擬環境時毋須重新建立：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

### 3. 啟動後端

在第一個 PowerShell 視窗、專案根目錄執行：

```powershell
$env:PYTHONPATH = "$PWD;$PWD/backend"
./.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
```

### 4. 啟動前端

在第二個 PowerShell 視窗、專案根目錄執行：

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

`npm.cmd ci` 只在首次安裝或依賴更新後執行。日後啟動只需確保 PostgreSQL 正在運行，再分別執行後端命令及 `npm.cmd run dev`。前後端可用各自終端機的 `Ctrl+C` 停止；PostgreSQL 是獨立的背景服務。

| 頁面 | 地址 |
|---|---|
| 入職助理 | http://localhost:5173 |
| API 文件 | http://localhost:8000/docs |
| 健康檢查 | http://localhost:8000/health |
| 跟進會面 | http://localhost:5173/admin/checkins |
| 評估結果 | http://localhost:5173/admin/evals |

可選「我是今天入職的工程師」、「查詢公司福利」及「建立第一星期待辦」三個示範情境。預設員工是工程部 Alex Chen，主管 Maya Wong，入職夥伴 Jamie Lau。頁面標示「示範環境：公司、員工及內部政策均為虛構」，並未接駁真實僱員登入系統。

「重設示範」會清除目前示範員工的待辦事項、跟進會面，以及本頁的聊天與草稿；回覆進行中會暫停重設。其他員工及評估用員工資料不受影響。

## 使用 Docker Compose 啟動

Docker 是另一種啟動方式，並非必要。設定好 `.env` 並啟動 Docker Desktop 後，在專案根目錄執行：

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

Compose 會啟動 PostgreSQL、後端、前端、MCP 及 pgAdmin；前端仍在 5173，API 在 8000，pgAdmin 在 8080。容器內的資料庫地址由 Compose 自動改為 `postgres`。

不要同時讓本機服務和 Compose 佔用 5432、8000 或 5173。兩種方式各自使用的 PostgreSQL 資料儲存位置不同。

停止容器：

```powershell
docker compose down
```

## RAG 知識文件及模型

核心程式是 [shared/rag.py](shared/rag.py)。目前讀取 `seed-data/` 目錄第一層的 UTF-8 Markdown（`.md`）文件：

| 文件 | 內容 |
|---|---|
| [employee-handbook.md](seed-data/employee-handbook.md) | 年假、病假、出糧、工作安排、試用期及離職 |
| [benefits-guide.md](seed-data/benefits-guide.md) | 醫療保險、強積金、稅務文件、產假、侍產假及開支報銷 |
| [it-setup.md](seed-data/it-setup.md) | 電腦、VPN、Slack、系統權限及資訊保安 |
| [onboarding-checklist.md](seed-data/onboarding-checklist.md) | 首 30 天入職安排及工程團隊工作事項 |

各段應提供完整資料，不能只寫「請參閱另一個檔案」並預期 RAG 自動追讀。PDF、Word、Excel 及 TXT 尚未有直接匯入功能。文件已填入虛構的出糧、工時、年假結轉、醫療及報銷政策；例如每月最後一個工作天出糧、09:30–18:30 上班、HKD 2,000 健康津貼及支出後 30 天內提交報銷。所有 `.example` 聯絡地址及入口都是示範資料。未有載明的資料（例如保證年終獎金）仍須如實說明資料不足。

首次檢索會從 Hugging Face 下載 `intfloat/multilingual-e5-small`，權重約 471 MB，另有 tokenizer 及執行依賴。模型快取位於 `data/models/`，向量索引位於 `data/chroma/`；Compose 會透過既有 `./data` 掛載保留快取。

文件與問題會分別加上 E5 所需的 `passage: ` 及 `query: ` 前綴，產生正規化的 384 維向量。檢索預設返回前三個片段。混合語言語料中，相關的跨語言片段未必排第一。

### 更新知識文件後

目前不會自動偵測文件變動。新增、修改或刪除文件後，須更新向量索引；單純重啟不會更新已有內容。

先停止使用相同 Chroma 目錄的後端及 MCP 程序，再於專案根目錄執行以下命令。它只重建目前 E5 集合，不會刪除 PostgreSQL 的待辦事項或會面：

```powershell
@'
from shared import rag

client = rag._get_client()
names = [collection.name for collection in client.list_collections()]
if rag.COLLECTION_NAME in names:
    client.delete_collection(rag.COLLECTION_NAME)
rag.ensure_index()
print("Indexed chunks:", rag._get_collection().count())
'@ | ./.venv/Scripts/python.exe -
```

完成後重新啟動後端及所需的 MCP 程序。

## 測試及評估

### 前端導覽回歸測試

在前端目錄執行，測試會模擬 API 回覆，不會呼叫外部模型：

```powershell
cd frontend
npm.cmd ci
npm.cmd test
```

目前涵蓋切換管理頁後保留聊天內容、引用及後續問題上下文、未傳送草稿，以及背景中的回覆。聊天狀態保留於同一分頁的應用程式記憶體，重新整理或關閉分頁後仍會清空。

### 本地檢索測試

已驗證的檢索測試共有 **22 項**，涵蓋前綴、引用原文、索引重用、中英文及跨語言檢索，以及香港年假、出糧、報銷、強積金和產假查詢。這是檢索測試數目，不代表所有模型回答的準確率。

在專案根目錄執行：

```powershell
./.venv/Scripts/python.exe -m pip install pytest
$env:RUN_EMBEDDING_INTEGRATION = "1"
./.venv/Scripts/python.exe -m pytest tests/test_rag.py tests/test_rag_integration.py -q
```

首次需要下載模型；已完整下載後，可設定 `$env:HF_HUB_OFFLINE = "1"` 驗證離線檢索。這組測試不需要聊天 API Key、PostgreSQL 或 Docker，測試索引會使用臨時目錄。

### 聊天及工作流評估

`evals/` 的 Golden harness 及 DeepEval 共用 **29 個香港虛構公司測試個案**，涵蓋年假、醫療保險、強積金、產假、侍產假、港幣報銷、IT、入職流程及 6 個提示注入個案。已同步設定出糧日期、工作時間、年假結轉及福利預期答案，另保留未公布獎金的資料不足測試。報告可在「評估結果」頁查看；這批題目更新後尚未建立完整模型評估基準，舊的 22/28 成績不適用。

相關命令與歷史背景見 [docs/EVALS.md](docs/EVALS.md)。執行聊天或模型評分會使用所設定供應商的 API；DeepEval 評分模型可能需要另行設定。

## 在另一部電腦使用及資料備份

| 資料 | 是否在 GitHub | 搬移方式 |
|---|---|---|
| 程式碼、知識文件、依賴清單 | 是 | Clone 倉庫 |
| `.env` 及密鑰 | 否 | 私下保存或在新電腦重新設定 |
| PostgreSQL 待辦事項及跟進會面 | 否 | 如需保留，匯出及還原資料庫 |
| `data/models/` | 否 | 可複製快取，或重新下載 |
| Chroma 向量索引 | 否 | 可由知識文件重新建立 |
| 聊天紀錄 | 否 | 同一分頁內切換管理頁可保留；重新整理或關閉分頁後不會保留 |

在 Windows 備份本機 PostgreSQL；命令會要求輸入專案資料庫帳戶密碼：

```powershell
New-Item -ItemType Directory -Force data | Out-Null
& "C:/Program Files/PostgreSQL/16/bin/pg_dump.exe" -h localhost -U onboardai -d onboardai -Fc -f data/onboardai.backup
```

在新電腦先建立空白 `onboardai` 資料庫，再於啟動應用程式前還原：

```powershell
& "C:/Program Files/PostgreSQL/16/bin/pg_restore.exe" -h localhost -U onboardai -d onboardai --no-owner data/onboardai.backup
```

新電腦的 PostgreSQL 管理員密碼以該機安裝設定為準。`.venv`、`node_modules` 及執行紀錄不用搬移；應在新環境重新安裝依賴。

## 專案結構

```text
hr-agent/
├── backend/           # FastAPI、LangGraph 及人事工具
├── frontend/          # React、Vite、香港繁體中文介面
├── shared/            # RAG、資料庫及共用邏輯
├── seed-data/         # 香港知識文件
├── mcp-server/        # MCP 工具伺服器
├── tests/             # 本地及真實模型檢索測試
├── evals/             # Golden / DeepEval 程式及歷史個案
├── docs/              # 執行、安全、評估及部署說明
├── data/              # 本機快取、向量索引及紀錄，不提交 Git
└── docker-compose.yml
```

## 安全及部署狀態

目前具備多層提示注入防護，包括輸入包裝、規則檢查、安全提示、輸出檢查、可疑請求的寫入限制，以及每次訊息最多建立 5 個事項。詳見 [docs/SECURITY.md](docs/SECURITY.md)。

目前仍使用預設僱員，未完成正式身份驗證、多租戶隔離及管理頁授權。公開部署前須處理身份驗證、CORS、管理操作授權及速率限制。部署設定及既有 VPS 工作流程見 [docs/DEPLOY-VPS.md](docs/DEPLOY-VPS.md)；不能以本機已驗證的結果推斷遠端部署狀態。

## 專案背景及後續方向

本專案由 Django + LlamaIndex 文件問答版本演進，加入 FastAPI、LangGraph 多角色協作、React 全端介面及 MCP 工具。

後續方向包括文件變動自動索引、PDF 匯入、正式僱員登入、HRIS / Slack 整合、pgvector 及香港版完整 Golden 評估個案。

## 授權

MIT，詳見 [LICENSE](LICENSE)。
