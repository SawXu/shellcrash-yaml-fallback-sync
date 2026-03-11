# Default Branch Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the sync script follow the current default branch of `juewuy/ShellCrash` and ensure the workflow commits only when `generated/DustinWin_RS_Full_NoAds.yaml` changes.

**Architecture:** The Python script will query the GitHub repository API for `default_branch`, derive the raw YAML URL from that branch, then apply the existing select transformation. The workflow will continue generating the YAML but narrow commit detection to the generated file only.

**Tech Stack:** Python 3 standard library, unittest, GitHub Actions

---

### Task 1: Add failing tests for dynamic branch resolution

**Files:**
- Modify: `tests/test_sync_yaml.py`
- Modify: `scripts/sync_yaml.py`

**Step 1: Add tests for branch resolution helpers**

Add tests that expect:

- GitHub API JSON with `"default_branch": "dev"` returns `dev`
- the raw URL builder includes that branch in the final download URL

**Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: Tests fail because helper functions do not exist yet.

### Task 2: Implement default branch lookup

**Files:**
- Modify: `scripts/sync_yaml.py`

**Step 1: Add helper functions**

Implement:

- a function that downloads repo metadata from `https://api.github.com/repos/juewuy/ShellCrash`
- a function that extracts `default_branch`
- a function that builds the raw YAML URL from the branch

**Step 2: Update download flow**

Replace the fixed commit URL logic so runtime download always uses the current default branch.

**Step 3: Run tests**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_yaml.py
python3 scripts/sync_yaml.py --check
```

Expected: Tests pass and script still generates the YAML successfully.

**Step 4: Run `code-simplifier` on the updated script**

Apply `code-simplifier` to:

- `scripts/sync_yaml.py`
- `tests/test_sync_yaml.py`

### Task 3: Narrow commit detection in workflow

**Files:**
- Modify: `.github/workflows/sync-shellcrash-yaml.yml`
- Modify: `README.md`

**Step 1: Update workflow commit condition**

Change the workflow so it checks:

```bash
git diff --quiet -- generated/DustinWin_RS_Full_NoAds.yaml
```

Expected:

- no diff means no commit
- diff means commit only the generated file

**Step 2: Update README**

Document:

- upstream now follows the current ShellCrash default branch
- workflow commits only when the generated YAML changes

### Task 4: Final verification and push

**Files:**
- Test: `scripts/sync_yaml.py`
- Test: `tests/test_sync_yaml.py`
- Test: `.github/workflows/sync-shellcrash-yaml.yml`
- Test: `generated/DustinWin_RS_Full_NoAds.yaml`

**Step 1: Run full verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/sync_yaml.py
python3 scripts/sync_yaml.py --check
rg -n 'name: (🇭🇰 香港节点|🇹🇼 台湾节点|🇯🇵 日本节点|🇸🇬 新加坡节点|🇺🇸 美国节点), type: select' generated/DustinWin_RS_Full_NoAds.yaml
rg -n 'name: (♻️ 自动选择|👑 高级节点|📉 省流节点), type: url-test' generated/DustinWin_RS_Full_NoAds.yaml
git diff -- .github/workflows/sync-shellcrash-yaml.yml README.md scripts/sync_yaml.py tests/test_sync_yaml.py generated/DustinWin_RS_Full_NoAds.yaml
```

Expected: All checks pass and diff only contains intended files.

**Step 2: Commit and push**

Run:

```bash
git add README.md .github/workflows/sync-shellcrash-yaml.yml scripts/sync_yaml.py tests/test_sync_yaml.py generated/DustinWin_RS_Full_NoAds.yaml docs/plans/2026-03-10-default-branch-sync.md
git commit -m "fix: follow upstream default branch for yaml sync"
git push
```

Expected: The repository contains the updated sync logic and workflow.
