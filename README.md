# shellcrash-yaml-fallback-sync

定时拉取 ShellCrash 默认分支上的最新 YAML，对 `.mrs` 规则源做地址改写、并在 `🤖 AI 平台` 分组中追加 `👉 手动选择` 引用后提交回仓库。

> 仓库名沿用了早期命名，但当前同步脚本不再把地区节点组改成 `select`/`fallback`，地区组保持上游的 `url-test` 自动探活模式。

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
- 改写内容：
  - `🤖 AI 平台` 分组的 `proxies` 列表在 `🚀 节点选择` 之后插入 `👉 手动选择` 引用，便于在 AI 平台分组中锁定固定节点
  - 所有 `rule-providers` 里的 `.mrs` 下载地址改写为 DustinWin 官方源
- 不再改写：地区节点组（`🇭🇰/🇹🇼/🇯🇵/🇸🇬/🇺🇸`）保持上游 `type: url-test` 与 `tolerance`，使用 mihomo 自带的延迟探活自动选最快节点
- 前置依赖：上游必须保留 `👉 手动选择` 与 `🤖 AI 平台` 两个组的定义，否则同步会失败退出

## 本地运行

```bash
python3 -m unittest tests.test_sync_yaml -v
python3 scripts/sync_yaml.py
python3 scripts/sync_yaml.py --check
```

## 故障切换脚本（已弃用）

> `scripts/mihomo-failover.sh` 已标记为 **DEPRECATED**：地区节点组恢复 `url-test` 类型后，Mihomo 不接受对 `url-test` 组 `PUT /proxies` 切换 `now`，脚本里 `switch_node` 调用对地区组无实际效果；AI 平台路径若已切到 `👉 手动选择` 并锁定固定节点，脚本因追不到地区组而自动跳过。脚本与 `tests/test_mihomo_failover.py` 仅作历史参考保留，CI 不再执行 failover 相关测试，建议从 cron 中移除调用。

## 自动化

GitHub Actions 支持：

- 手动触发
- 每天定时同步
- 仅当 `generated/DustinWin_RS_Full_NoAds.yaml` 变化时才提交到 `main`
