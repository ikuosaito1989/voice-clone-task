#!/usr/bin/env python3
"""Kaggle の storageState（cookie）の残り日数を調べ、失効が近ければ警告する。

cookie が切れると trigger_via_ui.py が失敗し、Slack にエラー通知が飛ぶ。
それを「切れる前」に気づけるよう、日次で残り日数をチェックする。

使い方:
  python automation/check_cookie_expiry.py               # 残り日数を表示
  python automation/check_cookie_expiry.py --warn-days 7 # 7日以内なら should_warn=true

storageState の在り処は trigger_via_ui.py と同じルール（環境変数 KAGGLE_STATE_JSON →
KAGGLE_STATE_PATH → kaggle-state.json）。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# 認証の生命線になる cookie。これが切れるとログイン状態を失う。
AUTH_COOKIE = "__Host-KAGGLEID"


def resolve_state_path() -> str:
    """storageState の在り処を返す。CI 用に環境変数からも書き出せる。"""
    env_json = os.environ.get("KAGGLE_STATE_JSON")
    if env_json:
        path = Path("/tmp/kaggle-state.json")
        path.write_text(env_json)
        return str(path)
    return os.environ.get("KAGGLE_STATE_PATH", "kaggle-state.json")


def expires_at(state_path: str) -> tuple[str, datetime]:
    """最初に切れる認証 cookie の (名前, 失効日時) を返す。"""
    state = json.loads(Path(state_path).read_text())
    # expires が -1 の cookie はセッション cookie で、storageState では期限を持たない。
    dated = [c for c in state.get("cookies", []) if (c.get("expires") or -1) > 0]
    if not dated:
        sys.exit("期限付きの cookie が state に入っていません")

    auth = [c for c in dated if c["name"] == AUTH_COOKIE]
    target = min(auth or dated, key=lambda c: c["expires"])
    return target["name"], datetime.fromtimestamp(target["expires"], tz=timezone.utc)


def emit_output(name: str, value: str) -> None:
    """GitHub Actions の step output に書き出す（GITHUB_OUTPUT が無ければ何もしない）。"""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Kaggle cookie の残り日数チェック")
    ap.add_argument(
        "--warn-days",
        type=int,
        default=7,
        help="残りがこの日数以下なら should_warn=true（既定: 7）",
    )
    args = ap.parse_args()

    state_path = resolve_state_path()
    if not Path(state_path).exists():
        sys.exit(f"storageState が見つかりません: {state_path}")

    name, exp = expires_at(state_path)
    days_left = (exp - datetime.now(tz=timezone.utc)).total_seconds() / 86400

    print(f"{name} の失効: {exp.isoformat()}（残り {days_left:.1f} 日）")
    emit_output("days_left", f"{days_left:.1f}")
    emit_output("expires_at", exp.isoformat())
    emit_output("should_warn", "true" if days_left <= args.warn_days else "false")


if __name__ == "__main__":
    main()
