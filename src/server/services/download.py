import os
import requests
from typing import Optional
from ..interfaces import IDownloadStrategy, ILogger


class HTTPDownloadStrategy(IDownloadStrategy):
    """HTTP-based download strategy"""

    def __init__(self, logger: ILogger, chunk_size: int = 8192):
        self._logger = logger
        self._chunk_size = chunk_size

    def download(self, url: str, local_path: str) -> str:
        """Download file from HTTP URL to local path"""
        if os.path.exists(local_path):
            self._logger.info(f"File already exists at {local_path}")
            return local_path

        self._logger.info(f"Downloading from {url} to {local_path}")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self._chunk_size):
                    if chunk:
                        file.write(chunk)

            self._logger.info(f"Download completed: {local_path}")
            return local_path

        except requests.RequestException as e:
            self._logger.error(f"Download failed: {str(e)}")
            raise
        except IOError as e:
            self._logger.error(f"File write failed: {str(e)}")
            raise