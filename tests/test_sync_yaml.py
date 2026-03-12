import json
import unittest

from scripts.sync_yaml import (
    TARGET_NAMES,
    build_upstream_url,
    parse_default_branch_from_ls_remote,
    parse_default_branch,
    transform_content,
)


SOURCE = """#DustinWin-ruleset全分组规则
proxy-groups:
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
    def test_rewrites_region_groups_to_select(self) -> None:
        result = transform_content(SOURCE)

        for name in TARGET_NAMES:
            self.assertIn(f"name: {name}, type: select", result)

        self.assertNotIn("name: 🇭🇰 香港节点, type: url-test", result)
        self.assertNotIn("url: \"https://www.gstatic.com/generate_204\"", result)
        self.assertIn("name: ♻️ 自动选择, type: url-test", result)
        self.assertIn("name: 👑 高级节点, type: url-test", result)

    def test_rewrites_existing_mrs_urls_to_dustinwin_official_release(self) -> None:
        result = transform_content(SOURCE)

        self.assertIn(
            'url: "https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/media.mrs"',
            result,
        )
        self.assertIn(
            'url: "https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/private.mrs"',
            result,
        )
        self.assertNotIn("https://testingcf.jsdelivr.net/gh/DustinWin/ruleset_geodata@mihomo-ruleset/media.mrs", result)

    def test_raises_when_any_region_group_is_missing(self) -> None:
        incomplete = SOURCE.replace(
            '  - {name: 🇺🇸 美国节点, type: url-test, tolerance: 100, include-all: true, filter: "(?i)(🇺🇸|美|us|unitedstates|united states)"}\n',
            "",
        )

        with self.assertRaisesRegex(ValueError, "Missing target groups"):
            transform_content(incomplete)

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
