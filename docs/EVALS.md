# 聊天與文件測試

## 離線回歸

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest tests -q
cd frontend
npm.cmd test
npm.cmd run build
npm.cmd run lint
```

外部 API 使用 mock，涵蓋 GPT 成功／故障備援、冷卻探測、取消及逾時；Jina 向量驗證、索引增量更新、失敗時原子性和並行建索引；文件 API／路徑限制、LangGraph 及前端 SSE／閱讀／草稿。未啟用的真實 API 測試會跳過。

## 真實 Jina 檢索

需要有效 `.env`，會消耗 Jina 額度；不下載 E5 或連接資料庫。三組中英問題檢查 top-3 命中，另驗證維度及正規化。測試共用一個臨時索引，避免每題重算文件。

```powershell
$env:RUN_API_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_rag_integration.py -q
Remove-Item Env:RUN_API_INTEGRATION
```

## Golden

`evals/scenarios.yaml` 保留 29 個港雀科技公司政策、安全及範圍限制個案。舊建立任務／安排會面的題目改為驗證助理說明無法執行，不再要求資料庫。

```powershell
$env:PYTHONPATH = "$PWD;$PWD/backend"
.\.venv\Scripts\python.exe evals/run_evals.py --filter pto_policy
.\.venv\Scripts\python.exe evals/run_evals.py --filter prompt_injection
```

完整 29 題會逐題使用聊天 API；移除 `--filter` 才執行完整評估。結果寫入 `evals/results/latest.json`，通過門檻 85%。過濾執行會覆蓋 latest，但其成績只代表已選題目。沒有公開評估頁面，不在一般啟動或部署時自動呼叫模型。

Docker 可手動執行：

```bash
docker compose --profile evals run --rm --build evals --filter pto_policy
```

## DeepEval（可選）

```powershell
.\.venv\Scripts\python.exe -m pip install -r evals/requirements.txt
$env:PYTHONPATH = "$PWD;$PWD/backend"
.\.venv\Scripts\python.exe evals/run_deepeval.py --filter pto_policy
```

DeepEval 有獨立的評分模型及額外 API 費；須按其供應商設定 `DEEPEVAL_MODEL`、Key／端點。聊天供應商的自動備援不會替評分模型設定認證。報告為 `evals/results/deepeval-latest.json`。歷史四 agent／E5 的分數不代表目前版本品質。
