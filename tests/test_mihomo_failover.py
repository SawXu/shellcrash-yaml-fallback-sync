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
    def test_check_url_connectivity_enables_debug_logging_by_default(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { printf '%s\\n' "$1"; }
                curl() {
                    output_file=""
                    while [ "$#" -gt 0 ]; do
                        if [ "$1" = "-o" ]; then
                            output_file="$2"
                            shift 2
                            continue
                        fi
                        shift
                    done

                    cat >"$output_file" <<'EOF'
                <!DOCTYPE html>
                <html>
                    <body>ok</body>
                </html>
                EOF
                    printf '200 https://claude.ai/login'
                }

                set +e
                check_url_connectivity "https://claude.ai/"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[connectivity]", result.stdout)
        self.assertIn("decision=http-200", result.stdout)
        self.assertTrue(result.stdout.strip().endswith("status:0"))

    def test_check_url_connectivity_emits_debug_log_for_challenge(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=1 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { printf '%s\\n' "$1"; }
                curl() {
                    output_file=""
                    while [ "$#" -gt 0 ]; do
                        if [ "$1" = "-o" ]; then
                            output_file="$2"
                            shift 2
                            continue
                        fi
                        shift
                    done

                    cat >"$output_file" <<'EOF'
                <!DOCTYPE html>
                <html>
                    <head><title>Just a moment...</title></head>
                    <body>
                        <script>window._cf_chl_opt = {};</script>
                    </body>
                </html>
                EOF
                    printf '403 https://claude.ai/login'
                }

                set +e
                check_url_connectivity "https://claude.ai/"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("http_code=403", result.stdout)
        self.assertIn("final_url=https://claude.ai/login", result.stdout)
        self.assertIn("body_markers=cloudflare-challenge", result.stdout)
        self.assertIn("decision=cloudflare-challenge-accepted", result.stdout)
        self.assertTrue(result.stdout.strip().endswith("status:0"))

    def test_check_url_connectivity_treats_cloudflare_challenge_as_reachable(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=0 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                curl() {
                    output_file=""
                    while [ "$#" -gt 0 ]; do
                        if [ "$1" = "-o" ]; then
                            output_file="$2"
                            shift 2
                            continue
                        fi
                        shift
                    done

                    cat >"$output_file" <<'EOF'
                <!DOCTYPE html>
                <html>
                    <head><title>Just a moment...</title></head>
                    <body>
                        <script>window._cf_chl_opt = {};</script>
                    </body>
                </html>
                EOF
                    printf '403 https://claude.ai/login'
                }

                set +e
                check_url_connectivity "https://claude.ai/"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "status:0")

    def test_check_url_connectivity_handles_403_as_success(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=0 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                curl() {
                    # 模拟返回 403 且没有被弹走
                    printf '403 https://claude.ai/'
                }

                set +e
                check_url_connectivity "https://claude.ai/"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "status:0")

    def test_check_url_connectivity_follows_redirects_successfully(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=0 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                curl() {
                    # 模拟正常重定向到首页
                    printf '200 https://claude.ai/login'
                }

                set +e
                check_url_connectivity "https://claude.ai/"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "status:0")

    def test_check_url_connectivity_fails_on_region_lock_redirect(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=0 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                curl() {
                    # 模拟重定向到不可用页面，即便状态码是 200 也应失败
                    printf '200 https://claude.ai/app-unavailable-in-region'
                }

                set +e
                check_url_connectivity "https://claude.ai/"
                status=$?
                set -e
                printf 'status:%s\\n' "$status"
                """
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "status:1")

    def test_maintains_google_entry_group_with_google_connectivity(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=0 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
                log() { :; }
                SWITCH_WAIT=0
                CURRENT_NODE="香港A"
                get_group() {
                    case "$1" in
                        "🚀 节点选择") printf '%s' '{"now":"🇭🇰 香港节点"}' ;;
                        "🇭🇰 香港节点") printf '%s' "{\\\"now\\\":\\\"$CURRENT_NODE\\\",\\\"all\\\":[\\\"香港A\\\",\\\"香港B\\\",\\\"香港C\\\"]}" ;;
                        *) printf '%s' '{}' ;;
                    esac
                }
                check_url_connectivity() {
                    [ "$1" = "https://www.google.com/" ] && [ "$CURRENT_NODE" = "香港C" ]
                }
                switch_node() {
                    CURRENT_NODE="$2"
                    printf 'switched:%s\\n' "$2"
                }

                set +e
                maintain_entry_groups "Google" "🚀 节点选择" "https://www.google.com/"
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
                "switched:香港B",
                "switched:香港C",
                "status:0",
                "current:香港C",
            ],
        )

    def test_resolve_active_region_groups_uses_claude_entry_group_by_default(self) -> None:
        result = run_shell(
            textwrap.dedent(
                """
                DEBUG_CONNECTIVITY=0 MIHOMO_FAILOVER_SOURCE_ONLY=1 . ./scripts/mihomo-failover.sh
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


if __name__ == "__main__":
    unittest.main()
