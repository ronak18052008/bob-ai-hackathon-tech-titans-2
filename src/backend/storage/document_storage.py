"""
MedBrief AI — Secure Document Storage Service
Step 7: PDF / Medical Document Upload & Ingestion Foundation

Provides private file storage abstraction for clinical documents.
Guarantees:
- Private, access-controlled filesystem storage (never in static/public directories)
- Strict path-traversal prevention (rejects '..', absolute paths, and symlink attacks)
- Sanitized filenames and deterministic object keys (patients/{patient_id}/documents/{document_id}/original.pdf)
- Safe transactional file cleanup upon database error
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_STORAGE_ROOT = BASE_DIR / "storage" / "documents"


def get_storage_root() -> Path:
    """Resolve authoritative private storage root directory from environment or fallback."""
    env_dir = os.getenv("STORAGE_DIR")
    if env_dir:
        p = Path(env_dir)
        if not p.is_absolute():
            p = BASE_DIR / p
    else:
        p = DEFAULT_STORAGE_ROOT
    p.mkdir(parents=True, exist_ok=True)
    return p


def sanitize_filename(filename: str) -> str:
    """Sanitize display filename to prevent path traversal or special character attacks."""
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    clean = re.sub(r'_+', '_', clean).strip('._')
    return clean or "medical_record.pdf"


def get_relative_object_path(patient_id: str, document_id: str) -> str:
    """Conceptual standardized relative path: patients/{patient_id}/documents/{document_id}/original.pdf"""
    return f"patients/{patient_id}/documents/{document_id}/original.pdf"


def get_safe_absolute_path(storage_path: str) -> Path:
    """
    Resolve absolute path from a stored relative path, strictly verifying that
    the resolved path stays within the designated storage root.
    """
    root = get_storage_root().resolve()
    # Normalize separators
    norm_path = storage_path.replace("\\", "/").strip("/")
    target = (root / norm_path).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        raise PermissionError("Path traversal violation: Access to path outside storage root is strictly prohibited.")

    return target


def store_document_bytes(patient_id: str, document_id: str, content: bytes) -> str:
    """
    Persist document binary content in private storage and return the relative storage path.
    """
    rel_path = get_relative_object_path(patient_id, document_id)
    target = get_safe_absolute_path(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "wb") as f:
        f.write(content)

    return rel_path


def read_document_bytes(storage_path: str) -> bytes:
    """Read binary content of a stored document with security validation."""
    target = get_safe_absolute_path(storage_path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError("Requested document file does not exist on storage.")

    with open(target, "rb") as f:
        return f.read()


def delete_stored_document(storage_path: str) -> bool:
    """Safely delete stored file (used during transaction rollback or cleanup)."""
    try:
        target = get_safe_absolute_path(storage_path)
        if target.exists() and target.is_file():
            target.unlink()
            # Also clean empty parent directory if possible
            parent = target.parent
            if parent.exists() and not any(parent.iterdir()):
                shutil.rmtree(parent, ignore_errors=True)
            return True
        return False
    except Exception as e:
        print(f"[WARN] Failed to delete document file at {storage_path}: {e}")
        return False
