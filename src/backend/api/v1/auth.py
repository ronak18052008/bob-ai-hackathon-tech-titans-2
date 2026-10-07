"""
MedBrief AI — Authentication & RBAC API Router
Step 4: Authentication + RBAC

Provides REST endpoints for:
- User login (with demo accounts and token generation)
- Current user profile resolution (GET /api/v1/auth/me)
- Secure session sign-out (POST /api/v1/auth/logout)
- Role verification probes (Doctor vs Admin access checks)
- Patient-level authorization probes
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.backend.db.connection import get_db
from src.backend.db.models import User, Role, UserRole, UserPreference, utc_now
from src.backend.auth.security import (
    create_access_token,
    log_auth_audit_event,
    hash_password,
    verify_password,
)
from src.backend.auth.dependencies import (
    get_current_user,
    require_role,
    verify_patient_access,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & RBAC"])


# ── Pydantic Request & Response Schemas ──────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class SafeUserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role_title: Optional[str] = None
    medical_license_id: Optional[str] = None
    roles: List[str]
    is_active: bool


class UpdateProfileRequest(BaseModel):
    display_name: str
    role_title: Optional[str] = None
    medical_license_id: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


class UserPreferencesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: str = "light"
    reduced_motion: bool = False
    density: str = "comfortable"
    notify_in_app: bool = True
    notify_doc_processing: bool = True
    notify_ai_completion: bool = True
    notify_follow_up_alerts: bool = True
    default_dashboard_view: str = "dashboard"
    default_summary_type: str = "CLINICAL_BRIEF"
    results_per_page: int = 10
    date_format: str = "YYYY-MM-DD"


class StandardActionResponse(BaseModel):
    status: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: SafeUserProfile


class LogoutResponse(BaseModel):
    status: str
    message: str


class AccessCheckResponse(BaseModel):
    status: str
    role: str
    user_id: str
    display_name: str
    scope: str


class PatientAccessResponse(BaseModel):
    status: str
    patient_id: str
    user_id: str
    access_granted: bool


# ── Demo Account Aliases ─────────────────────────────────────────────────────
# Maps common development/demo aliases to seeded clinical accounts
DEMO_EMAIL_ALIASES = {
    "doctor.demo@medbrief.local": "dr.sarah.chen@demo-clinic.test",
    "admin.demo@medbrief.local": "admin@demo-clinic.test",
}

# Accepted passwords for local demo accounts
DEMO_PASSWORDS = {"MedBrief2026!", "MedBriefAdmin2026!", "demo123", "doctor123", "admin123"}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user credentials, resolve database identity, and issue a signed JWT.
    Supports seeded clinical demo accounts and production users.
    """
    raw_email = credentials.email.strip().lower()
    resolved_email = DEMO_EMAIL_ALIASES.get(raw_email, raw_email)

    # 1. Lookup user in database
    user = db.query(User).filter(User.email == resolved_email).first()

    # 2. Validate user existence and status
    if not user:
        log_auth_audit_event(
            db=db,
            user_id=None,
            action="AUTH_FAILURE",
            resource_type="USER_LOGIN",
            resource_id=raw_email,
            metadata={"reason": "User not found", "attempted_email": raw_email},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your clinical email and password.",
        )

    if not user.is_active:
        log_auth_audit_event(
            db=db,
            user_id=user.id,
            action="AUTH_FAILURE",
            resource_type="USER_LOGIN",
            resource_id=user.email,
            metadata={"reason": "Account deactivated"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact your clinical systems administrator.",
        )

    # 3. Password verification (verifies password_hash or fallback demo credentials)
    provided_password = credentials.password.strip()
    is_valid_pw = False
    if user.password_hash:
        is_valid_pw = verify_password(provided_password, user.password_hash)
    else:
        is_valid_pw = provided_password in DEMO_PASSWORDS

    if not is_valid_pw:
        log_auth_audit_event(
            db=db,
            user_id=user.id,
            action="AUTH_FAILURE",
            resource_type="USER_LOGIN",
            resource_id=user.email,
            metadata={"reason": "Invalid password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your clinical email and password.",
        )

    # 4. Resolve roles from database
    role_records = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    roles = [r[0].lower() for r in role_records]

    # 5. Issue JWT token
    token = create_access_token(data={
        "sub": user.id,
        "email": user.email,
        "roles": roles,
    })

    # 6. Audit successful login
    log_auth_audit_event(
        db=db,
        user_id=user.id,
        action="LOGIN",
        resource_type="USER_SESSION",
        resource_id=user.id,
        metadata={"email": user.email, "roles": roles},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=60 * 60 * 8,  # 8 hours in seconds
        user=SafeUserProfile(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role_title=user.role_title,
            medical_license_id=user.medical_license_id,
            roles=roles,
            is_active=user.is_active,
        ),
    )


@router.get("/me", response_model=SafeUserProfile)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieve authenticated application user profile and authoritative database roles.
    Never exposes internal hashes, secrets, or tokens.
    """
    return SafeUserProfile(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role_title=current_user.role_title,
        medical_license_id=current_user.medical_license_id,
        roles=getattr(current_user, "roles_list", []),
        is_active=current_user.is_active,
    )


@router.put("/me", response_model=SafeUserProfile)
def update_profile(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update editable profile fields for the authenticated clinician.
    Persists display_name, role_title, and medical_license_id to the users table.
    """
    name = req.display_name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full Name / Display Name cannot be empty.",
        )

    current_user.display_name = name
    if req.role_title is not None:
        current_user.role_title = req.role_title.strip() or None
    if req.medical_license_id is not None:
        current_user.medical_license_id = req.medical_license_id.strip() or None
    current_user.updated_at = utc_now()
    db.commit()
    db.refresh(current_user)

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PROFILE_UPDATE",
        resource_type="USER_PROFILE",
        resource_id=current_user.id,
        metadata={"display_name": current_user.display_name},
    )

    return SafeUserProfile(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role_title=current_user.role_title,
        medical_license_id=current_user.medical_license_id,
        roles=getattr(current_user, "roles_list", []),
        is_active=current_user.is_active,
    )


@router.post("/change-password", response_model=StandardActionResponse)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely update password for authenticated user.
    Verifies current password, enforces security standards,
    and stores PBKDF2-HMAC-SHA256 salted hash without logging plaintext passwords.
    """
    curr_pw = req.current_password.strip()
    new_pw = req.new_password.strip()
    conf_pw = req.confirm_password.strip()

    # 1. Verify current password
    if current_user.password_hash:
        if not verify_password(curr_pw, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
    else:
        if curr_pw not in DEMO_PASSWORDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

    # 2. Check confirm password match
    if new_pw != conf_pw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    # 3. Security requirements validation
    if len(new_pw) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet the required security requirements: Must be at least 8 characters long.",
        )
    if not any(c.isupper() for c in new_pw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet the required security requirements: Must contain at least one uppercase letter.",
        )
    if not any(c.islower() for c in new_pw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet the required security requirements: Must contain at least one lowercase letter.",
        )
    if not any(c.isdigit() for c in new_pw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet the required security requirements: Must contain at least one digit.",
        )
    special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?/~`")
    if not any(c in special_chars for c in new_pw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet the required security requirements: Must contain at least one special character.",
        )

    # 4. Hash and persist
    current_user.password_hash = hash_password(new_pw)
    current_user.updated_at = utc_now()
    db.commit()

    # 5. Audit event (never logging the password!)
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PASSWORD_CHANGE",
        resource_type="USER_ACCOUNT",
        resource_id=current_user.id,
        metadata={"email": current_user.email},
    )

    return StandardActionResponse(
        status="ok",
        message="Password changed successfully.",
    )


@router.get("/preferences", response_model=UserPreferencesSchema)
def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve stored UI and application preferences for the authenticated user.
    Initializes default preferences if not previously created.
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.put("/preferences", response_model=UserPreferencesSchema)
def update_user_preferences(
    req: UserPreferencesSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update UI and application preferences for the authenticated user.
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)

    pref.theme = req.theme
    pref.reduced_motion = req.reduced_motion
    pref.density = req.density
    pref.notify_in_app = req.notify_in_app
    pref.notify_doc_processing = req.notify_doc_processing
    pref.notify_ai_completion = req.notify_ai_completion
    pref.notify_follow_up_alerts = req.notify_follow_up_alerts
    pref.default_dashboard_view = req.default_dashboard_view
    pref.default_summary_type = req.default_summary_type
    pref.results_per_page = req.results_per_page
    pref.date_format = req.date_format
    pref.updated_at = utc_now()
    db.commit()
    db.refresh(pref)

    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="PREFERENCES_UPDATE",
        resource_type="USER_PREFERENCES",
        resource_id=current_user.id,
        metadata={"theme": pref.theme, "reduced_motion": pref.reduced_motion},
    )

    return pref


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Explicitly sign out and record a LOGOUT audit event.
    """
    log_auth_audit_event(
        db=db,
        user_id=current_user.id,
        action="LOGOUT",
        resource_type="USER_SESSION",
        resource_id=current_user.id,
        metadata={"email": current_user.email},
    )
    return LogoutResponse(
        status="ok",
        message="Successfully signed out of clinical session.",
    )


# ── RBAC Verification Probe Endpoints ────────────────────────────────────────

@router.get("/doctor-access", response_model=AccessCheckResponse)
def check_doctor_access(current_user: User = Depends(require_role("doctor"))):
    """
    Protected route requiring DOCTOR role.
    Verifies that clinical physicians can access doctor-scoped resources.
    """
    return AccessCheckResponse(
        status="authorized",
        role="doctor",
        user_id=current_user.id,
        display_name=current_user.display_name,
        scope="clinical_decision_support_shell",
    )


@router.get("/admin-access", response_model=AccessCheckResponse)
def check_admin_access(current_user: User = Depends(require_role("admin"))):
    """
    Protected route requiring ADMIN role.
    Verifies that administrative users can access audit and user management resources.
    """
    return AccessCheckResponse(
        status="authorized",
        role="admin",
        user_id=current_user.id,
        display_name=current_user.display_name,
        scope="system_administration_and_audit_shell",
    )


@router.get("/patient-access/{patient_id}", response_model=PatientAccessResponse)
def check_patient_access(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    _authorized: bool = Depends(verify_patient_access),
):
    """
    Protected route enforcing patient-level authorization via patient_user_access.
    """
    return PatientAccessResponse(
        status="authorized",
        patient_id=patient_id,
        user_id=current_user.id,
        access_granted=True,
    )
