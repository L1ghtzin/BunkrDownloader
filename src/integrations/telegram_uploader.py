"""Module for handling Telegram uploads."""

import os
import requests
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.managers.live_manager import LiveManager

TELEGRAM_API_URL = "https://giftedtech-tgbotapi.hf.space"

class TelegramUploader:
    """Class to handle uploading files via a custom Telegram Bot API server."""

    def __init__(self, token: str | None = None) -> None:
        """Initialize the Telegram Uploader with the bot token."""
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError(
                "Telegram Bot Token is required for uploading. Provide it via "
                "--tg-token or TELEGRAM_BOT_TOKEN environment variable."
            )
        
        self.base_url = f"{TELEGRAM_API_URL}/bot{self.token}"

    def upload_file(
        self,
        chat_id: str,
        file_path: Path,
        message_thread_id: int | None = None,
        live_manager: "LiveManager" | None = None,
    ) -> bool:
        """Upload a video or document to Telegram."""
        if not file_path.exists():
            if live_manager:
                live_manager.update_log(
                    event="Upload Error", details=f"File not found: {file_path.name}"
                )
            return False

        if live_manager:
            live_manager.update_log(
                event="Telegram Upload",
                details=f"Uploading {file_path.name} to Telegram...",
            )

        endpoint = f"{self.base_url}/sendVideo"
        
        data: dict[str, Any] = {
            "chat_id": chat_id,
            "supports_streaming": "true"
        }
        
        if message_thread_id:
            data["message_thread_id"] = message_thread_id

        try:
            with file_path.open("rb") as f:
                # We use 'video' parameter for sendVideo.
                files = {"video": f}
                # Use a larger timeout since we're uploading large files
                response = requests.post(endpoint, data=data, files=files, timeout=3600)
                
                # Fallback to sendDocument if sendVideo fails
                if response.status_code == 400 and "video" not in response.text.lower():
                    if live_manager:
                        live_manager.update_log(
                            event="Telegram Upload", details="Falling back to sendDocument..."
                        )
                    endpoint = f"{self.base_url}/sendDocument"
                    f.seek(0)
                    files = {"document": f}
                    response = requests.post(
                        endpoint,
                        data={k: v for k, v in data.items() if k != "supports_streaming"},
                        files=files,
                        timeout=3600
                    )

            response.raise_for_status()
            
            if live_manager:
                live_manager.update_log(
                    event="Telegram Upload",
                    details=f"Successfully uploaded {file_path.name} to Telegram!",
                )
            return True

        except requests.exceptions.RequestException as e:
            if live_manager:
                live_manager.update_log(
                    event="Telegram Error",
                    details=f"Failed to upload {file_path.name}: {e}"
                )
            return False
