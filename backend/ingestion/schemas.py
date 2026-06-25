from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class IngestionInput(BaseModel):
    """
    Schema representing a request to ingest a requirements document or connect to an external system.
    """
    source_type: str = Field(..., description="Source system type: JIRA, CONFLUENCE, SHAREPOINT, GDRIVE, or FILE")
    target_identifier: str = Field(..., description="Unique path, issue key, page URL, or document ID to ingest")
    connection_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Override runtime configuration details")

class IngestionOutput(BaseModel):
    """
    Schema representing processed requirements input text and layout metadata details.
    """
    raw_text: str = Field(..., description="Extracted raw text normalized from document parsing")
    fingerprint: str = Field(..., description="SHA256 checksum value of raw content")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata captured from the document header, length, file type")
    is_duplicate: bool = Field(default=False, description="Whether this document has been flagged as previously processed in Redis cache")

# INTEGRATION NOTE
# Member 1 (Ingestion) produces IngestionOutput, which is passed to the Orchestrator
# to populate the initial GraphState.
