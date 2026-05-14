import json
import unittest

from scripts.sync_yaml import (
    AI_PLATFORM_GROUP_NAME,
    MANUAL_SELECT_GROUP_NAME,
    build_upstream_url,
    parse_default_branch_from_ls_remote,
    parse_default_branch,
    transform_content,
)


REGION_GROUP_NAMES = (
    "🇭🇰 香港节点",
    "🇹🇼 台湾节点",
    "🇯🇵 日本节点",
    "🇸🇬 新加坡节点",
    "🇺🇸 美国节点",
)


SOURCE = """#DustinWin-ruleset全分组规则
proxy-groups:
  - {name: 🚀 节点选择, type: select, proxies: [♻️ 自动选择, 👉 手动选择, 🇭🇰 香港节点, 🇺🇸 美国节点]}
  - {name: 🤖 AI 平台, type: select, proxies: [🚀 节点选择, 👑 高级节点, 🇭🇰 香港节点, 🇺🇸 美国节点]}
  - {name: 👑 高级节点, type: url-test, tolerance: 50, include-all: true, filter: "(?i)(专线|专用)"}
  - {name: 📉 省流节点, type: url-test, tolerance: 100, include-all: true, filter: "(0\\\\.[1-5]|低倍率)"}
  - {name: ♻️ 自动选择, type: url-test, tolerance: 100, include-all: true}
  - {name: 👉 手动选择, type: select, include-all: true}
  - {name: 🇭🇰 香港节点, type: url-test, tolerance: 50, include-all: true, filter: "(?i)(🇭🇰|港|hk|hongkong|hong kong)"}
  - {name: 🇹🇼 台湾节点, type: url-test, tolerance: 50, include-all: true, filter: "(?i)(🇹🇼|台|tw|taiwan|tai wan)"}
  - {name: 🇯🇵 日本节点, type: url-test, tolerance: 50, include-all: true, filter: "(?i)(🇯🇵|日|jp|japan)"}
  - {name: 🇸🇬 新加坡节点, type: url-test, tolerance: 50, include-all: true, filter: "(?i)(🇸🇬|新|sg|singapore)"}
  - {name: 🇺🇸 美国节点, type: url-test, tolerance: 100, include-all: true, filter: "(?i)(🇺🇸|美|us|unitedstates|united states)"}
rule-providers:
  media:
    type: http
    behavior: domain
    format: mrs
    path: ./ruleset/media.mrs
    url: "https://testingcf.jsdelivr.net/gh/DustinWin/ruleset_geodata@mihomo-ruleset/media.mrs"
    interval: 86400
  private:
    type: http
    behavior: domain
    format: mrs
    path: ./ruleset/private.mrs
    url: "https://testingcf.jsdelivr.net/gh/DustinWin/ruleset_geodata@mihomo-ruleset/private.mrs"
    interval: 86400
"""


class TransformContentTests(unittest.TestCase):
    def test_injects_manual_select_after_node_selection_in_ai_platform(self) -> None:
        result = transform_content(SOURCE)

        self.assertIn(
            f"name: {AI_PLATFORM_GROUP_NAME}, type: select, proxies: [🚀 节点选择, {MANUAL_SELECT_GROUP_NAME}, 👑 高级节点,",
            result,
        )

    def test_preserves_region_groups_as_url_test(self) -> None:
        result = transform_content(SOURCE)

        for name in REGION_GROUP_NAMES:
            self.assertIn(f"name: {name}, type: url-test", result)
            self.assertNotIn(f"name: {name}, type: select", result)

    def test_does_not_duplicate_manual_select_when_already_present(self) -> None:
        already_injected = SOURCE.replace(
            "proxies: [🚀 节点选择, 👑 高级节点, 🇭🇰 香港节点, 🇺🇸 美国节点]",
            "proxies: [🚀 节点选择, 👉 手动选择, 👑 高级节点, 🇭🇰 香港节点, 🇺🇸 美国节点]",
        )

        result = transform_content(already_injected)

        ai_platform_line = next(
            line for line in result.splitlines() if AI_PLATFORM_GROUP_NAME in line
        )
        self.assertEqual(ai_platform_line.count(MANUAL_SELECT_GROUP_NAME), 1)

    def test_rewrites_existing_mrs_urls_to_dustinwin_official_release(self) -> None:
        result = transform_content(SOURCE)

        self.assertIn(
            'url: "https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/media.mrs"',
            result,
        )
        self.assertNotIn(
            "https://testingcf.jsdelivr.net/gh/DustinWin/ruleset_geodata@mihomo-ruleset/media.mrs",
            result,
        )

    def test_raises_when_manual_select_definition_is_missing(self) -> None:
        without_manual_select = SOURCE.replace(
            "  - {name: 👉 手动选择, type: select, include-all: true}\n",
            "",
        )

        with self.assertRaisesRegex(ValueError, "手动选择"):
            transform_content(without_manual_select)

    def test_raises_when_ai_platform_group_is_missing(self) -> None:
        without_ai_platform = SOURCE.replace(
            "  - {name: 🤖 AI 平台, type: select, proxies: [🚀 节点选择, 👑 高级节点, 🇭🇰 香港节点, 🇺🇸 美国节点]}\n",
            "",
        )

        with self.assertRaisesRegex(ValueError, "AI 平台"):
            transform_content(without_ai_platform)

    def test_parses_default_branch_from_repo_metadata(self) -> None:
        payload = json.dumps({"default_branch": "dev"})

        self.assertEqual(parse_default_branch(payload), "dev")

    def test_builds_upstream_url_from_default_branch(self) -> None:
        self.assertEqual(
            build_upstream_url("dev"),
            "https://raw.githubusercontent.com/juewuy/ShellCrash/dev/"
            "rules/clash_providers/DustinWin_RS_Full_NoAds.yaml",
        )

    def test_raises_when_default_branch_is_missing(self) -> None:
        with self.assertRaisesRegex(ValueError, "default_branch"):
            parse_default_branch(json.dumps({"name": "ShellCrash"}))

    def test_parses_default_branch_from_ls_remote_output(self) -> None:
        output = "ref: refs/heads/dev\tHEAD\nabc123\tHEAD\n"

        self.assertEqual(parse_default_branch_from_ls_remote(output), "dev")

    def test_raises_when_ls_remote_head_is_missing(self) -> None:
        with self.assertRaisesRegex(ValueError, "HEAD"):
            parse_default_branch_from_ls_remote("abc123\trefs/heads/dev\n")


if __name__ == "__main__":
    unittest.main()
