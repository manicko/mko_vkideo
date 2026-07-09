# Research: Resolving create_stealth_context Async Type Issue (CFG-005)

## Executive Summary

**Decision: Remove the function entirely** — `create_stealth_context` is dead code (unused in production) with a critical async/sync mismatch. The `BrowserManager` class already provides equivalent functionality via `create_stealth_page()` method.

## Evidence Analysis

### Current State

| Metric | Finding |
|--------|---------|
| **Production Usage** | `BrowserManager` imported in `extractor.py:13`, NOT `create_stealth_context` |
| **Type Error** | mypy: `Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext")` at line 29 |
| **Test Status** | Tests pass but mask the bug (MagicMock returns synchronously) |
| **Security Concern** | Empty `user_data_dir=""` passes undefined path to Playwright |
| **Documentation** | Mentioned in overview.md but never documented in API reference |

### Code Evidence

```python
# browser.py:13-29 - Function declared sync but calls async method
def create_stealth_context(...) -> "BrowserContext":
    return playwright.chromium.launch_persistent_context(...)  # Missing await!
```

```python
# extractor.py:13-15 - Only BrowserManager is imported
from ..infrastructure.browser import BrowserManager  # NOT create_stealth_context
```

```python
# browser.py:91 - BrowserManager already provides context creation
context = await self.browser.new_context(  # Uses correct async pattern
    viewport={"width": 1920, "height": 1080},
    user_agent=self.settings.user_agent,
    locale=self.settings.locale,
)
```

## Options Evaluated

### Option A: Fix async signature (Add `async`/`await`)

**Pros:**
- Maintains backward compatibility if external code uses it

**Cons:**
- Function is dead code — no external usage exists
- Required async signature would differ from tests (which use sync MagicMock)
- No value proposition — `BrowserManager` already provides context creation
- Requires test rewrite to be meaningful
- Security issue remains (undefined user_data_dir location)

### Option B: Remove function entirely

**Pros:**
- Eliminates the type error completely
- Removes dead code and security risk
- Tests would be deleted (they test a non-existent function)
- Cleaner codebase aligns with "Avoid Overengineering" principle
- `BrowserManager.create_stealth_page()` already provides equivalent functionality

**Cons:**
- Breaking change if external code somehow depends on it (unlikely per audit)

## Verification: Production Usage Check

```
grep -r "create_stealth_context" src/
Only finds: definition in browser.py (line 13)
```

```
grep -r "create_stealth_page" src/
Finds: extractor.py:158 (used in _extract_with_browser)
```

## Recommended Solution

**REMOVE `create_stealth_context` entirely.**

### Rationale

1. **Dead Code Principle**: Function is exported but never called in production
2. **Existing Alternative**: `BrowserManager.create_stealth_page()` provides identical stealth context functionality
3. **Security Risk**: Empty `user_data_dir=""` creates profiles in unpredictable locations
4. **Complexity Reduction**: Removing unused code aligns with "Small Modules" rule (#15)
5. **No False Positives**: Tests use MagicMock which doesn't enforce async correctness

### Implementation Changes

| File | Action |
|------|--------|
| `src/vkdownloader/infrastructure/browser.py` | Remove lines 13-37 (entire `create_stealth_context` function) |
| `src/vkdownloader/infrastructure/__init__.py` | Remove `create_stealth_context` from import and export |
| `tests/test_browser_infrastructure.py` | Remove `TestStealthContext` class (lines 59-101) |
| `docs/01-tools/vkdownloader-overview.md` | No action needed (doesn't mention function directly) |

## Confidence Assessment

| Source | Confidence |
|--------|------------|
| Production code analysis | HIGH - No usages found in src/ |
| Type checker (mypy) | HIGH - Confirms async/sync mismatch |
| Test analysis | HIGH - Tests mask async bug with MagicMock |
| Playwright API docs | HIGH - `launch_persistent_context` is clearly async |

---

**Final Recommendation: Remove `create_stealth_context` function, its export, and its tests. The `BrowserManager.create_stealth_page()` method already provides the needed stealth context functionality using the correct async pattern.**