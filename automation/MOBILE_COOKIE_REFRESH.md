# iPhone / PC で Kaggle cookie を更新する

iPhone の Safari から GitHub Codespaces のデスクトップを開き、Kaggle に手動ログインする。
PC を起動しておく必要はない。Kaggle のパスワードや cookie を ChatGPT に貼る必要もない。
Codespaces の利用には GitHub アカウントと利用枠が必要（無料枠超過時は課金される）。

## 初回・更新時

1. [Codespaces を作成](https://codespaces.new/ikuosaito1989/voice-clone-task) し、準備が終わるまで待つ。
   この設定を追加した PR を試す場合は、作成画面で **codex/mobile-kaggle-cookie-refresh** ブランチを選ぶ。
   既存の Codespace では、このブランチを取得して **Rebuild Container** を実行する。
2. iPhone は Safari の「デスクトップ用Webサイトを表示」を使い、横向きにすると操作しやすい。
3. Codespaces の Terminal（メニュー → Terminal → New Terminal）で実行:

   ```bash
   python automation/kaggle_capture_state.py --upload
   ```

4. **Ports** タブの **6080 / Desktop — Kaggle login** をブラウザで開く。
   ポートの公開範囲は **Private** のままにする。接続画面で Connect を押し、
   パスワードを求められたら desktop-lite の既定値 `vscode` を入力する。
5. 遠隔デスクトップ内の Chromium で Kaggle にログインする。
   既存の実行アカウント **lahylme** を使う。認証や CAPTCHA があれば自分で完了する。
   Google ログインが自動化ブラウザを拒否する場合は、Kaggle が提供するメールログインを使う。
6. 元の Codespaces のターミナルに戻り **Enter** を押す。
   「KAGGLE_STATE_JSON を更新しました」が出れば完了。`--upload` のみなら cookie ファイルは残らない。
7. [cookie チェックの Actions](https://github.com/ikuosaito1989/voice-clone-task/actions/workflows/check-kaggle-cookie.yml)
   で **Run workflow** を実行し、新しい有効期限を確認する。これは期限の確認であり、Notebook の起動テストではない。
8. 終了後、[Codespaces 一覧](https://github.com/codespaces)から停止・削除する。

## Secret 更新で権限エラーになる場合

Codespaces の自動トークンには Actions Secrets の書き込み権限がないことがある。
その場合はターミナルで次を実行し、表示された GitHub の URL とコードで本人認証する。
認証に使ったアカウントはリポジトリの Secret を更新できる権限が必要。

```bash
env -u GH_TOKEN -u GITHUB_TOKEN gh auth login --hostname github.com --web --scopes repo
env -u GH_TOKEN -u GITHUB_TOKEN python automation/kaggle_capture_state.py --upload
```

再ログインせずに更新を再試行したい場合は、最初からファイル保存も指定できる:

```bash
python automation/kaggle_capture_state.py kaggle-state.json
# 以下も上記と同じ GitHub 本人認証を済ませてから実行する
env -u GH_TOKEN -u GITHUB_TOKEN gh secret set KAGGLE_STATE_JSON --repo ikuosaito1989/voice-clone-task < kaggle-state.json
rm kaggle-state.json
```

Cookie ファイルはアカウントの認証情報。コミット、Issue、チャットには貼らない。

## ローカル PC

GUI のある PC でも同じスクリプトが使える:

```bash
python -m pip install playwright==1.58.0
python -m playwright install chromium
gh auth login
python automation/kaggle_capture_state.py --upload
```

従来どおり `python automation/kaggle_capture_state.py` だけなら `kaggle-state.json` に保存する。
GUI や操作用デスクトップのないチャット実行環境では手動ログインを完結できないため、
上記 Codespaces または PC を使う。Kaggle がクラウドからのログインを拒否する場合も PC から取得する。
