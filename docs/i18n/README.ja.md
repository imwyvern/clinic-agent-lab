# clinic-agent-lab

バージョン **0.1.0** · Apache-2.0 · [GitHub: imwyvern](https://github.com/imwyvern)

> **利用範囲：** SYNTHETIC（合成）データ専用。**医療機器ではありません（not a medical device）**。
> 診断、臨床モデルの学習、医療指示の自動実行は行わず、本番システムでもありません。
> 実在する患者のデータを入力しないでください。提案は常に MedicationRequest `draft` のままです。
> デモ医師がワークフロー上の判断を確認しても、医療指示は実行されません。

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

## このプロジェクトの機能

小さな Python ワークフロー実験環境です。決定的なエージェントが架空の患者の概要、検査値、
アレルギー、服薬情報を収集し、フィクスチャで指定された提案の下書きと安全カードを作成します。
認証のない**デモ医師ロール**が判断を確認または却下できます。
ツールの順序制御、永続化、冪等性、安全ゲート、再現可能な評価という工程を示すもので、
診断や治療を選択するものではありません。

P0 には **10 件の合成フィクスチャ**と、**Demo Rule Pack** を構成する
**4 件の独自ルール**が含まれます。短いルールと任意に設定した用量範囲はデモ用のロジックであり、
臨床ガイドラインではありません。リソースは簡略化した FHIR 風 JSON で、
完全な FHIR 実装や相互運用可能な EHR ではありません。

## クイックスタート

Python **3.11+** が必要です。リポジトリのルートで実行してください。
キー、外部モデル、有料サービスは不要です。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m clinic_agent_lab.demo --serve
```

<http://127.0.0.1:8000> を開きます。以下のデモを実行した後も、ローカルサーバーは動作し続けます。
成功の要約が表示された後に Ctrl-C で停止すると、終了コードは 0 です。
既定のデータベースは `.demo/demo.db` です。再実行時には一意な架空の業務キーを使い、履歴を保持します。
ポート 8000 が使用中の場合は `--port 8001` または `--port 0` を指定し、表示されたアドレスを使ってください。

実際の HTTP で管理画面を検証し、その後終了する無人実行のデモ：

```bash
python -m clinic_agent_lab.demo
```

管理画面のアドレスと、保存したケースを再表示するコマンドが出力されます。
検証後にデモのサーバーは停止します。空のローカル API・管理画面を単独で起動することもできます：

```bash
python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000
```

このサーバーは `.demo/clinic.db` を使います。デモの履歴を再表示するには、同じ起動コマンドの前に
`CLINIC_DB_PATH=.demo/demo.db` を設定してください。`.env.example` は設定例です。
アプリは環境変数を読み込みますが、`.env` は自動で読み込みません。
既定値は `CLINIC_CASE_TTL_SECONDS=300` です。有効期限はアクセス時に確認し、バックグラウンド処理はありません。

## デモ手順と API

1. 通常の提案が `awaiting_physician` に進み、デモ医師の確認後、タイムラインは `confirmed` で終わります。
2. ペニシリン系アレルギーで `block` になります。確認は HTTP 409 で拒否されますが、却下は可能です。
3. 必須検査がない場合は `warn` になります。確認と却下の両方を実演します。
4. 同じ `clientCaseId` を再送すると、元のケースと 1 件だけの下書きが返ります。
5. TTL の短いケースが `expired` になり、期限後の確認は HTTP 409 で拒否されます。
6. 一覧・詳細画面、安全カード、永続化されたツール・状態・判断イベントのタイムラインを確認します。

単独のサーバーを起動した状態で、最小の [API サンプル](../../examples/api_demo.py) を実行できます：

```bash
python examples/api_demo.py
```

API：`GET /api/fixtures`、`POST /api/cases`、`GET /api/cases`、
`GET /api/cases/{id}`、`POST /api/cases/{id}/decision`。
作成時に受け付けるのは `clientCaseId` と同梱の `fixture_id` のみで、患者記録のアップロードは受け付けません。
判断には `action`（`confirm`/`reject`）、`role`、`actor`、任意の `reason`（架空の内容のみ）を指定します。
両操作で `physician` ロールが必要です。`observer` は HTTP 403 で拒否されます。
**認証機能や医療資格の確認はありません。** ループバックアドレスにのみバインドしてください。

## 状態機械と安全上の意味

```text
accepted → gathering → drafted → awaiting_physician → confirmed | rejected | expired | failed
```

終了前のどの状態からも `expired` または `failed` へ移行できます。終了状態の再開はできません。
ツールの順序は `get_patient_summary`、`get_labs`、`get_allergies`、`get_medications`、
`draft_order` で固定されています。状態遷移とツール出力は SQLite の `cases`、`events`、`drafts`
に保存します。業務キー `clientCaseId` は一意で、別のフィクスチャに再利用すると 409 を返します。

カードのレベルは `clear`、`caution`、`warn`、`block` で、`block` が `warn` より優先されます。
`caution` は予約されたレベルで、P0 のルールからは生成されません。`clear` はデモルールに該当しなかった
という意味であり、臨床上の安全性の証拠ではありません。各カードにはルール ID、不足データ、競合、
説明、下書きが含まれます。阻止された提案の確認は拒否され、状態は `awaiting_physician` のままです。
その後の却下や期限切れは可能です。他のレベルではデモ医師が判断できます。
**どのレベルでも医療指示を実行しません。**

## 評価

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

テストは、阻止対象とラベル付けしたアレルギー・用量フィクスチャ、阻止された確認の拒否、
警告のみの動作と両判断、再送・並行実行時の冪等性、期限切れ、非実行、決定性、文書の整合性を検証します。
評価が報告するのは、実際のフィクスチャ上のルール該当件数とワークフロー検証だけです。
診断精度、医師との一致率、レイテンシーを主張しません。
HKT 日時を付けた実測結果は[評価方法と結果](../evaluation.md)を参照してください。

## ローカルコンテナ

```bash
docker build -t clinic-agent-lab:local .
docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local
```

スクリプトによるデモではなく、ローカル API と画面を起動します。ローカルディレクトリを
`/app/data` にマウントしない限り、コンテナのデータは一時的です。
利便性のためのローカルイメージであり、本番デプロイではありません。

## 提供済み（Shipped）

P0：Python/FastAPI/Pydantic v2、SQLite 状態機械、決定的ツール、10 件の合成フィクスチャ、
4 件のデモルール、安全カード、医師ゲート、HTML 管理画面、実際の HTTP を使うデモ、
フィクスチャ評価、テスト、lint、CI ワークフローファイル、ローカル Dockerfile、6 言語の文書。
この実装はローカルで検証しました。CI ワークフローファイルだけでは、ホスト型 CI の実行状況や公開済みリリースの存在は確認できません。

## Planned（計画）

P1/T8 は今回のリリース対象外です。任意の LLM による文面だけの書き換え（ルールの判断は変更不可）、
ライセンスを確認した Synthea の取り込み、小規模な合成特徴量の分類器ベースラインを計画しています。
いずれも未実装です。臨床モデルの学習、病院システムとの統合、医療指示の実行アダプターはありません。

## 経験の範囲と免責事項

作者がバックエンド開発で主に使うのは TypeScript/Node です。Python の経験には Django、FastAPI、
py-agents、個人プロジェクトが含まれますが、Python は日常の主力技術ではありません。
臨床データによる学習、病院システムとの統合、医療資格、医師と臨床システムを共同開発した経験はありません。
この実験環境はワークフローエージェント、安全ゲート、再現可能な評価を示すものであり、
臨床の専門性や臨床利用への準備が整っていることを示すものではありません。

同梱の架空のフィクスチャのみを使ってください。実際のケア、処方、診断、運用判断に出力を使わないでください。
確認は、ローカルのデモ上の判断を記録するだけです。

## 文書・貢献・ライセンス

[アーキテクチャ](../architecture.md) · [ルールとカード](../rules-and-safety.md) ·
[データとライセンス](../data-and-license.md) · [セキュリティ](../../SECURITY.md) ·
[貢献方法](../../CONTRIBUTING.md) · [変更履歴](../../CHANGELOG.md)

コード、独自フィクスチャ、文書は [Apache-2.0](../../LICENSE) で提供し、[NOTICE](../../NOTICE) を添付しています。
連絡先：wpkreg@gmail.com · GitHub：[imwyvern](https://github.com/imwyvern)。
