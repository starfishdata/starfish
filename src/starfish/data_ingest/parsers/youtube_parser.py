# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
# Download and save the transcript

import os
from typing import Dict, Any
from starfish.data_ingest.parsers.base_parser import BaseParser


class YouTubeParser(BaseParser):
    """Parser for YouTube transcripts"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = [".youtube", ".yt"]
        self.metadata = {}

    def parse(self, url: str) -> str:
        """Parse a YouTube video transcript

        Args:
            url: YouTube video URL

        Returns:
            Transcript text
        """
        try:
            from pytube import YouTube
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise ImportError(
                "pytube and youtube-transcript-api are required for YouTube parsing. " "Install them with: pip install pytube youtube-transcript-api"
            )

        # Extract video ID and metadata
        yt = YouTube(url)
        video_id = yt.video_id

        # Store metadata
        self.metadata = {
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "views": yt.views,
            "publish_date": yt.publish_date,
            "description": yt.description,
            "url": url,
        }

        # Get transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # Combine transcript segments
        combined_text = []
        for segment in transcript:
            combined_text.append(segment["text"])

        # Add video metadata
        metadata = f"Title: {yt.title}\n" f"Author: {yt.author}\n" f"Length: {yt.length} seconds\n" f"URL: {url}\n\n" f"Transcript:\n"

        return metadata + "\n".join(combined_text)

    def get_metadata(self) -> Dict[str, Any]:
        """Get video metadata

        Returns:
            Dictionary containing video metadata
        """
        return self.metadata

    def is_supported(self, url: str) -> bool:
        """Check if the URL is supported by this parser

        Args:
            url: YouTube URL or ID

        Returns:
            True if the URL is supported, False otherwise
        """
        return any(ext in url.lower() for ext in self.supported_extensions) or "youtube.com" in url.lower()
