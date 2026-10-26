# automation

Kaggle ノートブックを **Kaggle 公式 API** で Save & Run All（commit）実行するスクリプト。
ブラウザ自動化（Playwright 等）は使わない。

## セットアップ

```bash
# 1) Kaggle API クライアント
pip install kaggle

# 2) API トークン
#    Kaggle → 右上アイコン → Settings → API → "Create New API Token"
#    ダウンロードした kaggle.json を配置
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json
```

環境変数でも可（CI 等）:

```bash
export KAGGLE_USERNAME=lahylme   # Kaggle のユーザ名（GitHub の ikuosaito1989 とは別）
export KAGGLE_KEY=xxxxxxxxxxxxxxxx
```

> トークンは Kaggle の Settings → API → **「Legacy API Credentials」→「Create Legacy API Key」** で
> ダウンロードされる `kaggle.json`（`username` と `key` 入り）を使う。
> 新しい「Create New API Token」は OAuth 用（`access_token`）で、このスクリプトでは使えない。

## 使い方

```bash
python automation/run_notebook.py t4          # voice-clone-task-by-T4 を実行
python automation/run_notebook.py t4 --wait   # 完了までポーリング
python automation/run_notebook.py main --no-gpu
```

- `t4` → `voice-clone-task-by-T4.ipynb`、`main` → `voice-clone-task.ipynb`
- push すると Kaggle サーバ側でバックグラウンド実行される。ローカルは閉じてよい。

## cookie の失効チェック

UI 経由の実行（`trigger_via_ui.py`）に使う `kaggle-state.json` の cookie は 2〜4 週間で失効する。
切れてから気づくと自動実行が止まるので、`.github/workflows/check-kaggle-cookie.yml` が
日次（JST 09:00）で残り日数を見て、**7 日以内なら Slack に予告**する。

```bash
python automation/check_cookie_expiry.py --warn-days 7   # 手元でも確認できる
```

iPhone から更新する場合は [Codespaces での更新手順](MOBILE_COOKIE_REFRESH.md) を使う。
PC でも `python automation/kaggle_capture_state.py --upload` で取得から Secret 更新まで実行できる。

従来のファイル経由で更新する場合:

```bash
python automation/kaggle_capture_state.py
gh secret set KAGGLE_STATE_JSON < kaggle-state.json
```

## 前提・注意

- **Secrets**: 実行対象ノートブックに `webhook_url` などの Secrets が Kaggle 側でアタッチ済みであること（アタッチはバージョン間で維持される）。
- **GPU 種別**: メタデータでは `enable_gpu` の on/off しか指定できず、**T4 など機種の指定はできない**。機種にこだわる場合は Kaggle UI 側で確認・設定する。
- **認証は 2 層**: このスクリプトの認証は `kaggle.json`（Kaggle 実行のため）。ノートブックが `neglegere.com` にログインするのは従来どおりノートブック内の Kaggle Secrets で行われる。
