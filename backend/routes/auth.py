"""Authentication and account provisioning endpoints backed by Supabase Auth."""

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

import backend.database as database

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)

# Admins are intentionally a global server-side allowlist, not a profile field
# or user metadata value. Add additional administrator emails here only.
ADMIN_EMAILS = frozenset({"garmadiuszy@gmail.com"})
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,24}$")
AVATAR_PATTERN = re.compile(r"^avatar_(0[1-8])$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value.strip()):
            raise ValueError("Email inválido.")
        return value.strip().casefold()


class CreateAccountRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    username: str = Field(min_length=3, max_length=24)
    display_name: str = Field(min_length=1, max_length=40)
    avatar_key: str = "avatar_01"
    temporary_password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value.strip()):
            raise ValueError("Email inválido.")
        return value.strip().casefold()


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


def _client_options() -> SyncClientOptions:
    return SyncClientOptions(auto_refresh_token=False, persist_session=False)


def _require_project_config() -> tuple[str, str]:
    url = database.SUPABASE_URL
    key = database.SUPABASE_KEY
    if not url or not key:
        raise HTTPException(status_code=503, detail="La autenticación no está configurada.")
    return url, key


def _get_service_client() -> Client:
    url, _ = _require_project_config()
    service_key = database.SUPABASE_SERVICE_KEY
    if not service_key:
        raise HTTPException(
            status_code=503,
            detail="Falta configurar la clave administrativa de Supabase en el backend.",
        )
    return create_client(url, service_key, options=_client_options())


def _public_profile(profile: dict[str, Any], email: str) -> dict[str, Any]:
    return {
        "id": profile["id"],
        "email": email,
        "username": profile["username"],
        "display_name": profile["display_name"],
        "avatar_key": profile["avatar_key"],
        "must_change_password": profile["must_change_password"],
        "is_admin": email.casefold() in ADMIN_EMAILS,
    }


def _profile_for_user(client: Client, user_id: str) -> dict[str, Any]:
    result = client.table("profiles").select("*").eq("id", user_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=403, detail="La cuenta no tiene un perfil configurado.")
    return result.data[0]


def resolve_access_token(access_token: str) -> dict[str, Any]:
    client = _get_service_client()
    try:
        response = client.auth.get_user(access_token)
        user = getattr(response, "user", None)
        if not user or not getattr(user, "id", None):
            raise HTTPException(status_code=401, detail="La sesión no es válida.")
        email = (getattr(user, "email", None) or "").casefold()
        profile = _profile_for_user(client, user.id)
        return {"user": user, "profile": _public_profile(profile, email)}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=401, detail="La sesión no es válida o expiró.") from error


def get_current_auth_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=401, detail="Inicia sesión para continuar.")
    return resolve_access_token(credentials.credentials)


def require_admin(auth: dict[str, Any] = Depends(get_current_auth_user)) -> dict[str, Any]:
    if not auth["profile"]["is_admin"]:
        raise HTTPException(status_code=403, detail="Solo un admin puede realizar esta acción.")
    return auth


@router.post("/login")
def login(data: LoginRequest) -> dict[str, Any]:
    url, _ = _require_project_config()
    public_key = database.SUPABASE_PUBLIC_KEY
    if not public_key:
        raise HTTPException(status_code=503, detail="Falta configurar la clave pública de Supabase.")
    client = create_client(url, public_key, options=_client_options())
    try:
        response = client.auth.sign_in_with_password(
            {"email": str(data.email).strip().casefold(), "password": data.password}
        )
        if not response.user or not response.session:
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")

        service_client = _get_service_client()
        profile = _profile_for_user(service_client, response.user.id)
        email = (response.user.email or "").casefold()
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": response.session.expires_in,
            "profile": _public_profile(profile, email),
        }
    except HTTPException:
        raise
    except Exception as error:
        # Do not disclose whether an email exists or expose Auth internals.
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.") from error


@router.post("/refresh")
def refresh_session(data: RefreshRequest) -> dict[str, Any]:
    url, _ = _require_project_config()
    public_key = database.SUPABASE_PUBLIC_KEY
    if not public_key:
        raise HTTPException(status_code=503, detail="Falta configurar la clave pública de Supabase.")
    client = create_client(url, public_key, options=_client_options())
    try:
        response = client.auth.refresh_session(data.refresh_token)
        if not response.user or not response.session:
            raise HTTPException(status_code=401, detail="La sesión expiró. Inicia sesión de nuevo.")
        service_client = _get_service_client()
        profile = _profile_for_user(service_client, response.user.id)
        email = (response.user.email or "").casefold()
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": response.session.expires_in,
            "profile": _public_profile(profile, email),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=401, detail="La sesión expiró. Inicia sesión de nuevo.") from error


@router.get("/me")
def get_me(auth: dict[str, Any] = Depends(get_current_auth_user)) -> dict[str, Any]:
    return {"profile": auth["profile"]}


@router.get("/me/history")
def get_my_room_history(auth: dict[str, Any] = Depends(get_current_auth_user)) -> dict[str, Any]:
    client = _get_service_client()
    result = client.table("user_room_history").select(
        "session_id, mode, started_at, finished_at, result_summary"
    ).eq("user_id", auth["user"].id).order("finished_at", desc=True).execute()
    return {"history": result.data or []}


@router.get("/me/trophies")
def get_my_trophies(auth: dict[str, Any] = Depends(get_current_auth_user)) -> dict[str, Any]:
    client = _get_service_client()
    result = client.table("user_trophies").select(
        "earned_at, source_session_id, trophies(id, title, description, icon_key)"
    ).eq("user_id", auth["user"].id).order("earned_at", desc=True).execute()
    return {"trophies": result.data or []}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    auth: dict[str, Any] = Depends(get_current_auth_user),
) -> dict[str, bool]:
    if not auth["profile"]["must_change_password"]:
        raise HTTPException(status_code=409, detail="La contraseña temporal ya fue cambiada.")
    if len(data.new_password) < 12:
        raise HTTPException(status_code=422, detail="La nueva contraseña debe tener al menos 12 caracteres.")

    client = _get_service_client()
    try:
        client.auth.admin.update_user_by_id(
            auth["user"].id,
            {"password": data.new_password},
        )
        client.table("profiles").update({"must_change_password": False}).eq(
            "id", auth["user"].id
        ).execute()
    except Exception as error:
        raise HTTPException(status_code=400, detail="No se pudo actualizar la contraseña.") from error
    return {"password_changed": True}


@router.post("/admin/accounts", status_code=201)
def create_account(
    data: CreateAccountRequest,
    auth: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    username = data.username.strip()
    display_name = data.display_name.strip()
    email = str(data.email).strip().casefold()
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(status_code=422, detail="El usuario solo admite letras, números y guion bajo (3-24 caracteres).")
    if not display_name:
        raise HTTPException(status_code=422, detail="El nombre visible no puede estar vacío.")
    if not AVATAR_PATTERN.fullmatch(data.avatar_key):
        raise HTTPException(status_code=422, detail="El avatar seleccionado no es válido.")

    client = _get_service_client()
    try:
        response = client.auth.admin.create_user({
            "email": email,
            "password": data.temporary_password,
            "email_confirm": True,
            "user_metadata": {
                "username": username,
                "display_name": display_name,
                "avatar_key": data.avatar_key,
                "must_change_password": True,
            },
        })
        user = response.user
        profile = _profile_for_user(client, user.id)
    except Exception as error:
        error_text = str(error).casefold()
        if "already" in error_text or "duplicate" in error_text or "unique" in error_text:
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email o usuario.") from error
        raise HTTPException(status_code=400, detail="No se pudo crear la cuenta.") from error

    return {"profile": _public_profile(profile, email), "created_by": auth["profile"]["id"]}
