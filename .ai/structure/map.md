# Structure map of vkdownloader source tree (QLT-004).
# Regeneration: uv run find src/vkdownloader -name '*.py' | sort > .ai/structure/map.md
# (This file lists only .py source modules — no .pyc, no .egg-info.)
#
# src/vkdownloader/
# +-- __init__.py
# +-- __main__.py
# +-- cli.py
# +-- config.py
# +-- exceptions.py
# +-- infrastructure/
#     +-- __init__.py
#     +-- browser.py
#     +-- network_monitor.py
# +-- models/
#     +-- __init__.py
#     +-- dtos.py
#     +-- enums.py
#     +-- quality.py
#     +-- video.py
# +-- services/
#     +-- __init__.py
#     +-- batch_downloader.py
#     +-- concurrency.py
#     +-- cookies.py
#     +-- downloader.py
#     +-- downloader_throttle.py
#     +-- extractor.py
#     +-- ffmpeg_utils.py
#     +-- progress_display.py
#     +-- quality.py
#     +-- segment_downloader.py
#     +-- signal_handlers.py
#     +-- ytdlp_downloader.py
# +-- utils/
#     +-- __init__.py
#     +-- correlation.py
#     +-- formatting.py
#     +-- security.py
#     +-- url_sanitizer.py
