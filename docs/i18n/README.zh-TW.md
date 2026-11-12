# clinic-agent-lab

版本 **0.1.0** · Apache-2.0 · [GitHub: imwyvern](https://github.com/imwyvern)

> **誠實邊界：** 僅限 SYNTHETIC 合成資料；**不是醫療器材（not a medical device）**。
> 不做診斷、不訓練臨床模型、不自動執行醫囑，也不是正式環境系統。
> 切勿輸入真實病人資料。所有建議始終是 MedicationRequest `draft`，
> 即使示範醫師確認工作流程決定，也不會改變這一點。

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

## 專案做什麼

這是一個小型 Python 工作流程實驗室：確定性 Agent 蒐集虛構病人的摘要、檢驗、過敏和用藥資訊，
起草測試資料預設的建議，並產生安全卡。未經身分驗證的**示範醫師角色**可以確認或駁回決定。
專案展示工具編排、持久化、冪等、安全閘門和可重現評估等工程方法，不選擇診斷或治療方案。

P0 交付 **10 份合成測試資料**與 **4 條自行編寫的規則**，組成 **Demo Rule Pack**。
這些短規則及任意設定的示範劑量範圍只是示範邏輯，不是臨床指引。
資源採用簡化的 FHIR 風格 JSON，不是完整 FHIR 實作，也不是可互通的 EHR。

## 快速開始

需要 Python **3.11+**；在儲存庫根目錄執行下列命令。無須金鑰、外部模型或付費服務。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m clinic_agent_lab.demo --serve
```

開啟 <http://127.0.0.1:8000>。示範完成下述流程後，會保持本機服務執行。
顯示成功摘要後按 Ctrl-C 停止，結束代碼為 0。預設資料庫是 `.demo/demo.db`；
重複執行會使用唯一的虛構業務鍵，並保留歷史。如果連接埠 8000 已被使用，可使用
`--port 8001` 或 `--port 0`，以終端機印出的位址為準。

無人值守示範會透過真實 HTTP 檢查管理頁面，然後自行結束：

```bash
python -m clinic_agent_lab.demo
```

命令印出管理頁位址及重新開啟已儲存案件的命令；檢查完成後，示範服務隨即停止。
也可以單獨啟動一個初始為空的本機 API 和管理頁服務：

```bash
python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000
```

該服務使用 `.demo/clinic.db`。若要重新查看示範歷史，在同一服務命令前設定
`CLINIC_DB_PATH=.demo/demo.db`。`.env.example` 提供設定範例；應用程式讀取環境變數，
不會自動載入 `.env`。預設 `CLINIC_CASE_TTL_SECONDS=300`；存取時檢查到期，
沒有背景工作程序。

## 示範步驟與 API

1. 正常建議進入 `awaiting_physician`；示範醫師確認後，時間線結束於 `confirmed`。
2. 青黴素類過敏產生 `block`；確認回傳 HTTP 409，案件仍可駁回。
3. 缺少指定檢驗產生 `warn`；示範確認和駁回兩條路徑。
4. 重放相同的 `clientCaseId`；回傳原案件與唯一一份草稿。
5. 短 TTL 案件進入 `expired`；到期後確認回傳 HTTP 409。
6. 查看清單、詳細資料、安全卡，以及持久化的工具、狀態和決定事件時間線。

單獨執行服務後，最小 [API 範例](../../examples/api_demo.py) 對應下列命令：

```bash
python examples/api_demo.py
```

API：`GET /api/fixtures`、`POST /api/cases`、`GET /api/cases`、
`GET /api/cases/{id}`、`POST /api/cases/{id}/decision`。
建立介面僅接受 `clientCaseId` 和內建 `fixture_id`，不接受病人紀錄上傳。
決定介面接受 `action`（`confirm`/`reject`）、`role`、`actor` 和選填的 `reason`
（僅限虛構內容）。兩種操作都要求角色為 `physician`；`observer` 回傳 HTTP 403。
**沒有身分驗證**或經核實的醫療身分。請僅綁定本機回環位址。

## 狀態機與安全語義

```text
accepted → gathering → drafted → awaiting_physician → confirmed | rejected | expired | failed
```

任何非終止狀態都可以進入 `expired` 或 `failed`。終止狀態不可重新開啟。
工具順序固定為 `get_patient_summary`、`get_labs`、`get_allergies`、
`get_medications`、`draft_order`。狀態轉移和工具輸出儲存在 SQLite 的
`cases`、`events`、`drafts` 資料表中。業務鍵 `clientCaseId` 唯一；
將相同業務鍵用於另一份測試資料會回傳 409。

安全卡等級為 `clear`、`caution`、`warn`、`block`；`block` 優先於 `warn`。
`caution` 是保留等級，沒有 P0 規則產生它。`clear` 只表示沒有示範規則命中，
不是臨床安全的證據。每張卡包含規則 ID、缺失資料、衝突、說明與草稿。
阻擋卡的確認會被拒絕，案件維持 `awaiting_physician`；仍可駁回或到期。
其他等級允許示範醫師作決定。**任何等級都不執行醫囑。**

## 評估

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

測試鎖定標記為應阻擋的過敏與劑量測試資料、阻擋確認拒絕、僅警告行為與兩種決定、
重放及並行時的冪等、到期、不執行醫囑、確定性和文件一致性。
評估只報告實際測試資料層級的規則命中與工作流程檢查，不聲稱診斷準確率、醫師一致性或延遲。
實際執行結果與 HKT 時間請見[評估方法與結果](../evaluation.md)。

## 本機容器

```bash
docker build -t clinic-agent-lab:local .
docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local
```

容器執行本機 API 和頁面，而不是指令碼示範。除非將本機目錄掛載到 `/app/data`，
否則容器資料是暫時的。映像檔僅為本機使用提供便利，不是正式環境部署。

## 已交付（Shipped）

P0：Python/FastAPI/Pydantic v2、SQLite 狀態機、確定性工具、10 份合成測試資料、
4 條示範規則、安全卡、醫師閘門、HTML 管理頁、真實 HTTP 示範、測試資料評估、
測試、lint、CI 工作流程檔案、本機 Dockerfile 和六種語言文件。
本次實作已在本機驗證；僅有 CI 工作流程檔案不能證明託管 CI 的執行狀態或存在已發布版本。

## Planned（已規劃）

P1/T8 不屬於本次發布：可選的 LLM 文字改寫（不能改變規則決定）、
經授權核對的 Synthea 匯入，以及一個微型合成特徵分類器基線。以上均未實作。
沒有臨床模型訓練、醫院系統整合或醫囑執行介接程式。

## 經驗邊界與免責聲明

作者主要使用 TypeScript/Node 開發後端。Python 經驗包括 Django、FastAPI、py-agents
和個人專案；Python 不是作者日常主要技術棧。作者沒有臨床資料訓練經驗、
醫院系統整合經驗、持牌醫療背景，也沒有與醫師共同開發臨床系統的經驗。
本實驗室展示工作流程 Agent、安全閘門和可重現評估，不能證明臨床專業或已適合臨床使用。

僅使用內建虛構測試資料。不得將輸出用於真實照護、處方、診斷或營運決策。
確認只記錄一項本機示範決定。

## 文件、貢獻與授權

[架構](../architecture.md) · [規則與安全卡](../rules-and-safety.md) ·
[資料與授權](../data-and-license.md) · [安全](../../SECURITY.md) ·
[貢獻](../../CONTRIBUTING.md) · [更新紀錄](../../CHANGELOG.md)

程式碼、原創測試資料和文件均採用 [Apache-2.0](../../LICENSE)，並附有 [NOTICE](../../NOTICE)。
聯絡方式：wpkreg@gmail.com · GitHub：[imwyvern](https://github.com/imwyvern)。
