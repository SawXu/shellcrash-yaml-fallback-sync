#!/bin/sh
# mihomo-failover.sh
# 定时检查 Claude 与节点选择当前策略链是否可用，不可用时切换当前命中的地区组节点
# 用法: mihomo-failover.sh
# 建议 cron 每 2 分钟跑一次

# ============ 配置 ============
API_BASE="http://192.168.32.1:9999"
SECRET=""
PROXY_URL="http://192.168.32.1:7890"
CLAUDE_URL="https://claude.ai/"
GOOGLE_URL="https://www.google.com/"
CLAUDE_ENTRY_GROUPS="🤖 AI 平台"
GOOGLE_ENTRY_GROUPS="🚀 节点选择"
CURL_CONNECT_TIMEOUT=5
CURL_MAX_TIME=15
SWITCH_WAIT=1
DEBUG_CONNECTIVITY="${DEBUG_CONNECTIVITY:-1}"
CURL_USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
# 稳定性配置
CHECK_RETRIES=2                    # 单次检查重试次数
RETRY_DELAY=2                      # 重试间隔（秒）
FAIL_THRESHOLD=3                   # 连续失败阈值
STATE_DIR="/tmp/mihomo-failover"   # 状态目录
# ==================================

LOG_TAG="mihomo-failover"

log() {
    logger -t "$LOG_TAG" "$1" 2>/dev/null
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

debug_log() {
    [ "$DEBUG_CONNECTIVITY" = "1" ] || return 0
    log "$1"
}

# URL 编码（利用 curl 自身能力，无需 od/hexdump）
urlencode() {
    curl -Gso /dev/null -w '%{url_effective}' --data-urlencode "q=$1" 'http://x' 2>/dev/null | sed 's|http://x/?q=||;s/+/%20/g'
}

# curl 封装：自动附加 secret
api_request() {
    method="$1"
    url="$2"
    data="$3"

    auth_header=""
    [ -n "$SECRET" ] && auth_header="-H \"Authorization: Bearer $SECRET\""

    if [ "$method" = "GET" ]; then
        eval curl -s --connect-timeout 3 $auth_header "$url"
    else
        eval curl -s --connect-timeout 3 -X "$method" \
            $auth_header \
            -H "\"Content-Type: application/json\"" \
            -d "\"$data\"" "$url"
    fi
}

api_get() {
    api_request "GET" "$1"
}

api_put() {
    api_request "PUT" "$1" "$2"
}

# 获取代理组信息
get_group() {
    api_get "${API_BASE}/proxies/$(urlencode "$1")"
}

# 切换代理组到指定节点
switch_node() {
    api_put "${API_BASE}/proxies/$(urlencode "$1")" "{\"name\":\"$2\"}" >/dev/null
}

# JSON 解析（不依赖 jq）
parse_now() {
    echo "$1" | grep -o '"now":"[^"]*"' | sed 's/"now":"//;s/"$//'
}

parse_all_nodes() {
    echo "$1" | grep -o '"all":\[[^]]*\]' | sed 's/"all":\[//;s/\]$//' | tr ',' '\n' | sed 's/^"//;s/"$//' | sed 's/^ *//;s/ *$//'
}

is_region_group() {
    case "$1" in
        "🇭🇰 香港节点"|"🇹🇼 台湾节点"|"🇯🇵 日本节点"|"🇸🇬 新加坡节点"|"🇺🇸 美国节点")
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

contains_line() {
    text="$1"
    needle="$2"

    [ -n "$text" ] || return 1
    printf '%s\n' "$text" | grep -Fx -- "$needle" >/dev/null 2>&1
}

trim_spaces() {
    printf '%s' "$1" | sed 's/^ *//;s/ *$//'
}

append_line() {
    [ -n "$1" ] && printf '%s\n%s' "$1" "$2" || printf '%s' "$2"
}

is_claude_url() {
    case "$1" in
        https://claude.ai/*|https://www.claude.ai/*) return 0 ;;
        *) return 1 ;;
    esac
}

is_cloudflare_challenge_body() {
    case "$1" in
        *"Just a moment"*|*"challenge-platform"*|*"cf_chl_opt"*|*"Enable JavaScript and cookies to continue"*)
            return 0 ;;
        *) return 1 ;;
    esac
}

is_region_lock_body() {
    case "$1" in
        *"app-unavailable-in-region"*|*"not available in your region"*) return 0 ;;
        *) return 1 ;;
    esac
}

append_csv() {
    [ -n "$1" ] && printf '%s,%s' "$1" "$2" || printf '%s' "$2"
}

detect_connectivity_body_markers() {
    markers=""
    is_region_lock_body "$1" && markers=$(append_csv "$markers" "region-lock")
    is_cloudflare_challenge_body "$1" && markers=$(append_csv "$markers" "cloudflare-challenge")
    printf '%s' "${markers:-none}"
}

finish_connectivity_check() {
    status="$1"
    url="$2"
    http_code="${3:-none}"
    final_url="${4:-none}"
    body_markers="${5:-none}"
    decision="$6"
    tmpfile="$7"

    debug_log "[connectivity] url=$url proxy=$PROXY_URL http_code=$http_code final_url=$final_url body_markers=$body_markers decision=$decision"
    rm -f "$tmpfile"
    return "$status"
}

check_url_connectivity_once() {
    url="$1"
    tmpfile="/tmp/mihomo-failover-$$-$(date +%s).html"
    http_code=""
    final_url=""
    body_markers="none"
    decision="curl-failed"
    status=1

    if ! res=$(
        curl -sSL -o "$tmpfile" \
            --connect-timeout "$CURL_CONNECT_TIMEOUT" \
            --max-time "$CURL_MAX_TIME" \
            --proxy "$PROXY_URL" \
            -A "$CURL_USER_AGENT" \
            -w '%{http_code} %{url_effective}' \
            "$url" 2>/dev/null
    ); then
        finish_connectivity_check 1 "$url" "$http_code" "$final_url" "$body_markers" "$decision" "$tmpfile"
        return $?
    fi

    http_code=$(echo "$res" | cut -d' ' -f1)
    final_url=$(echo "$res" | cut -d' ' -f2)

    # 检查最终 URL 是否包含区域限制关键字
    case "$final_url" in
        *unavailable*|*not-available*|*region-lock*)
            decision="final-url-region-lock"
            finish_connectivity_check 1 "$url" "$http_code" "$final_url" "$body_markers" "$decision" "$tmpfile"
            return $?
            ;;
    esac

    # 检查响应体内容（Cloudflare 挑战、区域限制等）
    if [ -f "$tmpfile" ]; then
        content=$(cat "$tmpfile")
        body_markers=$(detect_connectivity_body_markers "$content")

        if is_region_lock_body "$content"; then
            finish_connectivity_check 1 "$url" "$http_code" "$final_url" "$body_markers" "body-region-lock" "$tmpfile"
            return 1
        fi

        if is_cloudflare_challenge_body "$content"; then
            status=1
            decision="cloudflare-challenge-rejected"
            if is_claude_url "$url" && is_claude_url "$final_url"; then
                status=0
                decision="cloudflare-challenge-accepted"
            fi
            finish_connectivity_check "$status" "$url" "$http_code" "$final_url" "$body_markers" "$decision" "$tmpfile"
            return $?
        fi
    else
        body_markers="body-missing"
    fi

    status=1
    case "$http_code" in
        200|204|403) status=0 ;;
    esac

    finish_connectivity_check "$status" "$url" "$http_code" "$final_url" "$body_markers" "http-$http_code" "$tmpfile"
}

check_url_connectivity() {
    url="$1"

    for i in $(seq 0 $CHECK_RETRIES); do
        [ $i -gt 0 ] && sleep "$RETRY_DELAY"
        check_url_connectivity_once "$url" && return 0
    done

    return 1
}

get_state_file() {
    echo "$STATE_DIR/$(echo "$1" | sed 's/[^a-zA-Z0-9]/_/g').state"
}

get_fail_count() {
    [ -f "$1" ] && cat "$1" || echo 0
}

increment_fail_count() {
    count=$(($(get_fail_count "$1") + 1))
    mkdir -p "$STATE_DIR"
    echo "$count" > "$1"
    echo "$count"
}

reset_fail_count() {
    rm -f "$1"
}

should_trigger_failover() {
    [ "$(get_fail_count "$1")" -ge "$FAIL_THRESHOLD" ]
}

wait_after_switch() {
    [ "$SWITCH_WAIT" -gt 0 ] 2>/dev/null || return 0
    sleep "$SWITCH_WAIT"
}

resolve_region_group_from_entry() {
    entry="$1"
    current="$entry"
    visited=""

    while [ -n "$current" ]; do
        if contains_line "$visited" "$current"; then
            log "[${entry}] 策略链出现循环：${current}"
            return 1
        fi

        visited=$(append_line "$visited" "$current")

        group_json=$(get_group "$current")
        [ -n "$group_json" ] || return 1

        selected=$(parse_now "$group_json")
        [ -n "$selected" ] || return 1

        if is_region_group "$selected"; then
            printf '%s\n' "$selected"
            return 0
        fi

        current="$selected"
    done

    return 1
}

resolve_active_region_groups() {
    entry_groups="${1:-$CLAUDE_ENTRY_GROUPS}"
    active_groups=""
    old_ifs=$IFS
    IFS='
'

    for entry in $entry_groups; do
        entry=$(trim_spaces "$entry")
        [ -n "$entry" ] || continue

        group=$(resolve_region_group_from_entry "$entry") || continue
        contains_line "$active_groups" "$group" && continue

        active_groups=$(append_line "$active_groups" "$group")
    done

    IFS=$old_ifs
    [ -n "$active_groups" ] && printf '%s\n' "$active_groups"
}

format_groups_for_log() {
    printf '%s' "$1" | tr '\n' ',' | sed 's/,$//'
}

check_group() {
    group="$1"
    target_name="${2:-Claude}"
    target_url="${3:-$CLAUDE_URL}"
    state_file=$(get_state_file "$group")

    group_json=$(get_group "$group")
    if [ -z "$group_json" ]; then
        log "[${group}] API 请求失败，跳过"
        return 1
    fi

    current=$(parse_now "$group_json")
    if [ -z "$current" ]; then
        log "[${group}] 无法获取当前节点，跳过"
        return 1
    fi

    if check_url_connectivity "$target_url"; then
        reset_fail_count "$state_file"
        log "[${group}] ${target_name} 连通正常，保持当前节点 ${current}"
        return 0
    fi

    count=$(increment_fail_count "$state_file")
    log "[${group}] ${target_name} 连通失败 (${count}/${FAIL_THRESHOLD})，当前节点 ${current}"

    if ! should_trigger_failover "$state_file"; then
        log "[${group}] 未达到切换阈值，暂不切换"
        return 1
    fi

    log "[${group}] 达到切换阈值，开始尝试其他节点"
    reset_fail_count "$state_file"

    all_nodes=$(parse_all_nodes "$group_json")
    original="$current"
    old_ifs=$IFS
    IFS='
'

    for node in $all_nodes; do
        [ -z "$node" ] && continue
        [ "$node" = "$current" ] && continue

        switch_node "$group" "$node"
        wait_after_switch

        if check_url_connectivity "$target_url"; then
            IFS=$old_ifs
            log "[${group}] 已切换到 ${node}，${target_name} 连通恢复"
            return 0
        fi
    done

    IFS=$old_ifs
    switch_node "$group" "$original"
    wait_after_switch
    log "[${group}] 已尝试所有候选节点，${target_name} 仍不可达，恢复到 ${original}"
    return 1
}

maintain_entry_groups() {
    target_name="$1"
    entry_groups="$2"
    target_url="$3"

    active_groups=$(resolve_active_region_groups "$entry_groups")
    if [ -z "$active_groups" ]; then
        log "未在当前 ${target_name} 策略链中发现地区组，跳过"
        return 0
    fi

    log "当前 ${target_name} 策略链命中的地区组: $(format_groups_for_log "$active_groups")"

    if check_url_connectivity "$target_url"; then
        log "当前 ${target_name} 连通正常，无需切换"
        return 0
    fi

    log "当前 ${target_name} 连通失败，开始维护命中的地区组"

    old_ifs=$IFS
    IFS='
'
    for group in $active_groups; do
        if check_group "$group" "$target_name" "$target_url"; then
            IFS=$old_ifs
            return 0
        fi
    done
    IFS=$old_ifs

    log "已尝试所有命中的地区组，${target_name} 仍不可达"
    return 1
}

main() {
    status=0

    maintain_entry_groups "Claude" "$CLAUDE_ENTRY_GROUPS" "$CLAUDE_URL" || status=1
    maintain_entry_groups "Google" "$GOOGLE_ENTRY_GROUPS" "$GOOGLE_URL" || status=1

    return "$status"
}

if [ "${MIHOMO_FAILOVER_SOURCE_ONLY:-0}" != "1" ]; then
    main "$@"
fi
