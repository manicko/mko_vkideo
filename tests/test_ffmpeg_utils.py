"""Unit tests for ffmpeg_utils merge and process management functions."""

import asyncio
import signal
import sys
from collections import namedtuple
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import DownloadError
from vkdownloader.services.ffmpeg_utils import (
    _MERGE_SPACE_MARGIN_BYTES,
    _build_ffmpeg_concat_command,
    _merge_batch_segments,
    _merge_segments_batched,
    _perform_final_merge,
    _required_merge_bytes,
    cancel_subprocess,
)

# Mirrors the shape of the value shutil.disk_usage returns (a named tuple of
# total/used/free) so a patched probe can be read by production code.
_DiskUsage = namedtuple("_DiskUsage", "total used free")


def _fake_disk_usage(free_bytes: int) -> _DiskUsage:
    """Build a disk_usage result reporting ``free_bytes`` of free space."""
    return _DiskUsage(free_bytes * 2, free_bytes, free_bytes)


class TestBuildFfmpegConcatCommand:
    """Tests for _build_ffmpeg_concat_command function."""

    def test_build_concat_command_basic(self, tmp_path: Path) -> None:
        """Test basic concat command construction with file list and output."""
        file_list = tmp_path / "list.txt"
        output = tmp_path / "output.ts"

        cmd = _build_ffmpeg_concat_command(file_list, output)

        assert cmd == [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(file_list),
            "-c",
            "copy",
            str(output),
        ]

    def test_build_concat_command_uses_paths(self, tmp_path: Path) -> None:
        """Test that paths are included in command."""
        file_list = tmp_path / "list.txt"
        output = tmp_path / "output" / "video.ts"

        cmd = _build_ffmpeg_concat_command(file_list, output)

        # Verify paths are in command (using str() for Windows compatibility)
        assert str(file_list) in cmd
        assert str(output) in cmd

    def test_build_concat_command_fixed_values(self, tmp_path: Path) -> None:
        """Test that command structure has required ffmpeg flags."""
        file_list = tmp_path / "list.txt"
        output = tmp_path / "output.ts"

        cmd = _build_ffmpeg_concat_command(file_list, output)

        # Verify required flags are present
        assert "ffmpeg" in cmd
        assert "-y" in cmd  # Overwrite output
        assert "-f" in cmd  # Format
        assert "concat" in cmd  # Concat demuxer
        assert "-safe" in cmd
        assert "0" in cmd  # Safe disabled
        assert "-i" in cmd  # Input
        assert "-c" in cmd  # Codec
        assert "copy" in cmd  # Stream copy


class TestCancelSubprocess:
    """Tests for cancel_subprocess function."""

    @pytest.mark.asyncio
    async def test_terminate_on_success(self) -> None:
        """Test that process is terminated when it exits gracefully."""
        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_process.pid = 12345

        result = await cancel_subprocess(mock_process)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_not_called()
        assert result is True

    @pytest.mark.asyncio
    async def test_kill_on_timeout(self) -> None:
        """Test that process is killed when terminate times out."""
        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.pid = 12345

        # Create a wait mock that raises TimeoutError to simulate timeout
        # The coroutine (process.wait()) must NOT be awaited here as we're mocking wait_for
        wait_call_count = 0

        async def mock_wait() -> int:
            nonlocal wait_call_count
            wait_call_count += 1
            if wait_call_count == 1:
                # First call - simulate timeout
                raise TimeoutError()
            return 0  # Second call after kill - return success

        mock_process.wait = mock_wait

        result = await cancel_subprocess(mock_process, timeout=0.01)  # Short timeout

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_process_lookup_error(self) -> None:
        """Test that returns False when process already terminated."""
        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.terminate = MagicMock()
        mock_process.pid = 12345

        async def mock_wait() -> int:
            raise ProcessLookupError()

        mock_process.wait = mock_wait

        result = await cancel_subprocess(mock_process)

        mock_process.terminate.assert_called_once()
        assert result is False

    def test_backward_compatible_alias(self) -> None:
        """Test that cancel_ffmpeg_process alias still works."""
        from vkdownloader.services import ffmpeg_utils

        assert ffmpeg_utils.cancel_ffmpeg_process is ffmpeg_utils.cancel_subprocess

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: killpg path")
    async def test_killpg_called_when_returncode_none(self) -> None:
        """On POSIX, os.killpg is called with SIGTERM when returncode is None."""
        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.pid = 4242
        mock_process.returncode = None

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait

        with patch("vkdownloader.services.ffmpeg_utils.os.killpg") as mock_killpg:
            result = await cancel_subprocess(mock_process)

        assert result is True
        mock_killpg.assert_called_once_with(4242, signal.SIGTERM)
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only: killpg path")
    async def test_killpg_skipped_when_returncode_set(self) -> None:
        """When returncode is already set, os.killpg is not called (gh-127049 guard)."""
        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.pid = 4242
        mock_process.returncode = 0  # Already exited

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait

        with patch("vkdownloader.services.ffmpeg_utils.os.killpg") as mock_killpg:
            result = await cancel_subprocess(mock_process)

        assert result is True
        mock_killpg.assert_not_called()
        mock_process.terminate.assert_called_once()


class TestMergeBatchSegments:
    """Tests for _merge_batch_segments function."""

    @pytest.mark.asyncio
    async def test_merge_batch_creates_file_list(self, tmp_path: Path) -> None:
        """Test that merge creates correct file list content."""
        # Create mock segment files
        segment1 = tmp_path / "00000.ts"
        segment2 = tmp_path / "00001.ts"
        segment1.write_bytes(b"segment1 data")
        segment2.write_bytes(b"segment2 data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _merge_batch_segments([segment1, segment2], tmp_path, 300)

            # Should return path to batch output
            assert result is not None
            assert result.name == "batch_00000.ts"
            assert result.parent == tmp_path

    @pytest.mark.asyncio
    async def test_merge_batch_preserves_input_files_on_success(self, tmp_path: Path) -> None:
        """D-13: the batch stage is additive; its inputs outlive it.

        Removing the inputs here destroyed the only copy of every
        already-merged byte whenever a later stage failed. They are now
        removed on the whole-merge success tail in _merge_segments_batched;
        the concat list is still removed here, because it is rebuilt on every
        attempt and carries no information.
        """
        segment1 = tmp_path / "00000.ts"
        segment2 = tmp_path / "00001.ts"
        segment1.write_bytes(b"segment1 data")
        segment2.write_bytes(b"segment2 data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _merge_batch_segments([segment1, segment2], tmp_path, 300)

        assert segment1.exists()
        assert segment2.exists()
        assert result is not None
        assert result.name == "batch_00000.ts"

    @pytest.mark.asyncio
    async def test_merge_batch_removes_file_list(self, tmp_path: Path) -> None:
        """Test that file list is removed after merge."""
        segment1 = tmp_path / "00000.ts"
        segment1.write_bytes(b"segment1 data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await _merge_batch_segments([segment1], tmp_path, 300)

            # File list should be removed
            file_list = tmp_path / "batch_list_0.txt"
            assert not file_list.exists()

    @pytest.mark.asyncio
    async def test_merge_batch_returns_none_on_failure(self, tmp_path: Path) -> None:
        """Test that merge returns None when ffmpeg fails."""
        segment1 = tmp_path / "00000.ts"
        segment1.write_bytes(b"segment1 data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b"ffmpeg error: invalid input"

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _merge_batch_segments([segment1], tmp_path, 300)

            assert result is None


class TestPerformFinalMerge:
    """Tests for _perform_final_merge function."""

    @pytest.mark.asyncio
    async def test_final_merge_creates_output(self, tmp_path: Path) -> None:
        """Test that final merge creates output file."""
        temp_file1 = tmp_path / "batch_00000.ts"
        temp_file2 = tmp_path / "batch_00001.ts"
        temp_file1.write_bytes(b"batch1 data")
        temp_file2.write_bytes(b"batch2 data")

        output = tmp_path / "merged.ts"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _perform_final_merge([temp_file1, temp_file2], output, 300)

            assert result is True

    @pytest.mark.asyncio
    async def test_final_merge_removes_temp_files(self, tmp_path: Path) -> None:
        """Test that temp files are removed after final merge."""
        temp_file1 = tmp_path / "batch_00000.ts"
        temp_file2 = tmp_path / "batch_00001.ts"
        temp_file1.write_bytes(b"batch1 data")
        temp_file2.write_bytes(b"batch2 data")

        output = tmp_path / "merged.ts"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await _perform_final_merge([temp_file1, temp_file2], output, 300)

            assert not temp_file1.exists()
            assert not temp_file2.exists()

    @pytest.mark.asyncio
    async def test_final_merge_removes_final_list(self, tmp_path: Path) -> None:
        """Test that final list file is removed after merge."""
        temp_file1 = tmp_path / "batch_00000.ts"
        temp_file1.write_bytes(b"batch1 data")

        output = tmp_path / "merged.ts"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await _perform_final_merge([temp_file1], output, 300)

            final_list = tmp_path / "final_list.txt"
            assert not final_list.exists()

    @pytest.mark.asyncio
    async def test_final_merge_returns_false_on_failure(self, tmp_path: Path) -> None:
        """Test that final merge returns False when ffmpeg fails."""
        temp_file1 = tmp_path / "batch_00000.ts"
        temp_file1.write_bytes(b"batch1 data")

        output = tmp_path / "merged.ts"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b"ffmpeg error"

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _perform_final_merge([temp_file1], output, 300)

            assert result is False

    @pytest.mark.asyncio
    async def test_final_merge_uses_correct_pipe_options(self, tmp_path: Path) -> None:
        """Test that final merge uses PIPE for stdout/stderr capture."""
        temp_file1 = tmp_path / "batch_00000.ts"
        temp_file1.write_bytes(b"batch1 data")

        output = tmp_path / "merged.ts"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await _perform_final_merge([temp_file1], output, 300)

            # Verify stderr was captured with PIPE
            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs["stdout"] == asyncio.subprocess.PIPE
            assert call_kwargs["stderr"] == asyncio.subprocess.PIPE


class TestMergeSegmentsBatched:
    """Tests for _merge_segments_batched function."""

    @pytest.mark.asyncio
    async def test_single_batch_merge(self, tmp_path: Path) -> None:
        """Test merge with single batch (<= 100 segments)."""
        output = tmp_path / "output.ts"

        # Create 10 segment files to satisfy the existence check
        for i in range(10):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Also create the batch output file since _merge_batch_segments creates it
            batch_output = tmp_path / "batch_00000.ts"
            batch_output.write_bytes(b"batch data")

            result = await _merge_segments_batched(tmp_path, output, 10)

        assert result == output

    @pytest.mark.asyncio
    async def test_multiple_batch_merge(self, tmp_path: Path) -> None:
        """Test merge with multiple batches (> 100 segments)."""
        output = tmp_path / "output.ts"

        # Create 250 segment files to satisfy the existence check
        for i in range(250):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Create batch output files
            for i in range(0, 250, 100):
                batch_output = tmp_path / f"batch_{i:05d}.ts"
                batch_output.write_bytes(b"batch data")

            result = await _merge_segments_batched(tmp_path, output, 250)

        assert result == output

    @pytest.mark.asyncio
    async def test_returns_error_on_missing_segment_files(self, tmp_path: Path) -> None:
        """Test that merge raises FileNotFoundError when segment files are missing."""
        output = tmp_path / "output.ts"

        # No segment files created

        with pytest.raises(FileNotFoundError) as exc_info:
            await _merge_segments_batched(tmp_path, output, 5)

        assert "Missing segment files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_returns_none_on_batch_merge_failure(self, tmp_path: Path) -> None:
        """Test that merge returns None when batch merge fails."""
        output = tmp_path / "output.ts"

        # Create segment files but make batch merge fail
        for i in range(5):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b"ffmpeg error"

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _merge_segments_batched(tmp_path, output, 5)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_final_merge_failure(self, tmp_path: Path) -> None:
        """Test that merge returns None when final merge fails."""
        output = tmp_path / "output.ts"

        # Create segment files
        for i in range(5):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        # Create the batch output file
        batch_output = tmp_path / "batch_00000.ts"
        batch_output.write_bytes(b"batch data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1  # Final merge fails
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b"final merge error"

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _merge_segments_batched(tmp_path, output, 5)

        assert result is None

    @pytest.mark.asyncio
    async def test_uses_correct_batch_size(self, tmp_path: Path) -> None:
        """Test that merge uses correct batch size of 100."""
        output = tmp_path / "output.ts"

        # Create 150 segment files
        for i in range(150):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        # Each batch merge deletes its concat list once it succeeds, so the way the
        # 150 segments were grouped is only observable while the ffmpeg call is in
        # flight. Record the list every invocation is handed, and succeed each one.
        concat_lists: list[tuple[str, list[str]]] = []

        async def fake_exec(*args: str, **kwargs: object) -> MagicMock:
            file_list = Path(args[args.index("-i") + 1])
            # Concat demuxer entries read `file '<path>'`; record the path itself.
            paths = [
                line.removeprefix("file '").removesuffix("'")
                for line in file_list.read_text(encoding="utf-8").splitlines()
            ]
            concat_lists.append((file_list.name, paths))
            return _successful_process()

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            # Create batch output files (2 batches for 150 segments). Their names
            # are the batch starts the merge actually produces, and the final
            # merge unlinks them, so a wrong batch size fails here too.
            batch_output_1 = tmp_path / "batch_00000.ts"
            batch_output_1.write_bytes(b"batch data")
            batch_output_2 = tmp_path / "batch_00100.ts"
            batch_output_2.write_bytes(b"batch data")

            result = await _merge_segments_batched(tmp_path, output, 150)

        assert result == output

        # 150 segments at 100 per batch: two batch merges plus one final merge.
        assert [name for name, _ in concat_lists] == [
            "batch_list_0.txt",
            "batch_list_100.txt",
            "final_list.txt",
        ]
        assert [len(paths) for _, paths in concat_lists] == [100, 50, 2]

        # The batch boundaries themselves: 0-99, then 100-149.
        assert concat_lists[0][1][0].endswith("/00000.ts")
        assert concat_lists[0][1][-1].endswith("/00099.ts")
        assert concat_lists[1][1][0].endswith("/00100.ts")
        assert concat_lists[1][1][-1].endswith("/00149.ts")

        # The final merge concatenates the two batch outputs into the artefact.
        assert concat_lists[2][1][0].endswith("/batch_00000.ts")
        assert concat_lists[2][1][1].endswith("/batch_00100.ts")

    @pytest.mark.asyncio
    async def test_final_merge_failure_preserves_every_input_segment(self, tmp_path: Path) -> None:
        """NET-001: a failed final stage must not destroy any original segment.

        Measured with the local stub: 250 segments + failed final stage left
        0 of 250 originals surviving (every batch temp and final_list.txt were
        swept by the finally). The fix preserves all 250 originals, all batch
        temps and final_list.txt, and returns None.
        """
        segments_dir = tmp_path / "segments"
        segments_dir.mkdir()
        output = tmp_path / "output.ts"
        _write_segments(segments_dir, 250, 1024)

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(1 << 40)),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_failing_exec("final_list.txt"),
            ),
        ):
            result = await _merge_segments_batched(segments_dir, output, 250)

        assert result is None
        assert all((segments_dir / f"{i:05d}.ts").exists() for i in range(250))
        assert (segments_dir / "batch_00000.ts").exists()
        assert (segments_dir / "batch_00100.ts").exists()
        assert (segments_dir / "batch_00200.ts").exists()
        assert (segments_dir / "final_list.txt").exists()
        assert not output.exists()

    @pytest.mark.asyncio
    async def test_batch_failure_preserves_inputs_and_earlier_batch_temps(
        self, tmp_path: Path
    ) -> None:
        """NET-001: a failure in a later batch must not destroy earlier data.

        Measured with the local stub: 250 segments + failed second batch left
        150 of 250 originals surviving and batch_00000.ts destroyed by the
        finally sweep. The fix preserves all 250 originals and the first
        batch's temp.
        """
        segments_dir = tmp_path / "segments"
        segments_dir.mkdir()
        output = tmp_path / "output.ts"
        _write_segments(segments_dir, 250, 1024)

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(1 << 40)),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_failing_exec("batch_list_100.txt"),
            ),
        ):
            result = await _merge_segments_batched(segments_dir, output, 250)

        assert result is None
        assert all((segments_dir / f"{i:05d}.ts").exists() for i in range(250))
        assert (segments_dir / "batch_00000.ts").exists()
        assert not (segments_dir / "batch_00100.ts").exists()

    @pytest.mark.asyncio
    async def test_success_removes_every_segment_temp_and_list(self, tmp_path: Path) -> None:
        """NET-001: the success path must leave the working directory empty.

        Every input segment, every batch temp, every batch_list and the
        final_list are removed -- zero *.ts and zero *.txt remain.
        """
        segments_dir = tmp_path / "segments"
        segments_dir.mkdir()
        output = tmp_path / "output.ts"
        _write_segments(segments_dir, 250, 1024)

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(1 << 40)),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_failing_exec(""),
            ),
        ):
            result = await _merge_segments_batched(segments_dir, output, 250)

        assert result == output
        assert output.exists()
        remaining = list(segments_dir.iterdir())
        assert remaining == []


def _write_segments(directory: Path, count: int, size_bytes: int) -> list[Path]:
    """Create ``count`` segments of ``size_bytes`` each, as the merge names them."""
    paths = [directory / f"{i:05d}.ts" for i in range(count)]
    for path in paths:
        path.write_bytes(b"x" * size_bytes)
    return paths


def _successful_process() -> MagicMock:
    """Build a mock ffmpeg process that exits cleanly."""

    mock_process = MagicMock(spec=asyncio.subprocess.Process)
    mock_process.returncode = 0
    mock_process.pid = 12345

    async def mock_communicate() -> tuple[bytes, bytes]:
        return b"", b""

    mock_process.communicate = mock_communicate
    return mock_process


def _failed_process() -> MagicMock:
    """Build a mock ffmpeg process that exits with a failure return code."""

    mock_process = MagicMock(spec=asyncio.subprocess.Process)
    mock_process.returncode = 1
    mock_process.pid = 12345

    async def mock_communicate() -> tuple[bytes, bytes]:
        return b"", b"ffmpeg error: invalid input"

    mock_process.communicate = mock_communicate
    return mock_process


def _failing_exec(fail_on: str) -> Callable[..., MagicMock]:
    """Build a process-launch stub that fails the named concat list only.

    Materialises the output path the real child would write, so the batch
    temps and the final output really exist: a MagicMock writes nothing, and
    a test over one asserts on the mock, not the merge.
    """

    def exec_(*args: str, **kwargs: object) -> MagicMock:
        file_list = Path(args[args.index("-i") + 1])
        if file_list.name == fail_on:
            return _failed_process()
        Path(args[-1]).write_bytes(b"merged data")
        return _successful_process()

    return exec_


class TestMergeFreeSpaceProbe:
    """Tests for the pre-merge free-space probe (D-09)."""

    def test_required_bytes_cover_final_merge_headroom(self, tmp_path: Path) -> None:
        """D-09: the requirement is the segments plus a full copy of them.

        The final artefact is written while the input is still on disk, so the
        required figure must cover the segment bytes twice, and carry the
        safety margin on top. This is the assertion that fails if the
        arithmetic drifts toward the segment total alone.
        """
        segments = _write_segments(tmp_path, 4, 1000)
        segment_bytes = 4000

        required = _required_merge_bytes(segments)

        assert required >= segment_bytes * 2
        assert required == segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES

    def test_required_bytes_ignore_missing_segments(self, tmp_path: Path) -> None:
        """D-09: a segment that is already gone contributes no bytes.

        Its absence is a different precondition, reported by the merge's own
        existence check; the size probe must not pre-empt that verdict by
        raising on the unstattable path.
        """
        segments = _write_segments(tmp_path, 2, 1000)

        required = _required_merge_bytes([*segments, tmp_path / "00002.ts"])

        assert required == 2000 * 2 + _MERGE_SPACE_MARGIN_BYTES

    @pytest.mark.asyncio
    async def test_insufficient_space_fails_before_spawning_ffmpeg(self, tmp_path: Path) -> None:
        """D-09: too little free space fails the merge before any subprocess.

        The subprocess assertion is the "fail early" half of the contract:
        without the probe the merge would spawn ffmpeg and discover the full
        volume at an arbitrary later point. The message must name both figures
        so the user can act on it.
        """
        _write_segments(tmp_path, 3, 2048)
        output = tmp_path / "output.ts"
        available = 1024

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(available)),
            patch("asyncio.create_subprocess_exec") as mock_exec,
            pytest.raises(DownloadError) as exc_info,
        ):
            await _merge_segments_batched(tmp_path, output, 3)

        mock_exec.assert_not_called()
        message = str(exc_info.value)
        assert str(3 * 2048 * 2 + _MERGE_SPACE_MARGIN_BYTES) in message
        assert str(available) in message
        assert "lower quality" in message

    @pytest.mark.asyncio
    async def test_sufficient_space_merges_normally(self, tmp_path: Path) -> None:
        """D-09: with room to spare the merge runs exactly as before."""
        _write_segments(tmp_path, 10, 2048)
        output = tmp_path / "output.ts"
        (tmp_path / "batch_00000.ts").write_bytes(b"batch data")
        mock_process = _successful_process()

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(1024**4)),
            patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        ):
            result = await _merge_segments_batched(tmp_path, output, 10)

        assert result == output
        mock_exec.assert_called()

    @pytest.mark.asyncio
    async def test_free_space_exactly_meeting_requirement_proceeds(self, tmp_path: Path) -> None:
        """D-09: free space equal to the requirement is enough, not one byte less."""
        segments = _write_segments(tmp_path, 4, 4096)
        exact_free = _required_merge_bytes(segments)
        output = tmp_path / "output.ts"
        (tmp_path / "batch_00000.ts").write_bytes(b"batch data")
        mock_process = _successful_process()

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(exact_free)),
            patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        ):
            result = await _merge_segments_batched(tmp_path, output, 4)

        assert result == output
        mock_exec.assert_called()

    @pytest.mark.asyncio
    async def test_free_space_one_byte_below_requirement_fails(self, tmp_path: Path) -> None:
        """D-09: one byte short of the requirement fails before any subprocess."""
        segments = _write_segments(tmp_path, 4, 4096)
        short_free = _required_merge_bytes(segments) - 1
        output = tmp_path / "output.ts"

        with (
            patch("shutil.disk_usage", return_value=_fake_disk_usage(short_free)),
            patch("asyncio.create_subprocess_exec") as mock_exec,
            pytest.raises(DownloadError),
        ):
            await _merge_segments_batched(tmp_path, output, 4)

        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_unreadable_volume_proceeds_with_merge(self, tmp_path: Path) -> None:
        """D-09: a volume whose usage cannot be read does not block the merge.

        An unreadable mount is not evidence of a full one, and a probe that
        failed for an unrelated reason must not turn a working download into a
        failure.
        """
        _write_segments(tmp_path, 5, 2048)
        output = tmp_path / "output.ts"
        (tmp_path / "batch_00000.ts").write_bytes(b"batch data")
        mock_process = _successful_process()

        with (
            patch("shutil.disk_usage", side_effect=OSError("unreadable mount")),
            patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        ):
            result = await _merge_segments_batched(tmp_path, output, 5)

        assert result == output
        mock_exec.assert_called()


class TestMergeFailureUrlRedaction:
    """SEC-002: signed CDN URLs redacted at both merge-failure log sinks."""

    @pytest.mark.asyncio
    async def test_batch_merge_failed_redacts_url(self, tmp_path: Path) -> None:
        """batch_merge_failed redacts signed URLs from stderr before logging."""
        segment = tmp_path / "00000.ts"
        segment.write_bytes(b"data")

        signed_url = "https://cdn.example.com/seg_00000.ts?token=SECRET123&sig=ABC"
        stderr_output = f"http error fetching {signed_url}: 403 Forbidden".encode()

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", stderr_output

        mock_process.communicate = mock_communicate

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger,
        ):
            result = await _merge_batch_segments([segment], tmp_path, 300)

            assert result is None
            mock_logger.error.assert_called_once()
            call = mock_logger.error.call_args
            assert call.args[0] == "batch_merge_failed"
            logged_error = call.kwargs["error"]
            assert "SECRET123" not in logged_error
            assert "ABC" not in logged_error
            assert "cdn.example.com" in logged_error

    @pytest.mark.asyncio
    async def test_batch_merge_failed_preserves_plaintext(self, tmp_path: Path) -> None:
        """batch_merge_failed passes plaintext stderr through unchanged."""
        segment = tmp_path / "00000.ts"
        segment.write_bytes(b"data")

        stderr_output = b"ffmpeg error: invalid data found in stream"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", stderr_output

        mock_process.communicate = mock_communicate

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger,
        ):
            result = await _merge_batch_segments([segment], tmp_path, 300)

            assert result is None
            mock_logger.error.assert_called_once()
            call = mock_logger.error.call_args
            assert call.args[0] == "batch_merge_failed"
            assert call.kwargs["error"] == "ffmpeg error: invalid data found in stream"

    @pytest.mark.asyncio
    async def test_final_merge_failed_redacts_url(self, tmp_path: Path) -> None:
        """final_merge_failed redacts signed URLs from stderr before logging."""
        temp_file = tmp_path / "batch_00000.ts"
        temp_file.write_bytes(b"data")
        output = tmp_path / "merged.ts"

        signed_url = "https://cdn.example.com/seg.m3u8?token=SECRET123&sig=ABC"
        stderr_output = f"Error fetching {signed_url}: 403 Forbidden".encode()

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", stderr_output

        mock_process.communicate = mock_communicate

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger,
        ):
            result = await _perform_final_merge([temp_file], output, 300)

            assert result is False
            mock_logger.error.assert_called_once()
            call = mock_logger.error.call_args
            assert call.args[0] == "final_merge_failed"
            logged_error = call.kwargs["error"]
            assert "SECRET123" not in logged_error
            assert "ABC" not in logged_error
            assert "cdn.example.com" in logged_error

    @pytest.mark.asyncio
    async def test_final_merge_failed_preserves_plaintext(self, tmp_path: Path) -> None:
        """final_merge_failed passes plaintext stderr through unchanged."""
        temp_file = tmp_path / "batch_00000.ts"
        temp_file.write_bytes(b"data")
        output = tmp_path / "merged.ts"

        stderr_output = b"ffmpeg error: invalid data found in stream"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", stderr_output

        mock_process.communicate = mock_communicate

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger,
        ):
            result = await _perform_final_merge([temp_file], output, 300)

            assert result is False
            mock_logger.error.assert_called_once()
            call = mock_logger.error.call_args
            assert call.args[0] == "final_merge_failed"
            assert call.kwargs["error"] == "ffmpeg error: invalid data found in stream"

    @pytest.mark.asyncio
    async def test_batch_merge_failed_host_survives_when_url_extends_past_200(
        self, tmp_path: Path
    ) -> None:
        """SEC-002/B14: the batch_merge_failed sink applies sanitize-then-truncate.

        The stderr is >200 chars and the signed URL's token starts past the
        200-char truncation point. With the correct order (sanitize → truncate)
        the URL shrinks to ``scheme://host/***REDACTED***/`` so the host survives
        the ``[:200]`` slice. Inverting to truncate → sanitize yields a 209-char
        string (the partial URL at [:200] still matches the redaction regex and
        expands to 39 chars), caught by the ``len == 200`` assertion.
        """
        segment = tmp_path / "00000.ts"
        segment.write_bytes(b"data")

        filler = "x" * 170
        signed_url = "https://cdn.example.com/seg.m3u8?token=SECRET123&sig=ABC"
        stderr_output = (filler + signed_url).encode()

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", stderr_output

        mock_process.communicate = mock_communicate

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger,
        ):
            result = await _merge_batch_segments([segment], tmp_path, 300)

            assert result is None
            mock_logger.error.assert_called_once()
            call = mock_logger.error.call_args
            assert call.args[0] == "batch_merge_failed"
            logged_error = call.kwargs["error"]
            assert "cdn.example.com" in logged_error
            assert "SECRET123" not in logged_error
            assert "ABC" not in logged_error
            assert len(logged_error) == 200

    @pytest.mark.asyncio
    async def test_final_merge_failed_host_survives_when_url_extends_past_200(
        self, tmp_path: Path
    ) -> None:
        """SEC-002/B14: the final_merge_failed sink applies sanitize-then-truncate."""
        temp_file = tmp_path / "batch_00000.ts"
        temp_file.write_bytes(b"data")
        output = tmp_path / "merged.ts"

        filler = "x" * 170
        signed_url = "https://cdn.example.com/seg.m3u8?token=SECRET123&sig=ABC"
        stderr_output = (filler + signed_url).encode()

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 1
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", stderr_output

        mock_process.communicate = mock_communicate

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger,
        ):
            result = await _perform_final_merge([temp_file], output, 300)

            assert result is False
            mock_logger.error.assert_called_once()
            call = mock_logger.error.call_args
            assert call.args[0] == "final_merge_failed"
            logged_error = call.kwargs["error"]
            assert "cdn.example.com" in logged_error
            assert "SECRET123" not in logged_error
            assert "ABC" not in logged_error
            assert len(logged_error) == 200


class TestSpawnBoundaryKwargs:
    """Tests that spawn sites apply the TRN-003 platform boundary keyword."""

    @pytest.mark.asyncio
    async def test_merge_batch_segments_passes_boundary(self, tmp_path: Path) -> None:
        """_merge_batch_segments passes the platform boundary keyword to the spawn."""
        from vkdownloader.services.ffmpeg_utils import _IS_WINDOWS

        segment1 = tmp_path / "00000.ts"
        segment2 = tmp_path / "00001.ts"
        segment1.write_bytes(b"segment1 data")
        segment2.write_bytes(b"segment2 data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await _merge_batch_segments([segment1, segment2], tmp_path, 300)

            call_kwargs = mock_exec.call_args[1]
            if _IS_WINDOWS:
                assert "creationflags" in call_kwargs
            else:
                assert call_kwargs["start_new_session"] is True

    @pytest.mark.asyncio
    async def test_perform_final_merge_passes_boundary(self, tmp_path: Path) -> None:
        """_perform_final_merge passes the platform boundary keyword to the spawn."""
        from vkdownloader.services.ffmpeg_utils import _IS_WINDOWS

        temp_file = tmp_path / "batch_00000.ts"
        temp_file.write_bytes(b"data")
        output = tmp_path / "merged.ts"

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await _perform_final_merge([temp_file], output, 300)

            call_kwargs = mock_exec.call_args[1]
            if _IS_WINDOWS:
                assert "creationflags" in call_kwargs
            else:
                assert call_kwargs["start_new_session"] is True

    @pytest.mark.asyncio
    async def test_download_with_ytdlp_passes_boundary(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """_download_with_ytdlp passes the platform boundary keyword to the spawn."""
        from vkdownloader.services.ffmpeg_utils import _IS_WINDOWS
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                output_file,
                "720",
                test_settings,
            )

            call_kwargs = mock_exec.call_args[1]
            if _IS_WINDOWS:
                assert "creationflags" in call_kwargs
            else:
                assert call_kwargs["start_new_session"] is True
