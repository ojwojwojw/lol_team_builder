from fastapi import APIRouter, Body, Depends

from ..models.request_models import (
    AuthBootstrapRequest,
    CreateUserRequest,
    LoginRequest,
)
from ..security import get_current_user, require_admin_user
from ..services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])
auth_service = AuthService()


@router.get("/setup-status")
def get_setup_status():
    # 새 PC/새 클라이언트에서는 이 값을 보고
    # "최초 관리자 생성" 버튼을 보여줄지 숨길지 결정한다.
    return auth_service.get_setup_status()


@router.post("/bootstrap-admin")
def bootstrap_admin(req: AuthBootstrapRequest = Body(...)):
    # 최초 한 번만 가능한 관리자 계정 생성.
    # 다른 PC 에서 클라이언트를 켜더라도 DB 에 이미 계정이 있으면 더 이상 성공하지 않는다.
    """Create the very first admin account exactly once."""
    return auth_service.bootstrap_admin(req.username, req.password)


@router.post("/login")
def login(req: LoginRequest = Body(...)):
    # 클라이언트는 여기서 받은 access_token 을 로컬 config 에 저장해 두고,
    # 이후 모든 보호 API 요청에 Bearer 토큰으로 다시 보낸다.
    """Issue a JWT access token for one existing user."""
    return auth_service.login(req.username, req.password)


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    # "지금 저장된 토큰이 아직 유효한가?"를 클라이언트가 확인할 때 사용한다.
    """Return the current authenticated user."""
    return auth_service.get_me(current_user)


@router.get("/users")
def list_users(_: dict = Depends(require_admin_user)):
    # 관리자 전용 계정 관리 화면이 이 엔드포인트를 사용한다.
    """List known app users for the admin."""
    return auth_service.list_members()


@router.post("/users")
def create_user(
    req: CreateUserRequest = Body(...),
    _: dict = Depends(require_admin_user),
):
    # 관리자만 친구 계정을 만들어 줄 수 있다.
    """Create one friend account from the admin panel flow."""
    return auth_service.create_member(req.username, req.password)
