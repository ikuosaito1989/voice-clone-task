#!/usr/bin/env python3
"""Kaggle ノートブックを Save & Run All（commit）で実行する。

Kaggle 公式 API を使い、指定した .ipynb を push して
サーバ側でバックグラウンド実行（Save & Run All）させる。

前提:
  1. pip install kaggle
  2. Kaggle の Account → "Create New API Token" で kaggle.json を取得し
     ~/.kaggle/kaggle.json に置く（または環境変数 KAGGLE_USERNAME / KAGGLE_KEY）
  3. 実行対象ノートブックに Secrets（webhook_url など）が
     Kaggle 側でアタッチ済みであること（アタッチはバージョン間で維持される）

使い方:
  python automation/run_notebook.py t4            # by-T4 を実行
  python automation/run_notebook.py t4 --wait     # 完了までポーリング
  python automation/run_notebook.py main --no-gpu  # GPU なしで main を実行
"""
import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Kaggle ユーザ名（kernel の所有者）。GitHub のユーザ名とは別なので注意。
USER = "lahylme"

# エイリアス -> (リポジトリ内の .ipynb ファイル名, Kaggle 上の kernel スラッグ)
# スラッグは Kaggle 側の既存 kernel と完全一致させる（小文字）。ズレると新規 kernel が作られる。
NOTEBOOKS = {
    "t4": ("voice-clone-task-by-T4.ipynb", "voice-clone-task-by-t4"),
    "main": ("voice-clone-task.ipynb", "voice-clone-task"),
}

# 実行完了とみなすステータス（部分一致で判定。enum 表記 KernelWorkerStatus.COMPLETE 等に対応）
TERMINAL = ("complete", "error", "cancel")


def pending_has_items() -> bool:
    """R2 の pending.json を見て処理対象があるか返す。

    R2 認証は環境変数から取る（GitHub Secrets 経由）:
      R2_ACCOUNT_ID / R2_ACCESS_KEY / R2_SECRET_KEY / R2_BUCKET_NAME
    取得に失敗したら「不明」として True を返す（fail-open。取りこぼしを避ける）。
    """
    import os

    import boto3

    try:
        account = os.environ["R2_ACCOUNT_ID"]
        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"],
        )
        res = s3.get_object(Bucket=os.environ["R2_BUCKET_NAME"], Key="pending.json")
        data = json.loads(res["Body"].read().decode("utf-8"))
        return bool(data and data.get("items"))
    except Exception as e:  # noqa: BLE001 - チェック失敗時は起動側に倒す
        print(f"pending チェックに失敗（起動を継続）: {type(e).__name__}: {e}")
        return True


def build_metadata(slug: str, code_file: str, gpu: bool) -> dict:
    return {
        "id": f"{USER}/{slug}",
        "title": slug,
        "code_file": code_file,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": gpu,
        "enable_internet": True,
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": [],
    }


def status_str(st) -> str:
    """KaggleApi のバージョン差（dict / オブジェクト / enum）を吸収して status 名を返す。"""
    if isinstance(st, dict):
        st = st.get("status", st)
    else:
        st = getattr(st, "status", st)
    # "KernelWorkerStatus.COMPLETE" -> "complete"
    return str(st).split(".")[-1].strip().lower()


def main() -> None:
    ap = argparse.ArgumentParser(description="Kaggle ノートブックを Save & Run All で実行")
    ap.add_argument("notebook", choices=NOTEBOOKS, help="実行するノートブック")
    ap.add_argument("--no-gpu", action="store_true", help="GPU を使わない")
    ap.add_argument("--wait", action="store_true", help="完了までステータスをポーリング")
    ap.add_argument(
        "--skip-if-busy",
        action="store_true",
        help="前回の実行がまだ終わっていなければトリガーせずにスキップする",
    )
    ap.add_argument(
        "--skip-if-empty",
        action="store_true",
        help="R2 の pending が 0 件なら Kaggle を起動せずにスキップする",
    )
    args = ap.parse_args()

    # pending が空なら Kaggle を起動しない（GPU クォータを一切使わない）
    if args.skip_if_empty and not pending_has_items():
        print("skip: pending 0件のため Kaggle を起動しません")
        return

    # 認証は import 時ではなく明示的に行う（未設定なら分かりやすく落ちる）
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    repo = Path(__file__).resolve().parent.parent
    code_file, slug = NOTEBOOKS[args.notebook]
    src = repo / code_file
    if not src.exists():
        sys.exit(f"ノートブックが見つかりません: {src}")

    # 実行中なら二重起動しない（前回が終端状態のときだけ走らせる）
    if args.skip_if_busy:
        cur = status_str(api.kernels_status(f"{USER}/{slug}"))
        if not any(t in cur for t in TERMINAL):
            print(f"skip: 前回の実行が未完了のためトリガーしません (status={cur})")
            return
        print(f"前回は終了済み (status={cur}) -> 実行します")

    # kernel-metadata.json + code_file を一時フォルダに用意して push
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(src, tmp / code_file)
        meta = build_metadata(slug, code_file, gpu=not args.no_gpu)
        (tmp / "kernel-metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False)
        )
        print(f"pushing {slug} (gpu={not args.no_gpu}) ...")
        api.kernels_push(str(tmp))

    url = f"https://www.kaggle.com/code/{USER}/{slug}"
    print(f"triggered: {url}")

    if not args.wait:
        return

    print("完了までポーリングします（Ctrl-C で中断）...")
    while True:
        st = status_str(api.kernels_status(f"{USER}/{slug}"))
        print("status:", st)
        if any(t in st for t in TERMINAL):
            sys.exit(0 if "complete" in st else 1)
        time.sleep(15)


if __name__ == "__main__":
    main()
