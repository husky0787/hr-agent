# 可選 VPS 部署

`deploy/vps/docker-compose.yml` 沿用既有 Traefik `zanbeel` 網路及 `hr.xpotify.cc`／`hr-api.xpotify.cc` 路由，現在只運行前端和後端，不需要 PostgreSQL／pgAdmin。這份配置不代表本次已部署到遠端。

在目標主機備妥 `.env`、網路及 TLS 後才執行：

```bash
docker compose -f deploy/vps/docker-compose.yml up -d --build backend frontend
docker compose -f deploy/vps/docker-compose.yml logs -f backend
```

後端使用持久 named volume `hr_onboarding_data:/app/data`；前端編譯的 `VITE_API_URL` 及後端 `CORS_ORIGINS` 需對應實際網域。沒有公開的 `/admin/evals` 或資料庫管理頁。

不要刪除舊資料庫 volume 來套用本版；資料庫已不在啟動路徑，原資料可獨立保留。發布前請自行檢查此倉庫的 GitHub Actions／主機腳本及其目標，避免把分支修改誤當成部署授權。

驗證：

```bash
curl --fail https://hr-api.xpotify.cc/health
curl --fail https://hr-api.xpotify.cc/api/documents
```

模型評估只在手動啟用時執行，命令見 [EVALS](EVALS.md)。前後端啟動與環境變數見 [README](../README.md)。
