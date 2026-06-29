import os
import uuid
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import APIIngestRequest, APIIngestResponse
from backend.api.middleware import verify_api_key
from backend.db.postgres import get_db_session
from backend.db.models import Job
from backend.ingestion.docling_loader import load_from_file
from backend.ingestion.text_normalizer import TextNormalizer
from backend.ingestion.fingerprint import Fingerprint

# Import connectors
from backend.ingestion.connectors.jira_connector import JiraConnector
from backend.ingestion.connectors.confluence_connector import ConfluenceConnector
from backend.ingestion.connectors.sharepoint_connector import SharePointConnector
from backend.ingestion.connectors.gdrive_connector import GDriveConnector

from backend.shared.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("", response_model=APIIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_requirements(
    payload: APIIngestRequest,
    db: AsyncSession = Depends(get_db_session),
    _auth: str = Depends(verify_api_key)
):
    """
    Ingests requirement document text from direct paths or connected sources.
    Calculates fingerprints and initializes pipeline jobs.
    """
    source_type = payload.source_type.upper()
    target = payload.target_identifier
    config_override = payload.connection_config or {}

    logger.info(f"Received Ingest request. Source: {source_type}, Target: {target}")

    # 1. Create a job record in DB
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        status="PENDING",
        source_type=source_type,
        config=config_override
    )
    db.add(job)
    await db.commit()

    raw_text = ""

    try:
        # 2. Retrieve content based on connector selection
        if source_type == "FILE":
            raw_text = await load_from_file(target)
            
        elif source_type == "JIRA":
            conn = JiraConnector()
            await conn.connect(config_override)
            raw_text = await conn.fetch(target)
            
        elif source_type == "CONFLUENCE":
            conn = ConfluenceConnector()
            await conn.connect(config_override)
            raw_text = await conn.fetch(target)
            
        elif source_type == "SHAREPOINT":
            conn = SharePointConnector()
            await conn.connect(config_override)
            raw_text = await conn.fetch(target)
            
        elif source_type == "GDRIVE":
            conn = GDriveConnector()
            await conn.connect(config_override)
            raw_text = await conn.fetch(target)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported source type '{source_type}'. Use FILE, JIRA, CONFLUENCE, SHAREPOINT, or GDRIVE."
            )

        # 3. Text clean-up and normalization
        cleaned_text = TextNormalizer.clean(raw_text)
        lang = TextNormalizer.detect_language(cleaned_text)

        # 4. Fingerprint checks
        fingerprint_hash = Fingerprint.calculate(cleaned_text)
        is_duplicate = await Fingerprint.check_and_register(fingerprint_hash, job_id)

        # 5. Persist retrieved text and status to job DB
        job.meta_info = {
            "fingerprint": fingerprint_hash,
            "language": lang,
            "char_count": len(cleaned_text),
            "target": target
        }
        
        # We can temporarily store the text on the job's model or a local S3/MinIO bucket.
        # For simplicity and compliance, store layout directly in a local text file named after the job_id
        # inside a workspace temp folder or on the Job model itself.
        # Let's save to a localized directory: backend/data/requirements/<job_id>.txt
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "requirements")
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, f"{job_id}.txt")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        await db.commit()

        return APIIngestResponse(
            job_id=job_id,
            fingerprint=fingerprint_hash,
            is_duplicate=is_duplicate,
            status="PENDING"
        )

    except Exception as e:
        logger.error(f"Failed ingestion flow for target {target}: {str(e)}")
        # Update Job status to fail
        job.status = "FAILED"
        job.error_message = str(e)
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion process failed: {str(e)}"
        )

# INTEGRATION NOTE
# Connector initialization is blocking. This endpoint runs them inside thread executors.
