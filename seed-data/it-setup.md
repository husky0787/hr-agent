# Harbour Finch Labs｜港雀科技 IT 設定及資訊保安指南（香港）

> 示範環境：公司、員工及內部政策均為虛構。以下系統名稱及 .example 入口用於展示，不提供真實帳戶或登入服務。

## 工作電腦

工作電腦為 MacBook Pro 或 Dell XPS。入職第 1 天 09:30 到觀塘辦公室的 IT 接待處領取，IT 會協助登入。遠端領取須於入職前 3 個工作天向 it@harbourfinch.example 預約送遞。未經批准不得使用私人裝置處理公司資料。

## VPN 設定

安裝 **Cisco AnyConnect**，使用 IT 發送至公司電郵的示範登入資料，設定伺服器為 vpn.harbourfinch.example。連接內部系統前先登入公司 VPN，切勿在聊天中貼上密碼或認證碼；登入失敗請聯絡 IT 支援。

## Slack 設定

加入 **Harbour Finch Labs** 示範 Slack 工作區，入口為 https://chat.harbourfinch.example。所有員工加入 **#general**、**#random** 及所屬團隊頻道；工程部使用 **#team-engineering**。帳戶邀請由 IT 在入職首日發送至公司電郵。

## 磁碟加密

僱員須在取得工作電腦後 **24 小時內**啟用全碟加密；Mac 使用 FileVault，Windows 使用 BitLocker。不確定是否啟用時，請聯絡 IT 協助檢查。

## 雙重認證

僱員須在 **48 小時內**為 Google Workspace、Slack 及 GitHub 啟用雙重認證（2FA）。復原碼只存放於公司提供的 1Password Business；遺失手機或無法登入時，請聯絡 IT 支援。

## 密碼管理

公司提供 1Password Business 作為帳戶密碼及復原碼管理工具。不得將公司密碼存於私人密碼管理工具，不得與他人共用密碼、雙重認證碼或 VPN 登入資料。

## 個人資料及機密文件

身份證明、銀行戶口及僱員資料只可透過 PeopleDesk 的安全文件區提交。文件僅向處理該工作的人員開放；不得在公開聊天室張貼個人資料，或將公司文件存到未經批准的私人雲端。

## 可疑電郵、裝置遺失及保安事故

收到可疑電郵、懷疑帳戶被盜或遺失裝置時，立即電郵 **security@harbourfinch.example** 並在 Slack **#security-help** 通報，保留原始郵件或事件時間等紀錄。保安事故須即時通報，不等待一般支援回覆；切勿提供密碼或認證碼。

## 開發環境及系統權限

在 IT Helpdesk 提交工單，類別選擇 **Developer Access**，申請 GitHub 組織存取權限。GitHub 示範組織代號為 harbourfinch-demo，入口為 https://code.harbourfinch.example。工程師按專案要求安裝 Docker、Node.js 20+ 及 Python 3.11+；測試環境由主管 Maya Wong 審批，正式環境及發佈權限須另外經主管與 IT 審批。

## IT 支援聯絡方式

一般支援電郵為 **it@harbourfinch.example**，Slack 頻道為 **#it-support**；工單入口為 https://help.harbourfinch.example。服務時間為週一至週五 09:30–18:30，一般支援回覆目標為 **4 個工作小時**，不代表問題必定在 4 小時內解決。
