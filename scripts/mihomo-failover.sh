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
CURL_USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
# ==================================

LOG_TAG="mihomo-failover"

log() {
    logger -t "$LOG_TAG" "$1" 2>/dev/null
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# URL 编码（利用 curl 自身能力，无需 od/hexdump）
urlencode() {
    curl -Gso /dev/null -w '%{url_effective}' --data-urlencode "q=$1" 'http://x' 2>/dev/null | sed 's|http://x/?q=||;s/+/%20/g'
}

# curl 封装：自动附加 secret
api_get() {
    if [ -n "$SECRET" ]; then
        curl -s --connect-timeout 3 -H "Authorization: Bearer $SECRET" "$1"
    else
        curl -s --connect-timeout 3 "$1"
    fi
}

api_put() {
    if [ -n "$SECRET" ]; then
        curl -s --connect-timeout 3 -X PUT \
            -H "Authorization: Bearer $SECRET" \
            -H "Content-Type: application/json" \
            -d "$2" "$1"
    else
        curl -s --connect-timeout 3 -X PUT \
            -H "Content-Type: application/json" \
            -d "$2" "$1"
    fi
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
    text="$1"
    line="$2"

    if [ -n "$text" ]; then
        printf '%s\n%s' "$text" "$line"
    else
        printf '%s' "$line"
    fi
}

check_url_connectivity() {
    url="$1"
    tmpfile="/tmp/mihomo-failover-$$-$(date +%s).html"

    # 确保临时文件总是被清理
    trap 'rm -f "$tmpfile"' EXIT RETURN

    res=$(
        curl -sSL -o "$tmpfile" \
            --connect-timeout "$CURL_CONNECT_TIMEOUT" \
            --max-time "$CURL_MAX_TIME" \
            --proxy "$PROXY_URL" \
            -A "$CURL_USER_AGENT" \
            -w '%{http_code} %{url_effective}' \
            "$url" 2>/dev/null
    ) || return 1

    http_code=$(echo "$res" | cut -d' ' -f1)
    final_url=$(echo "$res" | cut -d' ' -f2)

    # 检查最终 URL 是否包含区域限制关键字
    case "$final_url" in
        *unavailable*|*not-available*|*region-lock*)
            return 1
            ;;
    esac

    # 检查响应体内容（Cloudflare 挑战、区域限制等）
    if [ -f "$tmpfile" ]; then
        content=$(cat "$tmpfile")

        case "$content" in
            *"Just a moment"*|*"challenge-platform"*|*"cf_chl_opt"*|\
            *"app-unavailable-in-region"*|*"not available in your region"*)
                return 1
                ;;
        esac
    fi

    # 状态码判定：200/204 成功，403 若未触发内容检测则视为可用
    case "$http_code" in
        200|204|403)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
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
        if contains_line "$active_groups" "$group"; then
            continue
        fi

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
        log "[${group}] ${target_name} 连通正常，保持当前节点 ${current}"
        return 0
    fi

    log "[${group}] ${target_name} 连通失败，开始切换当前节点 ${current}"
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
        check_group "$group" "$target_name" "$target_url" && {
            IFS=$old_ifs
            return 0
        }
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
