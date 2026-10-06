# voice-clone-task

Kaggle Notebook 上で動くボイスクローン（音声合成）バッチ処理。
`neglegere.com` の API と Cloudflare R2 の処理キューを見て、未処理のリクエストを
[Qwen3-TTS](https://huggingface.co/Qwen) でクローン音声に変換し、結果をアップロードする。

Kaggle への反映は `.ipynb` を **File Import** で読み込ませる（GitHub の Push/Pull 連携は使っていない）。

## リポジトリ構成

| ファイル | 役割 |
|---|---|
| `voice-clone-task.ipynb` | 本番ノートブック（唯一の実体） |
| `voice-clone-task-by-T4.ipynb` | T4 GPU 向けノートブック |
| `AGENTS.md` | AI エージェント（Codex / Claude Code）向けの作業ルール。`CLAUDE.md` はここへのポインタ |

## 処理フロー

```
R2 の pending.json を取得
      ↓（未処理 item ごとに）
neglegere.com にログイン → start API で生成中に更新
      ↓（先に開始済みならスキップ）
pending.json から除外 → 参照音声をダウンロード
      ↓
Qwen3-TTS でクローン音声を生成
      ↓
生成結果を neglegere.com にアップロード（complete）
      ↓
作業ディレクトリを掃除して次の item へ
```

主なセル：

- **cell 0** … Secrets 読み込み、定数定義、`notify_slack()`
- **cell 1** … `generate_qwen_voice()`（Qwen3-TTS での音声生成）
- **cell 2** … `neglegere.com` API クライアント（login / pending / start / download / upload）
- **cell 3** … R2 から pending キューを取得
- **cell 4** … `main()` メインループ

## 必要な Kaggle Secrets

Kaggle の **Add-ons → Secrets** に以下を登録し、Notebook にアタッチする。

| ラベル | 用途 |
|---|---|
| `email` / `password` | neglegere.com ログイン |
| `hf_token` | Hugging Face（モデル取得） |
| `r2_AccountID` / `r2_accesskey` / `r2_secretkey` / `r2_bucket_name` | Cloudflare R2 |
| `webhook_url` | Slack Incoming Webhook（エラー通知先） |

## エラーハンドリング

- **Slack 通知**: `main()` を try/except で囲み、例外発生時はトレースバックを Slack に通知してから `raise` で終了する。Webhook URL は Secrets の `webhook_url` から取得。
- **生成タイムアウト**: `generate_voice_clone()` が **10 分**を超えた場合、`signal.alarm` で `GenerationTimeout` を送出し、その item をスキップして次へ進む（ループは継続）。スキップ時は Slack に通知し、`POST /api/voice_clones/{id}/fail` を呼んで失敗を記録する。
  - 逐次・単一 GPU 前提の実装。並列（複数スレッド）化する場合は signal 方式は使えないため要変更。

## 開発・運用メモ

- 編集対象は `.ipynb` ファイルそのもの。編集後、Kaggle に File Import で読み込ませる。
- JSON を直接編集するときは構造を壊さないよう注意。推奨整形はインデント付き JSON ＋ 各セルの `source` を行ごとの配列。

詳細な作業ルールは [AGENTS.md](./AGENTS.md) を参照。

