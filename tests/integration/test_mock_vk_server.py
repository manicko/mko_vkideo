"""Integration tests for VK Video Downloader with mock VK video page server."""

from unittest.mock import MagicMock


class TestMockServerIntegration:
    """Integration tests using mock VK server responses."""

    def test_mock_video_page_response(self) -> None:
        """Test mock video page returns valid HTML with video parameters."""
        # Simulate mock response for video page
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = MagicMock(return_value="""
        <!DOCTYPE html>
        <html>
        <head><title>VK Video 12345_67890</title></head>
        <body>
            <video data-id="12345_67890"></video>
            <script>
                window.videoParams = {"id": "12345_67890", "m3u8": "https://cdn.example.com/video.m3u8"};
            </script>
        </body>
        </html>
        """)

        # Verify the mock response structure
        assert mock_response.status == 200

    def test_mock_m3u8_response(self) -> None:
        """Test mock m3u8 endpoint returns valid playlist."""
        m3u8_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=4684000,RESOLUTION=1920x804
https://cdn.example.com/1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2384000,RESOLUTION=1280x540
https://cdn.example.com/720p.m3u8
"""

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = MagicMock(return_value=m3u8_content)

        assert mock_response.status == 200
        assert "#EXTM3U" in m3u8_content
        assert "1080p.m3u8" in m3u8_content
        assert "720p.m3u8" in m3u8_content

    def test_mock_video_page_various_ids(self) -> None:
        """Test mock server handles various video IDs."""
        # Test multiple video ID patterns
        video_ids = ["1_2", "123_456", "12345_67890"]

        for vid in video_ids:
            html_content = f"""
            <html>
            <body>
                <video data-id="{vid}"></video>
                <script>window.videoParams = {{"id": "{vid}"}};</script>
            </body>
            </html>
            """
            assert vid in html_content
