# shellcrash-yaml-fallback-sync

定时拉取上游 ShellCrash YAML，并将 5 个地区节点组改写为 `fallback` 后提交回仓库。

## 上游来源

- `https://raw.githubusercontent.com/juewuy/ShellCrash/ed635b871a3b0441b0c62cfa2dd120dbde0e3aa6/rules/clash_providers/DustinWin_RS_Full_NoAds.yaml`

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
- 内容变化时自动提交到 `main`
