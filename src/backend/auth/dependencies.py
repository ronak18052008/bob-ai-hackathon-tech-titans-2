"""
MedBrief AI — Server-Side RBAC & Authentication Dependencies
Step 4: Authentication + RBAC

Provides reusable FastAPI dependencies for:
- Authenticated user resolution (via cryptographically validated Bearer JWT)
- Authoritative server-side role resolution from DB (never trusting client input)
- Role verification guards (Doctor, Admin, Any)
- Patient-level access verification (via patient_user_access mapping)
"""

from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.backend.db.connection import get_db
from src.backend.db.models import User, Role, UserRole, PatientUserAccess
from src.backend.auth.security import decode_access_token, log_auth_audit_event

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate Bearer token, query authoritative application user profile,
    and resolve server-side roles from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials were not provided or have expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        # Check standard Authorization header fallback if OAuth2 scheme missed it
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user profile not found in system.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Please contact your clinical systems administrator.",
        )

    # Resolve roles authoritatively from the database
    role_records = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    user.roles_list = [r[0].lower() for r in role_records]

    return user


def require_role(required_role: str) -> Callable:
    """
    Factory creating a dependency that enforces a specific role.
    Raises 403 Forbidden and records an audit log if the user lacks the role.
    """
    normalized_target = required_role.strip().lower()

    def role_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_roles = getattr(current_user, "roles_list", [])
        if normalized_target not in user_roles:
            log_auth_audit_event(
                db=db,
                user_id=current_user.id,
                action="ACCESS_DENIED",
                resource_type="ROLE_GUARD",
                resource_id=required_role,
                metadata={
                    "required_role": required_role,
                    "assigned_roles": user_roles,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires '{required_role.upper()}' role.",
            )
        return current_user

    return role_dependency


def require_any_role(required_roles: List[str]) -> Callable:
    """
    Factory creating a dependency that allows any role from a list.
    """
    normalized_targets = [r.strip().lower() for r in required_roles]

    def any_role_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_roles = getattr(current_user, "roles_list", [])
        if not any(r in user_roles for r in normalized_targets):
            log_auth_audit_event(
                db=db,
                user_id=current_user.id,
                action="ACCESS_DENIED",
                resource_type="ROLE_GUARD",
                resource_id=",".join(required_roles),
                metadata={
                    "required_roles": required_roles,
                    "assigned_roles": user_roles,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of {required_roles}.",
            )
        return current_user

    return any_role_dependency


def can_user_access_patient(user_id: str, patient_id: str, db: Session) -> bool:
    """
    Core authorization check for patient-level medical record access.
    Admins have system-level audit access; clinicians require explicit patient_user_access mapping.
    """
    # 1. Check if user has admin role
    admin_check = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user_id, Role.name == "admin")
        .first()
    )
    if admin_check:
        return True

    # 2. Check patient_user_access mapping
    access_mapping = (
        db.query(PatientUserAccess)
        .filter(
            PatientUserAccess.user_id == user_id,
            PatientUserAccess.patient_id == patient_id,
        )
        .first()
    )
    return access_mapping is not None


def verify_patient_access(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> bool:
    """
    Reusable endpoint dependency for patient-level authorization.
    """
    has_access = can_user_access_patient(current_user.id, patient_id, db)
    if not has_access:
        log_auth_audit_event(
            db=db,
            user_id=current_user.id,
            action="ACCESS_DENIED",
            resource_type="PATIENT_RECORD",
            resource_id=patient_id,
            metadata={"reason": "No patient_user_access mapping"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Clinician is not authorized to access this patient record.",
        )
    return True


# Alias for explicit active-user semantics
get_current_active_user = get_current_user

