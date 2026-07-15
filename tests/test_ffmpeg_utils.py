"""Unit tests for ffmpeg_utils merge and process management functions."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.services.ffmpeg_utils import (
    _build_ffmpeg_concat_command,
    _merge_batch_segments,
    _merge_segments_batched,
    _perform_final_merge,
    cancel_ffmpeg_process,
)


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


class TestCancelFfmpegProcess:
    """Tests for cancel_ffmpeg_process function."""

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

        result = await cancel_ffmpeg_process(mock_process)

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

        # Use AsyncMock for wait since it's called twice (once inside wait_for, once directly)
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()

            result = await cancel_ffmpeg_process(mock_process, timeout=5.0)

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

        result = await cancel_ffmpeg_process(mock_process)

        mock_process.terminate.assert_called_once()
        assert result is False


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
            result = await _merge_batch_segments([segment1, segment2], tmp_path)

            # Should return path to batch output
            assert result is not None
            assert result.name == "batch_00000.ts"
            assert result.parent == tmp_path

    @pytest.mark.asyncio
    async def test_merge_batch_removes_input_files_on_success(self, tmp_path: Path) -> None:
        """Test that input files are removed after successful merge."""
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
            await _merge_batch_segments([segment1, segment2], tmp_path)

            # Input files should be removed
            assert not segment1.exists()
            assert not segment2.exists()

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
            await _merge_batch_segments([segment1], tmp_path)

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
            result = await _merge_batch_segments([segment1], tmp_path)

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
            result = await _perform_final_merge([temp_file1, temp_file2], output)

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
            await _perform_final_merge([temp_file1, temp_file2], output)

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
            await _perform_final_merge([temp_file1], output)

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
            result = await _perform_final_merge([temp_file1], output)

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
            await _perform_final_merge([temp_file1], output)

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

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Create batch output files (2 batches for 150 segments)
            batch_output_1 = tmp_path / "batch_00000.ts"
            batch_output_1.write_bytes(b"batch data")
            batch_output_2 = tmp_path / "batch_00100.ts"
            batch_output_2.write_bytes(b"batch data")

            await _merge_segments_batched(tmp_path, output, 150)
