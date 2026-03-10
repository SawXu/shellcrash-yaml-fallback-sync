# 默认分支跟随与条件提交设计

## 背景

当前仓库会从固定 commit 下载上游 YAML，这不符合“始终跟随 ShellCrash 默认分支最新文件”的目标。

此外，workflow 当前使用全仓库 diff 作为提交条件，虽然已经能避免大多数空提交，但更稳妥的做法是只根据目标生成文件是否变化来决定是否提交。

## 目标

- 每次执行时动态查询 `juewuy/ShellCrash` 的默认分支
- 从该默认分支下载最新的 `rules/clash_providers/DustinWin_RS_Full_NoAds.yaml`
- 继续只改 5 个地区组为 `fallback`
- 仅当 `generated/DustinWin_RS_Full_NoAds.yaml` 与上一次提交相比有变化时才提交

## 方案

### 方案 1：脚本内解析默认分支

脚本先请求 GitHub API：

- `https://api.github.com/repos/juewuy/ShellCrash`

读取 `default_branch` 后再拼出 raw URL。

优点：

- 逻辑集中在脚本里
- workflow 简洁
- 默认分支未来改名时无需手动更新

缺点：

- 多一次 API 请求

### 方案 2：workflow 里解析默认分支

优点：

- 脚本更单纯

缺点：

- 逻辑分散在 workflow 和脚本之间
- 后续维护成本更高

推荐采用方案 1。

## 条件提交设计

workflow 生成 YAML 后，使用：

- `git diff --quiet -- generated/DustinWin_RS_Full_NoAds.yaml`

判定是否变化。

行为：

- 无变化：直接结束，不提交
- 有变化：仅提交目标生成文件

## 验证

- 单测验证默认分支 API 响应可正确拼接 raw URL
- 单测验证地区组仍会被正确改成 `fallback`
- 本地运行脚本生成 YAML
- 本地运行 `--check`
- 检查 workflow 只对目标文件做 diff 判断
