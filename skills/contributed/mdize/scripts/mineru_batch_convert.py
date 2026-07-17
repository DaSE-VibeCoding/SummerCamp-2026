#!/usr/bin/env python3
"""Convert local documents to Markdown through the MinerU v4 batch API.

Set MINERU_API_TOKEN before use. The script never stores credentials.
"""

import argparse
import os
import sys
import time
import zipfile
from pathlib import Path

import requests


SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"}
API_BASE = "https://mineru.net/api/v4"


def token_from_environment():
    """Return the MinerU token without ever accepting a hard-coded fallback."""
    token = os.environ.get("MINERU_API_TOKEN", "").strip()
    if not token:
        raise ValueError("MINERU_API_TOKEN is required; export it before running this script.")
    return token


def collect_input_files(inputs):
    """Collect supported files from explicit files and non-recursive directories."""
    files = []
    for item in inputs:
        path = Path(item).expanduser()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.iterdir()
                         if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES)
        else:
            print(f"Skip unsupported or missing input: {path}", file=sys.stderr)
    return sorted(set(files), key=lambda file: file.name.lower())


def request_json(method, url, **kwargs):
    response = requests.request(method, url, timeout=60, **kwargs)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (None, 0):
        raise RuntimeError(payload.get("msg") or payload.get("message") or str(payload))
    return payload


def api_headers(token):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


def apply_upload_urls(files, token):
    payload = request_json(
        "POST",
        f"{API_BASE}/file-urls/batch",
        headers=api_headers(token),
        json={"files": [{"name": file.name} for file in files], "model_version": "vlm"},
    )
    data = payload["data"]
    return data["batch_id"], data["file_urls"]


def upload_files(files, upload_urls):
    for file, upload_url in zip(files, upload_urls):
        print(f"Upload: {file.name}")
        with file.open("rb") as handle:
            response = requests.put(upload_url, data=handle, timeout=300)
            response.raise_for_status()


def safe_extract(zip_path, output_dir):
    output_dir = output_dir.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (output_dir / member.filename).resolve()
            if target != output_dir and output_dir not in target.parents:
                raise RuntimeError(f"Unsafe path in archive: {member.filename}")
        archive.extractall(output_dir)


def download_result(zip_url, output_dir, file_name):
    response = requests.get(zip_url, timeout=300)
    response.raise_for_status()
    temporary_zip = output_dir / f".{Path(file_name).stem}.zip"
    temporary_zip.write_bytes(response.content)
    try:
        safe_extract(temporary_zip, output_dir)
    finally:
        temporary_zip.unlink(missing_ok=True)


def poll_and_download(batch_id, token, output_dir, interval):
    downloaded = set()
    while True:
        payload = request_json(
            "GET", f"{API_BASE}/extract-results/batch/{batch_id}", headers=api_headers(token)
        )
        results = payload["data"]["extract_result"]
        finished = 0
        failed = []
        for result in results:
            state = result.get("state")
            if state == "done":
                finished += 1
                file_name = result.get("file_name", "result")
                if file_name not in downloaded and result.get("full_zip_url"):
                    print(f"Download: {file_name}")
                    download_result(result["full_zip_url"], output_dir, file_name)
                    downloaded.add(file_name)
            elif state == "failed":
                finished += 1
                failed.append(result.get("file_name", "unknown file"))
        print(f"Progress: {finished}/{len(results)}")
        if finished == len(results):
            if failed:
                raise RuntimeError("MinerU failed: " + ", ".join(failed))
            return
        time.sleep(interval)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Files or directories to convert")
    parser.add_argument("--output", type=Path, help="Output directory (default: <first input parent>/_md)")
    parser.add_argument("--poll-interval", type=int, default=10, help="Status polling interval in seconds")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        token = token_from_environment()
        files = collect_input_files(args.inputs)
        if not files:
            raise ValueError("No supported files found.")
        output_dir = args.output or files[0].parent / "_md"
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Submit {len(files)} file(s); results will be saved to {output_dir}")
        batch_id, upload_urls = apply_upload_urls(files, token)
        upload_files(files, upload_urls)
        poll_and_download(batch_id, token, output_dir, args.poll_interval)
        print(f"Done: {output_dir}")
    except (ValueError, RuntimeError, requests.RequestException) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
