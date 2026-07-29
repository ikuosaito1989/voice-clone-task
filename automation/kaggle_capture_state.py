#!/usr/bin/env python3
"""Kaggle にログインした状態（cookie 等）を storageState として保存する。

Playwright の UI 自動化（trigger_via_ui.py）で使う認証情報を作る。
ブラウザが開くので、手動で Kaggle にログインし、完了したらターミナルで Enter を押す。

使い方:
  python automation/kaggle_capture_state.py            # kaggle-state.json に保存
  python automation/kaggle_capture_state.py out.json   # 保存先を指定

出力ファイルは Kaggle セッション cookie を含むため秘密情報。リポジトリにコミットせず、
GitHub Secrets 等に入れて使う。cookie は数日〜数週間で失効するので、切れたら取り直す。
"""
import sys

from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else "kaggle-state.json"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.kaggle.com/account/login")

        print("=" * 60)
        print("ブラウザで Kaggle にログインしてください。")
        print("ログインが完了したら、ここで Enter を押してください。")
        print("=" * 60)
        input()

        context.storage_state(path=OUT)
        print(f"保存しました: {OUT}")
        browser.close()


if __name__ == "__main__":
    main()
