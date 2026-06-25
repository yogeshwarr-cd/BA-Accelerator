import asyncio
from typing import Dict, Any
import re
from atlassian import Confluence
from backend.ingestion.connectors.base_connector import BaseConnector
from backend.shared.exceptions import ConnectorAuthError
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class ConfluenceConnector(BaseConnector):
    """
    Ingests page content from Confluence wiki spaces.
    """
    def __init__(self):
        self.client = None

    async def connect(self, connection_config: Dict[str, Any]) -> None:
        """
        Initializes Confluence client with configurations or env settings.
        """
        url = connection_config.get("url") or settings.CONFLUENCE_API_URL
        username = connection_config.get("username") or settings.CONFLUENCE_USERNAME
        token = connection_config.get("token") or settings.CONFLUENCE_API_TOKEN

        if not url or not username or not token:
            raise ConnectorAuthError("Insufficient credentials provided for Confluence authentication.")

        try:
            def init_client():
                return Confluence(url=url, username=username, password=token, cloud=True)
            self.client = await asyncio.to_thread(init_client)
            logger.info(f"Successfully authenticated with Confluence: {url}")
        except Exception as e:
            raise ConnectorAuthError(f"Failed to authenticate with Confluence: {str(e)}")

    async def fetch(self, identifier: str) -> str:
        """
        Retrieves page title and body content. Cleans html storage formatting tags.
        """
        if not self.client:
            raise ConnectorAuthError("Confluence client connection not established. Call connect() first.")

        try:
            def fetch_page():
                page = self.client.get_page_by_id(page_id=identifier, expand="body.storage")
                title = page.get("title", "")
                body_html = page.get("body", {}).get("storage", {}).get("value", "")
                
                # Basic regex removal of HTML tags for normalization
                clean_body = re.sub(r"<[^>]+>", " ", body_html)
                clean_body = re.sub(r"\s+", " ", clean_body).strip()
                
                return f"Confluence Page: {title}\nContent:\n{clean_body}"

            return await asyncio.to_thread(fetch_page)
        except Exception as e:
            logger.error(f"Error fetching page {identifier} from Confluence: {str(e)}")
            raise RuntimeError(f"Confluence fetch failed: {str(e)}")

# INTEGRATION NOTE
# Confluence page storage uses HTML formats. The fetch method strips HTML elements for text processing.
