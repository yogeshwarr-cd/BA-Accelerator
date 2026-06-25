from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseConnector(ABC):
    """
    Abstract interface defining methods required by every ingestion connector.
    """
    @abstractmethod
    async def connect(self, connection_config: Dict[str, Any]) -> None:
        """
        Validate authentication and establish connection to target system.
        """
        pass

    @abstractmethod
    async def fetch(self, identifier: str) -> str:
        """
        Retrieves raw content body from connector endpoint.
        """
        pass

# INTEGRATION NOTE
# All connectors (Jira, Confluence, SharePoint, GDrive) must subclass BaseConnector.
# Avoid importing models or agents here. Keep ingestion connectors strictly focused on data extraction.
