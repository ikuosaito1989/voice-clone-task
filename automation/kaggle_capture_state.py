#!/usr/bin/env python3
"""手動ログインで Kaggle storageState を取得。--upload で GitHub Secret を更新。"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

AUTH_COOKIE = "__Host-KAGGLEID"
REPOSITORY = "ikuosaito1989/voice-clone-task"


def validate_state(state: dict) -> float:
    """Kaggle の有効な認証 cookie がなければ更新しない。値は表示しない。"""
    cookies = [
        c for c in state.get("cookies", [])
        if c.get("name") == AUTH_COOKIE
        and c.get("domain", "").lstrip(".") in ("kaggle.com", "www.kaggle.com")
        and c.get("value")
        and c.get("expires", 0) > time.time()
    ]
    if not cookies:
        raise ValueError("有効な Kaggle 認証 cookie がありません。ログインを完了して取り直してください。")
    return min(c["expires"] for c in cookies)


def upload_state(state: dict, repository: str) -> None:
    # JSON はコマンド引数・ログ・一時ファイルに出さず stdin で渡す。
    subprocess.run(
        ["gh", "secret", "set", "KAGGLE_STATE_JSON", "--repo", repository],
        input=json.dumps(state), text=True, check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", nargs="?", help="保存先（通常時の既定: kaggle-state.json）")
    ap.add_argument("--upload", action="store_true", help="GitHub Secret を更新。既定ではローカル保存しない")
    ap.add_argument("--repo", default=REPOSITORY, help="Secret の更新先 owner/repo")
    args = ap.parse_args()
    if args.upload:
        if not shutil.which("gh"):
            ap.error("GitHub CLI (gh) をインストールしてください")
        subprocess.run(["gh", "auth", "status"], check=True, capture_output=True)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.kaggle.com/account/login")
            print("ブラウザで Kaggle（lahylme）にログインしてください。")
            print("Codespaces: Ports の Desktop (6080) を開くとブラウザを操作できます。")
            input("ログイン完了後、このターミナルで Enter: ")
            state = context.storage_state()
            expiry = validate_state(state)
            print(f"認証 cookie を確認しました（残り {(expiry - time.time()) / 86400:.1f} 日）。")
            if args.upload:
                upload_state(state, args.repo)
                print(f"{args.repo} の KAGGLE_STATE_JSON を更新しました。")
            if args.output or not args.upload:
                output = Path(args.output or "kaggle-state.json")
                fd = os.open(output, os.O_WRONLY | os.O_CREAT, 0o600)
                with os.fdopen(fd, "w") as f:
                    os.fchmod(f.fileno(), 0o600)
                    f.truncate(0)
                    json.dump(state, f)
                print(f"保存しました: {output}（秘密情報のためコミットしないでください）")
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from None
