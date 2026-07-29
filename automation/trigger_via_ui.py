#!/usr/bin/env python3
"""Kaggle の Notebook エディタを Playwright で操作し「Save & Run All (Commit)」を実行する。

API push だと GPU 機種を選べず P100 が割り当たり失敗するため、UI 経由で実行して
ノートブックに保存された T4 設定・Secrets をそのまま使う。

前提:
  - storageState（kaggle_capture_state.py で作成）が必要。
    ローカル: kaggle-state.json / CI: 環境変数 KAGGLE_STATE_JSON の中身を書き出す。
  - pip install playwright && playwright install chromium

使い方:
  python automation/trigger_via_ui.py t4
  HEADLESS=0 python automation/trigger_via_ui.py t4   # 画面を見ながらデバッグ
"""
import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

USER = "lahylme"
NOTEBOOKS = {
    "t4": "voice-clone-task-by-t4",
    "main": "voice-clone-task",
}


def resolve_state_path() -> str:
    """storageState の在り処を返す。CI 用に環境変数からも書き出せる。"""
    env_json = os.environ.get("KAGGLE_STATE_JSON")
    if env_json:
        path = Path("/tmp/kaggle-state.json")
        path.write_text(env_json)
        return str(path)
    return os.environ.get("KAGGLE_STATE_PATH", "kaggle-state.json")


def main() -> None:
    ap = argparse.ArgumentParser(description="Kaggle UI 経由で Save & Run All を実行")
    ap.add_argument("notebook", choices=NOTEBOOKS)
    args = ap.parse_args()

    slug = NOTEBOOKS[args.notebook]
    state_path = resolve_state_path()
    if not Path(state_path).exists():
        sys.exit(f"storageState が見つかりません: {state_path}")

    headless = os.environ.get("HEADLESS", "1") != "0"
    edit_url = f"https://www.kaggle.com/code/{USER}/{slug}/edit"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(storage_state=state_path)
        page = context.new_page()
        page.set_default_timeout(60_000)

        print(f"open: {edit_url}")
        page.goto(edit_url, wait_until="domcontentloaded")

        # ログインが切れていると /edit がログイン画面へ飛ぶ
        if "login" in page.url.lower():
            _fail(page, "未ログイン（storageState 失効の可能性）。cookie を取り直してください。")

        # エディタ描画待ち
        page.get_by_role("button", name="Save Version").first.wait_for()
        page.wait_for_timeout(5_000)

        # 0) Cookie 同意バナーを閉じる（残っていると確定ボタンのクリックを奪う）
        for label in ("OK, Got it.", "OK, Got it", "Got it", "Accept"):
            try:
                page.get_by_text(label, exact=False).first.click(timeout=2_500)
                print(f"cookie バナーを閉じた: {label}")
                break
            except PWTimeout:
                continue

        # 1) Save Version ダイアログを開く
        page.get_by_role("button", name="Save Version").first.click()

        # 2) VERSION TYPE が "Save & Run All (Commit)"（既定）であることを確認。
        #    もし Quick Save になっていたら実行されないので、その場合は明示的に選び直す。
        try:
            page.wait_for_selector("text=Save & Run All (Commit)", timeout=10_000)
        except PWTimeout:
            _fail(page, "VERSION TYPE が Save & Run All になっていません")

        # 3) 確定（accessible name がちょうど "Save" のボタンは確定ボタン1つだけ）
        confirm = page.get_by_role("button", name="Save", exact=True)
        if confirm.is_disabled():
            _fail(page, "確定ボタン(Save)が無効です")
        confirm.click()

        # 4) ダイアログ(「Save version」ヘッダ)が閉じたらコミット受理とみなす
        try:
            page.get_by_role("heading", name="Save version").wait_for(
                state="hidden", timeout=30_000
            )
            print("Save & Run All を受理しました（ダイアログが閉じた）")
        except PWTimeout:
            _fail(page, "ダイアログが閉じませんでした（確定に失敗した可能性）")

        _shot(page, "trigger-ok.png")
        browser.close()


def _shot(page, name: str) -> None:
    out = os.environ.get("SHOT_DIR", ".")
    try:
        page.screenshot(path=str(Path(out) / name), full_page=False)
        print(f"screenshot: {name}")
    except Exception as e:  # noqa: BLE001
        print("screenshot 失敗:", e)


def _fail(page, msg: str):
    _shot(page, "trigger-fail.png")
    sys.exit(f"FAILED: {msg}")


if __name__ == "__main__":
    main()
