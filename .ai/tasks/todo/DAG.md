# Execution DAG - Dependency Graph

## High Priority Path (Security + Core Correctness)

```
TASK_001_sec_001_cookie_file_cleanup (SEC-001)
         |
         +-- Independent
TASK_002_sec_002_env_ssl_fix (SEC-002)
         |
         +-- Sequential (same file)
TASK_004_cfg_005_remove_dead_singleton (CFG-005)
         |
         +-- Sequential (same file)  
TASK_005_cfg_002_remove_download_method (CFG-002)
```

## Config Wiring Path

```
TASK_006_cfg_001_wire_download_dir (CFG-001)
```

## Core Download Flow Path (Critical Coupling)

```
TASK_007_srv_002_browser_quality_override (SRV-002/DF-001)
         |
         +-- Sequential
TASK_008_qlt_001_max_retries_wiring (QLT-001/SRV-003/SRV-004)
         |
         +-- Sequential
TASK_009_srv_001_callback_wiring (SRV-001/DF-002)
         |
         +-- Research First
TASK_010_qlt_008_hlsdownloadrequest_research (Blocked)
         |
         +-- Sequential
TASK_011_cli_002_003_006_exception_handling (CLI-002/CLI-003/QLT-006)
         |
         +-- Sequential (same download flow)
TASK_019_df_003_004_resume_fixes (DF-003/DF-004)
         |
         +-- Sequential
TASK_020_df_005_http_url_fix (DF-005)
         |
         +-- Verification
TASK_022_verify_download_flow_changes
```

## Cleanup Tasks (Independent)

```
TASK_012_qlt_003_remove_unused_dependencies (QLT-003)
         |
         +-- Sequential
TASK_013_qlt_004_remove_unwired_modules (QLT-004)
         |
         +-- Sequential
TASK_014_qlt_007_remove_unused_dtos (QLT-007/SRV-009)
         |
         +-- Independent
TASK_015_cfg_003_wire_timezone (CFG-003)
         |
         +-- Sequential
TASK_016_srv_008_sec_005_cleanups (SRV-008/SEC-005)
         |
         +-- Sequential
TASK_017_srv_010_cookie_file_not_implemented (SRV-010/DF-006)
         
         +-- Independent
TASK_018_qlt_002_datetime_deprecation (QLT-002)
         
         +-- Independent
TASK_021_df_008_get_event_loop_fix (DF-008)
```

## Structural Refactoring (Independent)

```
TASK_023_str_001_read_progress_refactor (STR-001)
TASK_024_str_002_download_hls_refactor (STR-002)
TASK_025_str_003_ytdlp_resume_refactor (STR-003)
TASK_026_str_004_batch_cli_refactor (STR-004)
TASK_027_str_005_perform_download_refactor (STR-005)
TASK_028_str_006_split_download_segment (STR-006)
TASK_029_str_007_retry_backoff_helpers (STR-007)
TASK_030_str_008_split_downloader_module (STR-008)
```

## Test Improvements (Independent)

```
TASK_031_tst_001_real_segment_tests (TST-001)
TASK_032_tst_002_003_adaptive_throttle_tests (TST-002/003)
TASK_033_tst_004_005_006_test_quality_fixes (TST-004/005/006)
TASK_034_tst_007_008_fix_tests (TST-007/008)
```

## Documentation (Independent)

```
TASK_035_int_001_002_doc_updates (INT-001/INT-002/DF-009)
```

## Merged Findings (Same Task)

- **CFG-004 + QLT-008 + SRV-005 + STR-009**: HLSDownloadRequest monkeypatch refactoring (TASK_010 research, TASK_027 implementation)
- **QLT-007 + SRV-009**: Unused DTO removal (TASK_014)
- **SRV-008 + SEC-005**: Dead is_paused + CRLF sanitization (TASK_016)