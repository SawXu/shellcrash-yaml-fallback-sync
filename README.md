# shellcrash-yaml-fallback-sync

定时拉取 ShellCrash 默认分支上的最新 YAML，并将 5 个地区节点组改写为 `fallback` 后提交回仓库。

## 上游来源

- 仓库：`juewuy/ShellCrash`
- 文件：`rules/clash_providers/DustinWin_RS_Full_NoAds.yaml`
- 分支：每次运行时动态查询仓库默认分支

## 生成结果

- 输出文件：`generated/DustinWin_RS_Full_NoAds.yaml`

## 本地运行

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_yaml.py
python3 scripts/sync_yaml.py --check
```

## 自动化

GitHub Actions 支持：

- 手动触发
- 每天定时同步
- 仅当 `generated/DustinWin_RS_Full_NoAds.yaml` 变化时才提交到 `main`
