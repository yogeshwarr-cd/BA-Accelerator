import hashlib
from backend.db.redis_client import redis_client
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class Fingerprint:
    """
    Computes text hashes and performs duplicate detection inside Redis storage.
    """
    @staticmethod
    def calculate(text: str) -> str:
        """
        Computes SHA256 hash representation of normalized content text.
        """
        if not text:
            return hashlib.sha256(b"").hexdigest()
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    async def check_and_register(fingerprint_hash: str, job_id: str, expire_seconds: int = 86400) -> bool:
        """
        Checks if the document fingerprint is cached in Redis.
        If missing, registers the fingerprint under the active job ID and returns False (not duplicate).
        If present, returns True (is duplicate).
        """
        redis_key = f"fingerprint:{fingerprint_hash}"
        try:
            exists = await redis_client.exists(redis_key)
            if exists:
                logger.info(f"Duplicate document detected via fingerprint lookup: {fingerprint_hash}")
                return True
            
            # Register fingerprint with 24h expiration by default
            await redis_client.set(redis_key, job_id, expire_seconds=expire_seconds)
            logger.info(f"Registered document fingerprint {fingerprint_hash} under job {job_id}")
            return False
        except Exception as e:
            logger.error(f"Redis fingerprint validation error: {str(e)}. Permitting ingestion to proceed.")
            return False

# INTEGRATION NOTE
# Fingerprint check handles Redis service disruptions gracefully by logging warnings and proceeding.
