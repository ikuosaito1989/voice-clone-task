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

        # headless CI では「ダイアログは閉じたのにコミットされない」ことがあるため、
        # クリックして終わりにせず Kaggle API で RUNNING を確認し、駄目ならリトライする。
        for attempt in range(1, 4):
            _dismiss_cookie_banner(page)
            _click_save_and_run_all(page)
            if _wait_running(slug, timeout_s=120):
                print(f"コミット成功（RUNNING を確認・試行 {attempt}）")
                break
            print(f"RUNNING を確認できませんでした（試行 {attempt}/3）。リロードして再試行。")
            page.reload(wait_until="domcontentloaded")
            page.get_by_role("button", name="Save Version").first.wait_for()
            page.wait_for_timeout(5_000)
        else:
            _fail(page, "3回試しても実行が始まりませんでした")

        _shot(page, "trigger-ok.png")
        browser.close()


def _dismiss_cookie_banner(page) -> None:
    """Cookie 同意バナーを閉じる（残っていると確定ボタンのクリックを奪う）。"""
    for label in ("OK, Got it.", "OK, Got it", "Got it", "Accept"):
        try:
            page.get_by_text(label, exact=False).first.click(timeout=2_500)
            print(f"cookie バナーを閉じた: {label}")
            return
        except PWTimeout:
            continue


def _click_save_and_run_all(page) -> None:
    """Save Version ダイアログを開き、Save & Run All (Commit) で確定する。"""
    page.get_by_role("button", name="Save Version").first.click()
    try:
        page.wait_for_selector("text=Save & Run All (Commit)", timeout=10_000)
    except PWTimeout:
        _fail(page, "VERSION TYPE が Save & Run All になっていません")
    confirm = page.get_by_role("button", name="Save", exact=True)
    if confirm.is_disabled():
        _fail(page, "確定ボタン(Save)が無効です")
    confirm.click()


def _wait_running(slug: str, timeout_s: int) -> bool:
    """Kaggle API で新しい実行が RUNNING/QUEUED になるまで待つ（コミット成功の確認）。"""
    import time

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = api.kernels_status(f"{USER}/{slug}")
        s = str(st.get("status") if isinstance(st, dict) else st).lower()
        if "running" in s or "queued" in s:
            return True
        time.sleep(10)
    return False


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
