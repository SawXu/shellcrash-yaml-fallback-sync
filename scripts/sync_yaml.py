from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_API_URL = "https://api.github.com/repos/juewuy/ShellCrash"
RAW_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/juewuy/ShellCrash/{branch}/"
    "rules/clash_providers/DustinWin_RS_Full_NoAds.yaml"
)
OUTPUT_PATH = Path("generated/DustinWin_RS_Full_NoAds.yaml")
OFFICIAL_MRS_BASE_URL = (
    "https://github.com/DustinWin/ruleset_geodata/releases/download/"
    "mihomo-ruleset"
)
AI_PLATFORM_GROUP_NAME = "🤖 AI 平台"
MANUAL_SELECT_GROUP_NAME = "👉 手动选择"
AI_PLATFORM_PROXIES_PREFIX = (
    f"name: {AI_PLATFORM_GROUP_NAME}, type: select, proxies: [🚀 节点选择,"
)
MRS_URL_PATTERN = re.compile(
    r'https://[^"]*/DustinWin/ruleset_geodata@[^"/]+/(?P<filename>[^"/]+\.mrs)'
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


def rewrite_mrs_url(line: str) -> str:
    def replace(match: re.Match[str]) -> str:
        filename = match.group("filename")
        return f"{OFFICIAL_MRS_BASE_URL}/{filename}"

    return MRS_URL_PATTERN.sub(replace, line)


def inject_manual_select_into_ai_platform(line: str) -> str:
    if AI_PLATFORM_PROXIES_PREFIX not in line:
        return line
    if MANUAL_SELECT_GROUP_NAME in line:
        return line
    return line.replace(
        f"{AI_PLATFORM_PROXIES_PREFIX} ",
        f"{AI_PLATFORM_PROXIES_PREFIX} {MANUAL_SELECT_GROUP_NAME}, ",
        1,
    )


def rewrite_line(line: str) -> str:
    return inject_manual_select_into_ai_platform(rewrite_mrs_url(line))


def transform_content(content: str) -> str:
    rewritten = "\n".join(rewrite_line(line) for line in content.splitlines()) + "\n"

    if f"name: {MANUAL_SELECT_GROUP_NAME}, type: select" not in rewritten:
        raise ValueError(
            f"Upstream is missing the {MANUAL_SELECT_GROUP_NAME} group definition"
        )

    if f"{AI_PLATFORM_PROXIES_PREFIX} {MANUAL_SELECT_GROUP_NAME}," not in rewritten:
        raise ValueError(
            f"Failed to inject {MANUAL_SELECT_GROUP_NAME} into {AI_PLATFORM_GROUP_NAME} proxies"
        )

    return rewritten


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
