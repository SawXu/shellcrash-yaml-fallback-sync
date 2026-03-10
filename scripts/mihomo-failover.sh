#!/bin/sh
# mihomo-failover.sh
# 定时检查 select 组当前节点是否可用，挂了自动切到下一个可用节点
# 用法: mihomo-failover.sh
# 建议 cron 每 2 分钟跑一次

# ============ 配置 ============
API_BASE="http://192.168.32.1:9999"
SECRET=""
TEST_URL="https://www.gstatic.com/generate_204"
TIMEOUT=3000
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

# 测试节点延迟，返回延迟 ms 或空
test_delay() {
    _resp=$(api_get "${API_BASE}/proxies/$(urlencode "$1")/delay?timeout=${TIMEOUT}&url=${TEST_URL}")
    echo "$_resp" | grep -o '"delay":[0-9]*' | grep -o '[0-9]*'
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

# 检查单个代理组
check_group() {
    group="$1"

    group_json=$(get_group "$group")
    if [ -z "$group_json" ]; then
        log "[${group}] API 请求失败，跳过"
        return
    fi

    current=$(parse_now "$group_json")
    if [ -z "$current" ]; then
        log "[${group}] 无法获取当前节点，跳过"
        return
    fi

    # 测试当前节点
    delay=$(test_delay "$current")
    if [ -n "$delay" ]; then
        log "[${group}] ${current} 正常 (${delay}ms)"
        return
    fi

    # 当前节点不可用，测试所有节点找延迟最低的
    log "[${group}] ${current} 不可用，测试所有节点..."

    all_nodes=$(parse_all_nodes "$group_json")
    best_node=""
    best_delay=999999

    # 写入临时文件收集结果（避免子 shell 变量丢失）
    _tmp="/tmp/mihomo_failover_$$"
    rm -f "$_tmp"

    echo "$all_nodes" | while IFS= read -r node; do
        [ -z "$node" ] && continue
        [ "$node" = "$current" ] && continue

        node_delay=$(test_delay "$node")
        if [ -n "$node_delay" ]; then
            echo "${node_delay} ${node}" >> "$_tmp"
        fi
    done

    if [ -f "$_tmp" ] && [ -s "$_tmp" ]; then
        # 按延迟排序取第一行（最低延迟）
        best_line=$(sort -n "$_tmp" | head -1)
        best_delay=$(echo "$best_line" | cut -d' ' -f1)
        best_node=$(echo "$best_line" | cut -d' ' -f2-)
        rm -f "$_tmp"

        switch_node "$group" "$best_node"
        log "[${group}] 已切换到 ${best_node} (${best_delay}ms)"
    else
        rm -f "$_tmp"
        log "[${group}] 所有节点均不可用！"
    fi
}

# ============ 主逻辑 ============
check_group "🇭🇰 香港节点"
check_group "🇹🇼 台湾节点"
check_group "🇯🇵 日本节点"
check_group "🇸🇬 新加坡节点"
check_group "🇺🇸 美国节点"
