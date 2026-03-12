# DustinWin MRS Source Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite existing `.mrs` rule-provider URLs in the generated mihomo YAML to DustinWin's current official GitHub Releases source.

**Architecture:** Keep the current sync flow from ShellCrash upstream unchanged, then apply a deterministic post-download text transform to existing `.mrs` rule-provider URLs. Preserve the current region-group fallback/select rewrite and avoid adding or removing any rule sets.

**Tech Stack:** Python 3, unittest, plain text YAML transformation

---

### Task 1: Add failing tests for official MRS source rewriting

**Files:**
- Modify: `tests/test_sync_yaml.py`
- Test: `tests/test_sync_yaml.py`

**Step 1: Write the failing test**

Add assertions that:
- `https://testingcf.jsdelivr.net/gh/DustinWin/ruleset_geodata@mihomo-ruleset/media.mrs` becomes `https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/media.mrs`
- another existing `.mrs` URL is also rewritten
- non-URL content remains unchanged

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_sync_yaml.TransformContentTests.test_rewrites_existing_mrs_urls_to_dustinwin_official_release -v`

Expected: FAIL because the current transform does not rewrite `.mrs` URLs.

### Task 2: Implement minimal URL rewrite

**Files:**
- Modify: `scripts/sync_yaml.py`
- Test: `tests/test_sync_yaml.py`

**Step 1: Write minimal implementation**

Add a helper that rewrites existing `ruleset_geodata` `.mrs` URLs to:

`https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/<filename>.mrs`

Apply it inside the existing line-by-line transformation flow.

**Step 2: Run focused tests to verify they pass**

Run: `python3 -m unittest tests.test_sync_yaml -v`

Expected: PASS

### Task 3: Regenerate output and verify generated file

**Files:**
- Modify: `generated/DustinWin_RS_Full_NoAds.yaml`
- Test: `generated/DustinWin_RS_Full_NoAds.yaml`

**Step 1: Regenerate output**

Run: `python3 scripts/sync_yaml.py`

**Step 2: Verify generated file contains official release URLs**

Run: `rg -n 'https://github.com/DustinWin/ruleset_geodata/releases/download/mihomo-ruleset/(media|private|cn)\\.mrs' generated/DustinWin_RS_Full_NoAds.yaml`

Expected: matching lines present, especially `media.mrs`.

### Task 4: Simplify and verify

**Files:**
- Modify: `scripts/sync_yaml.py`
- Modify: `tests/test_sync_yaml.py`

**Step 1: Apply code simplification review**

Review the recently modified Python code for clarity and remove any unnecessary complexity while preserving behavior.

**Step 2: Run full verification**

Run:
- `python3 -m unittest discover -s tests -v`
- `python3 scripts/sync_yaml.py --check`

Expected: all tests pass and `--check` exits successfully.
