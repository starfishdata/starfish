import requests
from typing import Optional
from .base_parser import BaseParser
import aiohttp


class WebParser(BaseParser):
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the web parser with optional Jina API key"""
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://r.jina.ai/"

    def parse(self, url: str) -> str:
        """
        Fetch and parse web content using Jina Reader API

        Args:
            url: The URL to fetch content from

        Returns:
            str: Clean, LLM-friendly text content
        """
        try:
            # Construct the full request URL
            request_url = f"{self.base_url}{url}"

            # Add headers if API key is provided
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Make the request
            response = requests.get(request_url, headers=headers)
            response.raise_for_status()

            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch content from {url}: {str(e)}")

    async def parse_async(self, url: str) -> str:
        """
        Asynchronously fetch and parse web content using Jina Reader API

        Args:
            url: The URL to fetch content from

        Returns:
            str: Clean, LLM-friendly text content
        """
        try:
            # Construct the full request URL
            request_url = f"{self.base_url}{url}"

            # Add headers if API key is provided
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Make the async request
            async with aiohttp.ClientSession() as session:
                async with session.get(request_url, headers=headers) as response:
                    response.raise_for_status()
                    return await response.text()
        except Exception as e:
            raise Exception(f"Failed to fetch content from {url}: {str(e)}")
