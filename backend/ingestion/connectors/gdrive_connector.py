import asyncio
import io
import json
from typing import Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from backend.ingestion.connectors.base_connector import BaseConnector
from backend.shared.exceptions import ConnectorAuthError
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class GDriveConnector(BaseConnector):
    """
    Ingests file resources from Google Drive directory locations.
    """
    def __init__(self):
        self.service = None

    async def connect(self, connection_config: Dict[str, Any]) -> None:
        """
        Builds Google Drive API client using service account keys.
        """
        credentials_json = connection_config.get("credentials_json") or settings.GOOGLE_DRIVE_CREDENTIALS_JSON
        
        if not credentials_json:
            raise ConnectorAuthError("Google Drive credentials path not specified in settings.")

        try:
            def build_service():
                if credentials_json.endswith(".json"):
                    creds = service_account.Credentials.from_service_account_file(
                        credentials_json, 
                        scopes=["https://www.googleapis.com/auth/drive.readonly"]
                    )
                else:
                    # Treat credentials_json as inline JSON dictionary string directly
                    creds_dict = json.loads(credentials_json)
                    creds = service_account.Credentials.from_service_account_info(
                        creds_dict,
                        scopes=["https://www.googleapis.com/auth/drive.readonly"]
                    )
                return build("drive", "v3", credentials=creds)

            self.service = await asyncio.to_thread(build_service)
            logger.info("Successfully established connection to Google Drive API.")
        except Exception as e:
            raise ConnectorAuthError(f"Failed to authenticate with Google Drive API: {str(e)}")

    async def fetch(self, identifier: str) -> str:
        """
        Downloads target file payload by ID. Automatically handles text conversion or exports docs.
        """
        if not self.service:
            raise ConnectorAuthError("Google Drive connection not established. Verify connect() runs first.")

        try:
            def download_file():
                # Fetch metadata to see mimeType
                file_metadata = self.service.files().get(fileId=identifier).execute()
                mime_type = file_metadata.get("mimeType", "")
                name = file_metadata.get("name", "untitled")

                # If Google Doc, export it as plaintext
                if mime_type == "application/vnd.google-apps.document":
                    request = self.service.files().export_media(fileId=identifier, mimeType="text/plain")
                else:
                    request = self.service.files().get_media(fileId=identifier)

                file_stream = io.BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.info(f"Downloading Google Drive file {identifier}: {int(status.progress() * 100)}%")

                payload = file_stream.getvalue()
                
                # Check if it can be decoded as text
                try:
                    text_content = payload.decode("utf-8")
                    return f"Google Drive File: {name}\nFileID: {identifier}\nContent:\n{text_content}"
                except UnicodeDecodeError:
                    return f"[BINARY_FILE] Google Drive File: {name}\nFileID: {identifier}\nLength: {len(payload)} bytes."

            return await asyncio.to_thread(download_file)
        except Exception as e:
            logger.error(f"Failed to download file {identifier} from Google Drive: {str(e)}")
            raise RuntimeError(f"Google Drive download error: {str(e)}")

# INTEGRATION NOTE
# Make sure Google Service Account email is added as a 'Viewer' to target documents/folders.
