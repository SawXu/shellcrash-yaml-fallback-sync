# shellcrash-yaml-fallback-sync

定时拉取 ShellCrash 默认分支上的最新 YAML，并将 5 个地区节点组从 `url-test` 改写为 `select` 后提交回仓库。

> 仓库名沿用了早期命名，但当前同步脚本并不会把节点组改成 `fallback`。

## 上游来源

- 仓库：`juewuy/ShellCrash`
- 文件：`rules/clash_providers/DustinWin_RS_Full_NoAds.yaml`
- 分支：每次运行时动态查询仓库默认分支
- 说明：本仓库先同步 ShellCrash 上游 YAML，再对生成结果做本地转换

## mrs 规则源

- 现有 `rule-providers` 中的 `.mrs` 文件下载地址统一改写为 DustinWin 官方源
- 官方源：`https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/<name>.mrs`
- 示例：`media.mrs` 对应 `https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/media.mrs`
- 当前不会新增或删除规则集，仅替换 YAML 中已有 `.mrs` 的下载地址

## 生成结果

- 输出文件：`generated/DustinWin_RS_Full_NoAds.yaml`
- 改写范围：`🇭🇰 香港节点`、`🇹🇼 台湾节点`、`🇯🇵 日本节点`、`🇸🇬 新加坡节点`、`🇺🇸 美国节点`
- 改写规则：将上述节点组的 `type: url-test` 改为 `type: select`，并移除对应的 `tolerance`
- 如需在 `select` 组基础上做自动故障切换，可配合 `scripts/mihomo-failover.sh`

## 本地运行

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_yaml.py
python3 scripts/sync_yaml.py --check
```

## 故障切换脚本

- 脚本：`scripts/mihomo-failover.sh`
- 作用：从 Claude 的入口策略组开始，递归解析当前实际命中的地区组；只有当当前链路真实无法访问 `claude.ai` 时，才在命中的地区组内依次切换候选节点
- 依赖：可访问 Mihomo Controller API，且系统可用 `curl`
- 先修改脚本顶部配置：`API_BASE`、`SECRET`、`PROXY_URL`、`CLAUDE_URL`、`ENTRY_GROUPS`、`CURL_CONNECT_TIMEOUT`、`CURL_MAX_TIME`、`SWITCH_WAIT`
- 默认只追踪 `🤖 AI 平台` 这条 Claude 入口策略链；只有你显式配置多个 Claude 专用入口时，才会维护多个入口
- 连通性判断不再依赖 `gstatic` 或 Mihomo 的 `delay` 探测，而是通过本机代理直接请求 `claude.ai`

```bash
sh scripts/mihomo-failover.sh
```

建议配合 `cron` 每 2 分钟执行一次：

```cron
*/2 * * * * /bin/sh /path/to/shellcrash-yaml-fallback-sync/scripts/mihomo-failover.sh >> /tmp/mihomo-failover.log 2>&1
```

## 自动化

GitHub Actions 支持：

- 手动触发
- 每天定时同步
- 仅当 `generated/DustinWin_RS_Full_NoAds.yaml` 变化时才提交到 `main`
