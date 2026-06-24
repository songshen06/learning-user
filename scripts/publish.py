#!/usr/bin/env python3
"""Publish usage guide HTML(s) to the learning-user GitHub Pages repo.

Usage:
  python3 publish.py \\
    --source-dir /path/to/learning-user/out/ \\
    --repo-id "omniverse-dsx-blueprint" \\
    --title "DSX Blueprint" \\
    --desc "NVIDIA Omniverse DSX Blueprint for AI Factory Digital Twins" \\
    [--repo-path /tmp/songshen06-learning-user] \\
    [--no-push]

The source directory should contain .html files (e.g. index.html, index_zh.html).
All .html files are copied into repos/<repo-id>/ on the target repo.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Publish usage guide to learning-user repo")
    parser.add_argument("--source-dir", required=True, help="Path to .learning-user/out/ with HTML files")
    parser.add_argument("--repo-id", required=True, help="Short repo identifier (folder name), e.g. 'omniverse-dsx-blueprint'")
    parser.add_argument("--title", required=True, help="Display title for the guide")
    parser.add_argument("--desc", default="", help="Short description")
    parser.add_argument("--repo-url", default="", help="Original GitHub repo URL (shown on landing page)")
    parser.add_argument("--repo-path", default="/tmp/songshen06-learning-user", help="Local clone of songshen06/learning-user")
    parser.add_argument("--no-push", action="store_true", help="Skip git push (local test)")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.is_dir():
        print(f"ERROR: source-dir not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    html_files = sorted(source_dir.glob("*.html"))
    if not html_files:
        print(f"ERROR: no .html files in {source_dir}", file=sys.stderr)
        sys.exit(1)

    has_en = any(f.name == "index.html" for f in html_files)
    has_zh = any("zh" in f.stem.lower() for f in html_files)

    repo_path = Path(args.repo_path)
    if not (repo_path / ".git").is_dir():
        print(f"ERROR: not a git repo: {repo_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure clean state
    run(["git", "pull", "origin", "main"], str(repo_path))

    # Create target folder
    target_dir = repo_path / "repos" / args.repo_id
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy all HTML files
    copied = []
    for f in html_files:
        dest = target_dir / f.name
        shutil.copy2(f, dest)
        copied.append(f.name)
        print(f"  Copied: {f.name} -> repos/{args.repo_id}/{f.name}")

    # Update repos/index.json
    index_json_path = repo_path / "repos" / "index.json"
    entries = []
    if index_json_path.exists():
        entries = json.loads(index_json_path.read_text())

    # Remove existing entry for this repo-id, then add/update
    entries = [e for e in entries if e.get("id") != args.repo_id]

    timestamp = datetime.now().strftime("%Y-%m-%d")
    entry = {
        "id": args.repo_id,
        "title": args.title,
        "desc": args.desc,
        "has_en": has_en,
        "has_zh": has_zh,
        "files": copied,
        "updated": timestamp
    }
    if args.repo_url:
        entry["repo_url"] = args.repo_url
    entries.insert(0, entry)

    index_json_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    print(f"  Updated: repos/index.json ({len(entries)} entries)")

    # Git operations
    run(["git", "add", "repos", "index.html"], str(repo_path))

    status = run(["git", "status", "--porcelain"], str(repo_path))
    if not status:
        print("No changes to commit.")
        return

    commit_msg = f"publish: {args.title} ({args.repo_id}) [{timestamp}]"
    run(["git", "commit", "-m", commit_msg], str(repo_path))
    commit_hash = run(["git", "rev-parse", "--short", "HEAD"], str(repo_path))
    print(f"  Committed: {commit_hash} — {commit_msg}")

    if not args.no_push:
        run(["git", "push", "origin", "main"], str(repo_path))
        print(f"  Pushed to origin/main")

    # Output summary
    base_url = "https://songshen06.github.io/learning-user"
    print(f"\nPublished:")
    for f in copied:
        print(f"  {base_url}/repos/{args.repo_id}/{f}")
    print(f"  Index: {base_url}/")


if __name__ == "__main__":
    main()