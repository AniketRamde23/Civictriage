"""
Background threaded worker for non-blocking grievance classification (FR3).
Allows instant UI response (Status: 'Received') while Ollama processes in the background.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Optional
from core.classifier import classify_grievance
from core.db import update_grievance_classification

logger = logging.getLogger(__name__)

# Dedicated thread pool for async classification tasks
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="CivicTriageWorker")


def _worker_task(
    grievance_id: int,
    text: str,
    detected_lang: str,
    db_path: Optional[str] = None
) -> None:
    """Worker function executed in the background thread."""
    try:
        result = classify_grievance(text=text, detected_lang=detected_lang)
        update_grievance_classification(
            grievance_id=grievance_id,
            emotion=result["emotion"],
            priority=result["priority"],
            category=result["category"],
            english_summary=result["english_summary"],
            reason=result["reason"],
            status=result["status"],
            db_path=db_path
        )
    except Exception as e:
        logger.error(f"Error in background classification for grievance {grievance_id}: {e}")
        # Ensure status is set to Needs Review even on unexpected uncaught exceptions
        update_grievance_classification(
            grievance_id=grievance_id,
            emotion="Neutral",
            priority="Routine",
            category="Other",
            english_summary=text[:100],
            reason="Background worker encountered an internal exception. Queued for manual review.",
            status="Needs Review",
            db_path=db_path
        )


def submit_async_classification(
    grievance_id: int,
    text: str,
    detected_lang: str,
    db_path: Optional[str] = None
) -> None:
    """Submit a grievance classification job to the background thread pool."""
    _executor.submit(_worker_task, grievance_id, text, detected_lang, db_path)


def process_grievance_sync(
    grievance_id: int,
    text: str,
    detected_lang: str,
    db_path: Optional[str] = None
) -> dict:
    """Synchronous execution used for unit tests, evaluation scripts, or demo mode."""
    result = classify_grievance(text=text, detected_lang=detected_lang)
    update_grievance_classification(
        grievance_id=grievance_id,
        emotion=result["emotion"],
        priority=result["priority"],
        category=result["category"],
        english_summary=result["english_summary"],
        reason=result["reason"],
        status=result["status"],
        db_path=db_path
    )
    return result
