# voice-clone-task

Kaggle Notebook のソースを管理するリポジトリ。
Kaggle への反映は **`.ipynb` を File Import** で行う（GitHub の Push/Pull 連携は使っていない）。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `voice-clone-task.ipynb` | 本番ノートブック（唯一の実体）。編集はこれに対して行う |
| `voice-clone-task-by-T4.ipynb` | T4 GPU 向けノートブック |

> 以前あった拡張子なしファイル（Kaggle の GitHub 連携用）は廃止済み。`.ipynb` が正。

## 編集ルール

- 編集対象は **`.ipynb` ファイルそのもの**。編集したら Kaggle に File Import で読み込ませる。
- JSON を直接いじるときは構造を壊さないよう注意。整形の推奨形式は
  **インデント付き JSON ＋ 各セルの `source` を行ごとの配列**（Kaggle も読める標準 ipynb）。

## Slack エラー通知

両ノートブックとも `main()` を try/except で囲み、例外時に Slack へトレースバックを通知してから `raise` で終了する。

- Webhook URL は Kaggle Secrets の `webhook_url` から取得（コードに直書きしない）。
- 新しい Notebook にも通知を入れる場合は、既存の `notify_slack()` と同じ形を踏襲する。

## 生成タイムアウト

`generate_voice_clone()` が 10 分を超えたら `signal.alarm` で `GenerationTimeout` を送出し、その item をスキップ（Slack 通知 ＋ `POST /api/voice_clones/{id}/fail` を呼ぶ ＋ 掃除 ＋ `continue`）。逐次・単一 GPU 前提。
