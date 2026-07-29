# voice-clone-task

Kaggle Notebook のソースを管理するリポジトリ。
`.ipynb` が唯一の実体で、Kaggle への反映は **`automation/run_notebook.py` の API push** で行う（下記「Kaggle への反映」参照）。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `voice-clone-task.ipynb` | 本番ノートブック（唯一の実体）。編集はこれに対して行う |
| `voice-clone-task-by-T4.ipynb` | T4 GPU 向けノートブック |

> 以前あった拡張子なしファイル（Kaggle の GitHub 連携用）は廃止済み。`.ipynb` が正。

## 編集ルール

- 編集対象は **`.ipynb` ファイルそのもの**。編集したら git push ＋ Kaggle へ反映する。
- JSON を直接いじるときは構造を壊さないよう注意。整形の推奨形式は
  **インデント付き JSON ＋ 各セルの `source` を行ごとの配列**（Kaggle も読める標準 ipynb）。

## Kaggle への反映（Claude Code / Codex 共通）

`.ipynb` を編集しても Kaggle には自動同期されない。反映するには API push する:

```bash
pip install --quiet kaggle          # 未導入なら
python automation/run_notebook.py t4   # by-T4 を反映（main で voice-clone-task.ipynb）
```

- **認証はマシン単位の `~/.kaggle/kaggle.json`**（Kaggle の Settings → API → "Create **Legacy** API Key" で取得）。
  ツール非依存なので、同じマシンで動く Codex でもそのまま使える。環境変数 `KAGGLE_USERNAME` / `KAGGLE_KEY` でも可。
- **反映は pending が 0 件のときに行う**。pending に item があると、その push で走る run は P100 が割り当たり失敗する（ただしコードは version として保存される）。
- Kaggle のユーザ名は `lahylme`（GitHub の `ikuosaito1989` とは別）。kernel は `lahylme/voice-clone-task-by-t4`。
- 定期実行の起動は別系統（Cloudflare Worker cron → GitHub Actions → Playwright で T4 実行）。詳細は `automation/README.md`。

## Slack エラー通知

両ノートブックとも `main()` を try/except で囲み、例外時に Slack へトレースバックを通知してから `raise` で終了する。

- Webhook URL は Kaggle Secrets の `webhook_url` から取得（コードに直書きしない）。
- 新しい Notebook にも通知を入れる場合は、既存の `notify_slack()` と同じ形を踏襲する。

## 生成タイムアウト

`generate_voice_clone()` が 10 分を超えたら `signal.alarm` で `GenerationTimeout` を送出し、その item をスキップ（Slack 通知 ＋ `POST /api/voice_clones/{id}/fail` を呼ぶ ＋ 掃除 ＋ `continue`）。逐次・単一 GPU 前提。
