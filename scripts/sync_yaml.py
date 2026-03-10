from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_API_URL = "https://api.github.com/repos/juewuy/ShellCrash"
RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/juewuy/ShellCrash/{branch}/"
    "rules/clash_providers/DustinWin_RS_Full_NoAds.yaml"
)
OUTPUT_PATH = Path("generated/DustinWin_RS_Full_NoAds.yaml")
FALLBACK_URL = "https://www.gstatic.com/generate_204"
FALLBACK_INTERVAL = 600
TARGET_NAMES = (
    "🇭🇰 香港节点",
    "🇹🇼 台湾节点",
    "🇯🇵 日本节点",
    "🇸🇬 新加坡节点",
    "🇺🇸 美国节点",
)


def fetch_text(url: str) -> str:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def parse_default_branch(payload: str) -> str:
    default_branch = json.loads(payload).get("default_branch")
    if not default_branch:
        raise ValueError("default_branch is missing from repository metadata")
    return default_branch


def build_upstream_url(branch: str) -> str:
    return RAW_URL_TEMPLATE.format(branch=branch)


def parse_default_branch_from_ls_remote(output: str) -> str:
    for line in output.splitlines():
        if not line.endswith("\tHEAD"):
            continue
        if not line.startswith("ref: refs/heads/"):
            continue
        return line.removeprefix("ref: refs/heads/").removesuffix("\tHEAD")
    raise ValueError("HEAD default branch is missing from ls-remote output")


def resolve_default_branch() -> str:
    try:
        return parse_default_branch(fetch_text(REPO_API_URL))
    except (HTTPError, URLError, ValueError):
        result = subprocess.run(
            [
                "git",
                "ls-remote",
                "--symref",
                "https://github.com/juewuy/ShellCrash",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return parse_default_branch_from_ls_remote(result.stdout)


def download_upstream() -> str:
    branch = resolve_default_branch()
    return fetch_text(build_upstream_url(branch))


def rewrite_line(line: str) -> str:
    for name in TARGET_NAMES:
        marker = f"name: {name}, type: url-test"
        if marker not in line:
            continue

        prefix, filter_part = line.split(', filter: "', 1)
        filter_value, suffix = filter_part.split('"}', 1)
        rewritten_prefix = prefix.replace("type: url-test, ", "type: fallback, ")
        rewritten_prefix = rewritten_prefix.replace("tolerance: 50, ", "")
        rewritten_prefix = rewritten_prefix.replace("tolerance: 100, ", "")
        return (
            f'{rewritten_prefix}, filter: "{filter_value}", '
            f'url: "{FALLBACK_URL}", interval: {FALLBACK_INTERVAL}'
            f"}}{suffix}"
        )

    return line


def transform_content(content: str) -> str:
    seen = set()
    lines = []

    for line in content.splitlines():
        rewritten = rewrite_line(line)
        for name in TARGET_NAMES:
            if f"name: {name}, type: fallback" in rewritten:
                seen.add(name)
        lines.append(rewritten)

    missing = sorted(set(TARGET_NAMES) - seen)
    if missing:
        raise ValueError(f"Missing target groups: {', '.join(missing)}")

    return "\n".join(lines) + "\n"


def check_output(content: str, output_path: Path = OUTPUT_PATH) -> bool:
    return output_path.exists() and output_path.read_text(encoding="utf-8") == content


def write_output(content: str, output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = transform_content(download_upstream())

    if args.check:
        if not check_output(output):
            raise SystemExit("generated file is out of date")
        return 0

    write_output(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
