# voice-clone-task

Kaggle Notebook を GitHub 連携（Push/Pull）で管理しているリポジトリ。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `voice-clone-task` / `voice-clone-task-by-T4` | **本体**。拡張子なしだが中身は ipynb（JSON）。Kaggle が Push/Pull で同期する対象 |
| `voice-clone-task.ipynb` / `voice-clone-task-by-T4.ipynb` | 上記のコピー。ローカルでの閲覧・編集、Kaggle の File Import 用 |

Kaggle 連携はファイル名の**完全一致**で紐付いているため、**拡張子なしファイルはリネームしない**こと（連携が壊れる）。

## 編集ルール

- **拡張子なしの本体が「正」**（Kaggle 連携の基準がこちらのため）。
- ノートブックを編集したら、対応する `.ipynb` コピーも同じ内容に揃える
  （例: `cp voice-clone-task voice-clone-task.ipynb`）。厳密な自動同期はしていないので、コミット前に手動で揃える。
- JSON を直接いじるときは構造を壊さないよう注意。整形の推奨形式は
  **インデント付き JSON ＋ 各セルの `source` を行ごとの配列**（Kaggle も読める標準 ipynb）。

## Slack エラー通知

両ノートブックとも `main()` を try/except で囲み、例外時に Slack へトレースバックを通知してから `raise` で終了する。

- Webhook URL は Kaggle Secrets の `webhook_url` から取得（コードに直書きしない）。
- 新しい Notebook にも通知を入れる場合は、既存の `notify_slack()` と同じ形を踏襲する。
