---
id: morfx-tools
domain: reference
tags:
  - tools
  - morfx
  - ast
  - code-transformation
  - agents
  - dsl
related:
  - ast-editor
  - doc-maintenance-rules
---

# Morfx Tools — Agent Reference

> **Note:** The DSL examples in this document reference `telegram_service.py` and other files that are synthetic examples for illustration purposes only. They do not correspond to actual files in this codebase. This project is a VK Video Downloader, not a Telegram posting application.

AST-based code transformation tools for agents. Morfx operates on the actual syntax tree, making every transformation targeted by node type and structure rather than raw text.

## ⚠️ Windows Restrictions

On Windows, **do NOT use** `morfX_replace`, `morfX_apply`, `morfx_file_replace`, or `morfx_file_delete`. These tools use file rename operations that fail on Windows due to file locking by Python language servers, file watchers, and antivirus software. Use `ast-editor` tools instead for all Python edits on Windows.

Safe on Windows: `morfx_query`, `morfx_file_query` (read-only search).

## Core Concept: DSL for Nested Constructs

Morfx uses a **structural DSL** (Domain-Specific Language) to target nested code elements. The DSL is accepted by all tools — use `dsl` with read tools (`query`, `file_query`) and `target_dsl` with mutation tools (`replace`, `delete`, `insert_before`, `insert_after`, `append`).

The DSL syntax: `kind:pattern` with operators for nesting.

```
class:UserController >> method:index
func:* > call:os.getenv
class:* > method:render > call:setState
```

This allows agents to express "find a class that has a method named index" or "find functions that contain a call to os.getenv" in a single compact expression.

---

## Available Tools

### 1. `morfx_query`

**Purpose:** Find code elements in a single file.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | yes | `"python"`, `"go"`, `"javascript"`, `"typescript"`, `"php"` |
| `path` | string | yes* | Absolute path to source file |
| `source` | string | yes* | Source code text (alternative to `path`) |
| `query` | object | no | JSON query: `{"type": "function", "name": "foo*"}` |
| `dsl` | string | no | DSL selector: `"func:* > call:os.getenv"` |

*Exactly one of `path` or `source`. Use either `query` or `dsl`.

**Output:**

```json
{
  "content": [{"type": "text", "text": "summary"}],
  "matches": 1,
  "results": [
    {
      "type": "class",
      "name": "ImageCache",
      "line": 35,
      "column": 1,
      "content": "class ImageCache:\n    ..."
    }
  ],
  "path": "file.py"
}
```

### 2. `morfx_replace`

**Purpose:** Replace matched code elements with new content.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | yes | Language identifier |
| `path` | string | yes | File path |
| `target` | object | no* | JSON target: `{"type": "function", "name": "foo"}` |
| `target_dsl` | string | no* | DSL target: `"class:ImageCache"` |
| `replacement` | string | yes | Replacement source code |

*Use either `target` or `target_dsl`.

### 3. `morfx_delete`

**Purpose:** Remove matched code elements.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | yes | Language identifier |
| `path` | string | yes | File path |
| `target` | object | no* | JSON target |
| `target_dsl` | string | no* | DSL target |

**Behavior:** Confidence >= 0.85 auto-applies. Below 0.85, stages for review (use `morfx_apply` to confirm).

### 4. `morfx_insert_after`

**Purpose:** Insert code after a matched element.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | yes | Language identifier |
| `path` | string | yes | File path |
| `target` | object | no* | JSON target |
| `target_dsl` | string | no* | DSL target |
| `content` | string | yes | Code to insert (include `\n` for line breaks) |

### 5. `morfx_insert_before`

**Purpose:** Insert code before a matched element.

**Input:** Same structure as `morfx_insert_after`.

### 6. `morfx_append`

**Purpose:** Append code to end of file or specific scope.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | yes | Language identifier |
| `path` | string | yes | File path |
| `target` | object | no | Optional target to scope the append |
| `target_dsl` | string | no | DSL target for scoped append |
| `content` | string | yes | Code to append |

### 7. `morfx_file_query`

**Purpose:** Search for matches across multiple files.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | yes | Root directory to scan |
| `scope` | object | yes | File scope configuration |
| `query` | object | no | JSON query |
| `dsl` | string | no | DSL selector |

**`scope` object:**

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Root directory |
| `include` | string[] | Glob patterns: `["*.py"]` |
| `exclude` | string[] | Glob patterns to exclude |
| `language` | string | Language identifier |
| `max_files` | number | Maximum files to scan |

### 8. `morfx_file_replace`

**Purpose:** Replace matches across multiple files.

**Additional fields vs single-file:**

| Field | Type | Description |
|-------|------|-------------|
| `dry_run` | boolean | Preview without applying (default false) |
| `backup` | boolean | Create backup files (default false) |

### 9. `morfx_file_delete`

**Purpose:** Delete matches across multiple files. Same input contract as `file_replace` minus `replacement`.

### 10. `morfx_apply`

**Purpose:** Apply staged (low-confidence) transformations.

**Input:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Apply specific stage by ID |
| `all` | boolean | Apply all staged changes |
| `latest` | boolean | Apply the most recent stage (default) |

### 11. `morfx_recipe`

**Purpose:** Named repeatable transformation composed of multiple steps.

**Input:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Recipe name |
| `description` | string | no | Human-readable note |
| `dry_run` | boolean | no | Preview without applying |
| `min_confidence` | number | no | Confidence threshold (default 0.85) |
| `steps` | array | yes | Array of step objects |

**Step object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Step name |
| `method` | string | yes | `replace`, `delete`, `insert_before`, `insert_after`, or `append` |
| `scope` | object | yes | File scope |
| `target` | object | no | JSON target |
| `target_dsl` | string | no | DSL target |
| `replacement` | string | no | Replacement code (for replace) |
| `content` | string | no | Content to insert (for insert/append) |
| `min_confidence` | number | no | Per-step confidence threshold |

---

## DSL Reference

### Selector Shape

Every selector starts with `kind:pattern`:

```
kind:pattern
```

- `kind` — provider-owned selector type (e.g., `func`, `class`, `method`, `call`, `import`)
- `pattern` — shell-style wildcard pattern (`*`, `?`, `[abc]`) or exact name

```
func:*           # All functions
func:Handle*     # Functions starting with "Handle"
class:User       # Class named exactly "User"
call:os.Getenv   # Calls to os.Getenv
```

### Nesting Operators

| Operator | Name | Meaning | Example |
|----------|------|---------|---------|
| `>` | Contains descendant | Left contains matching descendant at any depth | `func:* > call:os.getenv` |
| `>>` | Direct semantic child | Left contains matching direct child | `class:UserController >> method:index` |
| `&` | Intersection | Both selectors match | `func:* & !func:Test*` |
| `\|` | Union | Either selector matches | `func:*\|method:*` |
| `!` | Negation | Does not match | `!func:Test*` |

**Operator precedence (strongest to weakest):** `!` → `>` / `>>` → `&` → `|`

Use parentheses for clarity:

```
(func:* | method:*) > call:fetch
func:* > (call:os.Getenv | call:viper.GetString)
```

### How Nesting Works

`>>` and `>` are **filters on the parent**. They find parent elements that contain specific children. The match result is the **parent element**.

```
class:ImageCache >> method:__init__
```

This finds "a class named ImageCache that has a direct method `__init__`". The match is the **class** `ImageCache`.

```
class:* >> method:get_posts
```

This finds "any class that has a direct method `get_posts`". The match is the **class** `PostProcessor`.

```
func:* > call:os.getenv
```

This finds "any function that contains a call to `os.getenv`". The match is the **function**.

### Deep Nesting

Chain operators for deeper targeting:

```
class:* > method:render > call:setState
```

Finds "any class that has a method `render` that contains a call to `setState`". The match is the **class**.

```
class:TelegramService >> method:_try_send_message
```

Finds "class `TelegramService` that has direct method `_try_send_message`". The match is the **class** `TelegramService`.

### Attributes

Attributes further constrain selectors:

| Attribute | Example | Meaning |
|-----------|---------|---------|
| `type=` | `field:Secret type=string` | Match field type |
| `arg0=` | `call:fetch arg0="/api/user"` | Match specific call argument |
| `source=` | `import:* source=react` | Match import source |
| `text=` | `return:* text="success"` | Match source text |
| `visibility=` | `method:render visibility=public` | Match visibility modifier |

Use quotes for values with punctuation:

```
call:fetch arg0="/api/user"
import:* source="react"
```

### Pattern Captures

Use `$name` inside a pattern to capture portions of the matched name:

```
call:$client.$method
```

Returns captures in match results:

```json
{"captures": {"client": "api", "method": "fetch"}}
```

Captures are read-only — they return values in match results but cannot be used as template variables in replacements.

### Python-Specific Selectors

| Selector | Notes |
|----------|-------|
| `def:load_user` | Python owns `def` |
| `function:load_user` | Also works |
| `decorator:cached_property` | Decorator matching |
| `from:django.conf` | From-import matching |
| `class:*` | All classes |
| `method:render` | Method declarations |
| `import:os` | Import statements |
| `call:os.getenv` | Function calls |
| `return:*` | All return statements |
| `assign:cache` | Assignments |

---

## DSL Examples (Verified)

### Finding Classes by Their Members

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "class:ImageCache >> method:__init__"
}
```

Finds `ImageCache` class (it has `__init__` as direct child). Match: the class.

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "class:* >> method:get_posts"
}
```

Finds `PostProcessor` class (only class with `get_posts` method). Match: the class.

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "class:TelegramService >> method:_try_send_message"
}
```

Finds `TelegramService` class (it has `_try_send_message` as direct child). Match: the class.

### Finding Functions by Their Calls

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "func:* > call:asyncio.gather"
}
```

Finds functions containing `asyncio.gather` calls. Match: the function.

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "func:* > call:logger.error"
}
```

Finds functions containing `logger.error` calls. Match: the function.

### Deep Nesting

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "class:* > method:run > call:asyncio.gather"
}
```

Finds classes that have a `run` method containing `asyncio.gather`. Match: the class.

### Negation

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "func:* & !func:_push*"
}
```

Finds functions NOT starting with `_push`.

### Union

```json
{
  "language": "python",
  "path": "telegram_service.py",
  "dsl": "func:* | method:*"
}
```

Finds all functions and all methods.

---

## JSON Query Alternative

For simple flat matching by type and name:

```json
{
  "language": "python",
  "path": "file.py",
  "query": {"type": "class", "name": "ImageCache"}
```

```json
{
  "language": "python",
  "path": "file.py",
  "query": {"type": "function", "name": "run_posting"}
```

```json
{
  "language": "python",
  "path": "file.py",
  "query": {"type": "class", "name": "*"}
```

Wildcards supported: `"name": "*"`, `"name": "Handle*"`.

**When to use JSON query vs DSL:**

| Scenario | Use |
|----------|-----|
| Find by type and name only | JSON `query` |
| Find elements containing other elements | DSL with `>` or `>>` |
| Find elements with specific calls inside | DSL with `>` |
| Find classes with specific methods | DSL with `>>` |
| Complex structural conditions | DSL with `&`, `|`, `!` |

---

## Confidence Scoring

Every transformation returns a confidence score (0.0–1.0):

- **>= 0.85**: Auto-applied immediately
- **< 0.85**: Staged for review, requires `morfx_apply` to confirm

Factors:
- `single_target` (+0.10): Only one match found
- `exported_api` (-0.20): Modifying public API

---

## Tool Selection Guide

### Use `morfx` tools when:

| Scenario | Tool |
|----------|------|
| Find all classes in a file | `morfx_query` with `query: {"type": "class"}` |
| Find classes containing specific methods | `morfx_query` with `dsl: "class:* >> method:foo"` |
| Find functions containing specific calls | `morfx_query` with `dsl: "func:* > call:bar"` |
| Find elements across files | `morfx_file_query` |
| Delete a top-level function | `morfx_delete` with `target_dsl: "func:foo"` |
| Insert code before/after a class | `morfx_insert_before` / `morfx_insert_after` with `target_dsl: "class:Foo"` |
| Append to end of file | `morfx_append` |
| Replace across multiple files | `morfx_file_replace` |
| Cross-file search and delete | `morfx_file_delete` |

### Use `ast-editor` tools when:

| Scenario | Tool |
|----------|------|
| Replace a few lines inside a class method | `ast-editor:replace_in_body` |
| Add a field to a specific class | `ast-editor:add_field` |
| Delete a specific method in a class | `ast-editor:delete_symbol` |
| Insert code inside a method body | `ast-editor:insert_in_body` |
| Replace lines inside a method | `ast-editor:replace_in_body` |
| Add/remove import statements | `ast-editor:add_import` / `ast-editor:remove_import` |

`ast-editor` uses `ClassName.method` targeting which is always class-scoped and precise.

---

## Workflow Examples

### Example 1: Find and inspect a class, then modify a method

```
1. morfx_query(language="python", path="file.py", dsl="class:ImageCache >> method:__init__")
   → Finds ImageCache class, confirms it has __init__

2. ast-editor:read_symbol(file_path="file.py", target="ImageCache.__init__")
   → Read the exact source of __init__

3. ast-editor:replace_in_body(file_path="file.py", target="ImageCache.__init__",
       old_snippet="        self.cache_dir = cache_dir",
       new_snippet="        self.cache_dir = cache_dir\n        self.cache_dir.mkdir(parents=True, exist_ok=True)")
    → Line replaced inside method body
```

### Example 2: Find functions containing a pattern, then replace

```
1. morfx_query(language="python", path="file.py", dsl="func:* > call:logger.error")
   → Finds all functions containing logger.error calls

2. morfx_replace(language="python", path="file.py", target_dsl="func:run_posting",
      replacement="def run_posting(config_path=None):\n    ...")
   → Top-level function replaced
```

### Example 3: Cross-file operation

```
1. morfx_file_query(path="src", scope={"include": ["*.py"], "language": "python", "max_files": 50},
      dsl="class:* >> method:cleanup")
   → Finds all classes with cleanup methods across the codebase

2. morfx_file_replace(path="src", scope={...}, target_dsl="class:OldClass",
      replacement="class NewClass:\n    ...")
   → Replace across all matching files
```

### Example 4: Insert before a class

```
1. morfx_insert_before(language="python", path="file.py",
      target_dsl="class:PostProcessor",
      content="# New helper class\nclass Helper:\n    pass\n\n")
   → Comment and helper class inserted before PostProcessor
```

### Example 5: Delete a top-level function

```
1. morfx_delete(language="python", path="file.py", target_dsl="func:run_posting")
   → Deletes the run_posting function (stages if confidence < 0.85)

2. morfx_apply(id="stg_xxx")
   → Confirms the deletion
```

---

## Limitations (Verified)

1. **DSL `>>` and `>` return the parent match**: `class:ImageCache >> method:__init__` returns the class, not the method. For method-specific mutations, use `ast-editor` tools.

2. **JSON `target` is not class-scoped**: `{"type": "method", "name": "__init__"}` matches ALL methods named `__init__` across all classes in the file.

3. **Captures are read-only**: DSL captures like `call:$client.$method` return values in match results but cannot be used as template variables in replacements.

4. **No dry-run on single-file tools**: Only `file_replace` and `file_delete` support `dry_run`. Single-file mutation tools apply immediately or stage based on confidence.
