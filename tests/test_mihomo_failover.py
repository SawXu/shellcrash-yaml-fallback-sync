import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_shell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", "-eu", "-c", script],
        capture_output=True,
        cwd=REPO_ROOT,
        text=True,
    )


class MihomoFailoverTests(unittest.TestCase):
    def test_resolve_active_region_groups_uses_claude_entry_group_by_default(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { :; }
                get_group() {
                    case "$1" in
                        "🤖 AI 平台") printf '%s' '{"now":"🤖 AI 出口"}' ;;
                        "🤖 AI 出口") printf '%s' '{"now":"🇺🇸 美国节点"}' ;;
                        "🚀 节点选择") printf '%s' '{"now":"🇭🇰 香港节点"}' ;;
                        "🇺🇸 美国节点") printf '%s' '{"now":"美国A","all":["美国A","美国B"]}' ;;
                        "🇭🇰 香港节点") printf '%s' '{"now":"香港A","all":["香港A","香港B"]}' ;;
                        *) printf '%s' '{}' ;;
                    esac
                }

                resolve_active_region_groups
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["🇺🇸 美国节点"])

    def test_resolves_region_group_from_entry_chain(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { :; }
                get_group() {
                    case "$1" in
                        "🤖 AI 平台") printf '%s' '{"now":"🚀 节点选择"}' ;;
                        "🚀 节点选择") printf '%s' '{"now":"🇺🇸 美国节点"}' ;;
                        "🇺🇸 美国节点") printf '%s' '{"now":"美国A","all":["美国A","美国B"]}' ;;
                        *) printf '%s' '{}' ;;
                    esac
                }

                resolve_region_group_from_entry "🤖 AI 平台"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "🇺🇸 美国节点")

    def test_resolve_active_region_groups_deduplicates_entries(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { :; }
                ENTRY_GROUPS="🤖 AI 平台
                🚀 节点选择"
                get_group() {
                    case "$1" in
                        "🤖 AI 平台") printf '%s' '{"now":"🚀 节点选择"}' ;;
                        "🚀 节点选择") printf '%s' '{"now":"🇺🇸 美国节点"}' ;;
                        "🇺🇸 美国节点") printf '%s' '{"now":"美国A","all":["美国A","美国B"]}' ;;
                        *) printf '%s' '{}' ;;
                    esac
                }

                resolve_active_region_groups
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["🇺🇸 美国节点"])

    def test_check_group_keeps_current_node_when_claude_is_reachable(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { :; }
                get_group() {
                    printf '%s' '{"now":"美国A","all":["美国A","美国B"]}'
                }
                check_claude_connectivity() {
                    return 0
                }
                switch_node() {
                    printf 'switched:%s\\n' "$2"
                }

                check_group "🇺🇸 美国节点"
                printf 'status:%s\\n' "$?"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["status:0"])

    def test_check_group_switches_until_claude_is_reachable(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { :; }
                SWITCH_WAIT=0
                CURRENT_NODE="美国A"
                get_group() {
                    printf '%s' "{\\\"now\\\":\\\"$CURRENT_NODE\\\",\\\"all\\\":[\\\"美国A\\\",\\\"美国B\\\",\\\"美国C\\\"]}"
                }
                check_claude_connectivity() {
                    [ "$CURRENT_NODE" = "美国C" ]
                }
                switch_node() {
                    CURRENT_NODE="$2"
                    printf 'switched:%s\\n' "$2"
                }

                set +e
                check_group "🇺🇸 美国节点"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                printf 'current:%s\\n' "$CURRENT_NODE"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "switched:美国B",
                "switched:美国C",
                "status:0",
                "current:美国C",
            ],
        )


if __name__ == "__main__":
    unittest.main()
