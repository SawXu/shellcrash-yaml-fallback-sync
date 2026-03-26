# Claude AI Failover Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `mihomo-failover.sh` 只维护当前 Claude 策略链中实际使用的地区组，并以真实 `claude.ai` 连通性作为切换依据。

**Architecture:** 入口从可配置的 Claude 策略组开始，递归解析 Mihomo 当前选择链，找出最终命中的地区组。脚本先用本机代理真实请求 `claude.ai`；只有当前链路失败时，才在对应地区组内依次切换候选节点并重新实测。

**Tech Stack:** POSIX `sh`、`curl`、Mihomo Controller API、Python `unittest`

---

### Task 1: 补策略链和切换行为测试

**Files:**
- Create: `tests/test_mihomo_failover.py`
- Test: `tests/test_mihomo_failover.py`

- [ ] **Step 1: 写失败用例**

覆盖以下行为：
- 入口策略链能解析到当前实际使用的地区组
- 多个入口策略链会去重
- 当前 `claude.ai` 可达时不切换节点
- 当前 `claude.ai` 不可达时会逐个切换候选节点直到恢复

- [ ] **Step 2: 运行测试并确认失败**

Run: `python3 -m unittest tests.test_mihomo_failover -v`
Expected: FAIL，提示脚本缺少新的策略链解析/切换逻辑或无法被测试源码引用

### Task 2: 改造故障切换脚本

**Files:**
- Modify: `scripts/mihomo-failover.sh`
- Test: `tests/test_mihomo_failover.py`

- [ ] **Step 1: 增加可配置的 Claude 检测参数**

新增：
- Claude 入口策略组列表
- 本机代理地址
- Claude 检测 URL
- 脚本源码引用模式，供测试复用函数

- [ ] **Step 2: 实现策略链解析**

从 Claude 入口策略组开始递归读取 `now`，直到命中地区组或遇到非策略节点。对多个入口结果去重，只维护当前真实命中的地区组。

- [ ] **Step 3: 实现真实连通性检测与切换**

用 `curl --proxy` 直接探测 `claude.ai`。当前链路可达则不切换；不可达时，在命中的地区组内按顺序切换候选节点，每次切换后重新实测。

- [ ] **Step 4: 运行目标测试并确认通过**

Run: `python3 -m unittest tests.test_mihomo_failover -v`
Expected: PASS

### Task 3: 验证并整理

**Files:**
- Modify: `README.md`
- Test: `python3 -m unittest discover -s tests -v`

- [ ] **Step 1: 更新 README 的脚本说明**

把检测逻辑从 `gstatic`/延迟探测改成 Claude 实连检查，并补充新增配置项说明。

- [ ] **Step 2: 运行全量测试**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS
