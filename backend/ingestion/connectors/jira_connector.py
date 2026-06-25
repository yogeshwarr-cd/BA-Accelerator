import asyncio
from typing import Dict, Any
from atlassian import Jira
from backend.ingestion.connectors.base_connector import BaseConnector
from backend.shared.exceptions import ConnectorAuthError
from backend.config import settings
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class JiraConnector(BaseConnector):
    """
    Ingests requirement inputs from Jira issues.
    """
    def __init__(self):
        self.client = None

    async def connect(self, connection_config: Dict[str, Any]) -> None:
        """
        Initializes Jira REST client with user credentials or global configuration.
        """
        url = connection_config.get("url") or settings.JIRA_API_URL
        username = connection_config.get("username") or settings.JIRA_USERNAME
        token = connection_config.get("token") or settings.JIRA_API_TOKEN

        if not url or not username or not token:
            raise ConnectorAuthError("Insufficient credentials provided for Jira authentication.")

        try:
            # Wrap blocking sync connector initialization in event loop executor thread pool
            def init_client():
                return Jira(url=url, username=username, password=token, cloud=True)
            self.client = await asyncio.to_thread(init_client)
            logger.info(f"Successfully authenticated with Jira instance: {url}")
        except Exception as e:
            raise ConnectorAuthError(f"Failed to authenticate with Jira: {str(e)}")

    async def fetch(self, identifier: str) -> str:
        """
        Retrieves issue summary, description, and comments, returning them as a unified text block.
        """
        if not self.client:
            raise ConnectorAuthError("Jira client connection not established. Call connect() first.")

        try:
            def fetch_issue():
                issue = self.client.issue(identifier)
                summary = issue.get("fields", {}).get("summary", "")
                desc = issue.get("fields", {}).get("description", "")
                comments = issue.get("fields", {}).get("comment", {}).get("comments", [])
                
                comment_text = "\n".join([f"Comment: {c.get('body')}" for c in comments])
                
                full_text = f"Jira Issue: {identifier}\nSummary: {summary}\nDescription: {desc}\n{comment_text}"
                return full_text

            return await asyncio.to_thread(fetch_issue)
        except Exception as e:
            logger.error(f"Error fetching issue {identifier} from Jira: {str(e)}")
            raise RuntimeError(f"Jira fetch failed: {str(e)}")

# INTEGRATION NOTE
# The JiraConnector integrates with Atlassian API. In local dev, configure JIRA_ API credentials in .env.
