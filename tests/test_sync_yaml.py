import unittest

from scripts.sync_yaml import TARGET_NAMES, transform_content


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
"""


class TransformContentTests(unittest.TestCase):
    def test_rewrites_region_groups_to_fallback(self) -> None:
        result = transform_content(SOURCE)

        for name in TARGET_NAMES:
            self.assertIn(f"name: {name}, type: fallback", result)

        self.assertNotIn("name: 🇭🇰 香港节点, type: url-test", result)
        self.assertIn('url: "https://www.gstatic.com/generate_204", interval: 600', result)
        self.assertIn("name: ♻️ 自动选择, type: url-test", result)
        self.assertIn("name: 👑 高级节点, type: url-test", result)

    def test_raises_when_any_region_group_is_missing(self) -> None:
        incomplete = SOURCE.replace(
            '  - {name: 🇺🇸 美国节点, type: url-test, tolerance: 100, include-all: true, filter: "(?i)(🇺🇸|美|us|unitedstates|united states)"}\n',
            "",
        )

        with self.assertRaisesRegex(ValueError, "Missing target groups"):
            transform_content(incomplete)


if __name__ == "__main__":
    unittest.main()
