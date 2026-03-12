# shellcrash-yaml-fallback-sync

定时拉取 ShellCrash 默认分支上的最新 YAML，并将 5 个地区节点组从 `url-test` 改写为 `select` 后提交回仓库。

> 仓库名沿用了早期命名，但当前同步脚本并不会把节点组改成 `fallback`。

## 上游来源

- 仓库：`juewuy/ShellCrash`
- 文件：`rules/clash_providers/DustinWin_RS_Full_NoAds.yaml`
- 分支：每次运行时动态查询仓库默认分支

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
- 作用：定时检查 5 个地区 `select` 组当前节点是否可用；当前节点不可用时，测试组内其他节点并切换到延迟最低的可用节点
- 依赖：可访问 Mihomo Controller API，且系统可用 `curl`
- 先修改脚本顶部配置：`API_BASE`、`SECRET`、`TEST_URL`、`TIMEOUT`

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
