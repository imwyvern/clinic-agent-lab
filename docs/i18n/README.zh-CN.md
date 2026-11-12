# clinic-agent-lab

版本 **0.1.0** · Apache-2.0 · [GitHub: imwyvern](https://github.com/imwyvern)

> **诚实边界：** 仅限 SYNTHETIC 合成数据；**不是医疗器械（not a medical device）**。
> 不做诊断、不训练临床模型、不自动执行医嘱，也不是生产系统。
> 切勿输入真实患者数据。所有建议始终是 MedicationRequest `draft`，
> 即使演示医师确认工作流决定，也不会改变这一点。

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

## 项目做什么

这是一个小型 Python 工作流实验室：确定性 Agent 收集虚构患者的摘要、化验、过敏和用药信息，
起草夹具预设的建议，并生成安全卡。未经身份认证的**演示医师角色**可以确认或驳回决定。
项目展示工具编排、持久化、幂等、安全门禁和可复现评测等工程方法，不选择诊断或治疗方案。

P0 交付 **10 份合成夹具**和 **4 条自行编写的规则**，组成 **Demo Rule Pack**。
这些短规则和任意设定的演示剂量边界只是演示逻辑，不是临床指南。
资源是简化的 FHIR 风格 JSON，不是完整 FHIR 实现，也不是可互操作的 EHR。

## 快速开始

需要 Python **3.11+**；在仓库根目录运行以下命令。无需密钥、外部模型或付费服务。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m clinic_agent_lab.demo --serve
```

打开 <http://127.0.0.1:8000>。演示完成下述流程后，会保持本地服务运行。
显示成功摘要后按 Ctrl-C 停止，退出码为 0。默认数据库是 `.demo/demo.db`；
重复运行会使用唯一的虚构业务键，并保留历史。若端口 8000 被占用，可使用
`--port 8001` 或 `--port 0`，以终端打印的地址为准。

无人值守演示会通过真实 HTTP 检查管理页面，然后自行退出：

```bash
python -m clinic_agent_lab.demo
```

命令打印管理页地址及重新打开已保存案件的命令；检查完成后，演示服务随即停止。
也可以单独启动一个初始为空的本地 API 和管理页服务：

```bash
python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000
```

该服务使用 `.demo/clinic.db`。若要重新查看演示历史，在同一服务命令前设置
`CLINIC_DB_PATH=.demo/demo.db`。`.env.example` 提供配置示例；应用读取环境变量，
不会自动加载 `.env`。默认 `CLINIC_CASE_TTL_SECONDS=300`；访问时检查过期，
没有后台任务。

## 演示步骤与 API

1. 正常建议进入 `awaiting_physician`；演示医师确认后，时间线结束于 `confirmed`。
2. 青霉素类过敏产生 `block`；确认返回 HTTP 409，案件仍可驳回。
3. 缺少指定化验产生 `warn`；演示确认和驳回两条路径。
4. 重放同一 `clientCaseId`；返回原案件和唯一一份草稿。
5. 短 TTL 案件进入 `expired`；过期后确认返回 HTTP 409。
6. 查看列表、详情、安全卡，以及持久化的工具、状态和决定事件时间线。

单独运行服务后，最小 [API 示例](../../examples/api_demo.py) 对应以下命令：

```bash
python examples/api_demo.py
```

API：`GET /api/fixtures`、`POST /api/cases`、`GET /api/cases`、
`GET /api/cases/{id}`、`POST /api/cases/{id}/decision`。
创建接口仅接受 `clientCaseId` 和内置 `fixture_id`，不接受患者记录上传。
决定接口接受 `action`（`confirm`/`reject`）、`role`、`actor` 和可选的 `reason`
（仅限虚构内容）。两种操作都要求角色为 `physician`；`observer` 返回 HTTP 403。
**没有身份认证**或经核验的医疗身份。请仅绑定本地回环地址。

## 状态机与安全语义

```text
accepted → gathering → drafted → awaiting_physician → confirmed | rejected | expired | failed
```

任何非终态都可以进入 `expired` 或 `failed`。终态不可重新打开。
工具顺序固定为 `get_patient_summary`、`get_labs`、`get_allergies`、
`get_medications`、`draft_order`。状态转移和工具输出保存在 SQLite 的
`cases`、`events`、`drafts` 表中。业务键 `clientCaseId` 唯一；
将同一业务键用于另一夹具会返回 409。

安全卡级别为 `clear`、`caution`、`warn`、`block`；`block` 优先于 `warn`。
`caution` 是保留级别，没有 P0 规则产生它。`clear` 只表示没有演示规则命中，
不是临床安全的证据。每张卡包含规则 ID、缺失数据、冲突、说明和草稿。
阻断卡的确认会被拒绝，案件保持 `awaiting_physician`；仍可驳回或过期。
其他级别允许演示医师作决定。**任何级别都不执行医嘱。**

## 评测

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

测试锁定标注为应阻断的过敏和剂量夹具、阻断确认拒绝、仅警告行为及两种决定、
重放和并发下的幂等、过期、不执行医嘱、确定性和文档一致性。
评测只报告实际夹具级规则命中及工作流检查，不声称诊断准确率、医师一致性或时延。
实际运行结果和 HKT 时间见[评测方法与结果](../evaluation.md)。

## 本地容器

```bash
docker build -t clinic-agent-lab:local .
docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local
```

容器运行本地 API 和页面，而不是脚本演示。除非将本地目录挂载到 `/app/data`，
否则容器数据是临时的。镜像仅为本地使用提供便利，不是生产部署。

## 已交付（Shipped）

P0：Python/FastAPI/Pydantic v2、SQLite 状态机、确定性工具、10 份合成夹具、
4 条演示规则、安全卡、医师门禁、HTML 管理页、真实 HTTP 演示、夹具评测、
测试、lint、CI 工作流文件、本地 Dockerfile 和六种语言文档。
本次实现已在本地验证；仅有 CI 工作流文件不能证明托管 CI 的运行状态或存在已发布版本。

## Planned（已规划）

P1/T8 不属于本次发布：可选的 LLM 文案改写（不能改变规则决定）、
经许可核验的 Synthea 导入，以及一个微型合成特征分类器基线。以上均未实现。
没有临床模型训练、医院系统集成或医嘱执行适配器。

## 经验边界与免责声明

作者主要使用 TypeScript/Node 开发后端。Python 经验包括 Django、FastAPI、py-agents
和个人项目；Python 不是作者日常主力技术栈。作者没有临床数据训练经验、
医院系统集成经验、持牌医疗背景，也没有与医师共同开发临床系统的经验。
本实验室展示工作流 Agent、安全门禁和可复现评测，不能证明临床专长或临床使用就绪。

仅使用内置虚构夹具。不得将输出用于真实照护、处方、诊断或运营决策。
确认只记录一项本地演示决定。

## 文档、贡献与许可

[架构](../architecture.md) · [规则与安全卡](../rules-and-safety.md) ·
[数据与许可](../data-and-license.md) · [安全](../../SECURITY.md) ·
[贡献](../../CONTRIBUTING.md) · [更新日志](../../CHANGELOG.md)

代码、原创夹具和文档均采用 [Apache-2.0](../../LICENSE)，并附有 [NOTICE](../../NOTICE)。
联系方式：wpkreg@gmail.com · GitHub：[imwyvern](https://github.com/imwyvern)。
