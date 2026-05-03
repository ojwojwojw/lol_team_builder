from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .queries.auth_query import get_user_by_id


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JWT_SECRET_FILE = PROJECT_ROOT / ".jwt_secret"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
PASSWORD_HASH_ITERATIONS = 200_000

# FastAPI 라우터에서 Authorization: Bearer <token> 헤더를 읽을 때 쓰는 표준 helper.
# auto_error=False 로 둬서, 토큰이 없을 때 우리가 직접 한글 에러 메시지를 제어한다.
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    # 비밀번호는 절대 평문 저장하지 않는다.
    # salt 를 사용자별로 따로 두고 PBKDF2-HMAC-SHA256 반복 해시로 저장한다.
    raw_salt = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        raw_salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return hashed.hex(), raw_salt.hex()


def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    # 로그인 시에는 사용자가 입력한 평문 비밀번호를 같은 salt 로 다시 해시해서
    # DB 에 저장된 해시와 상수 시간 비교(hmac.compare_digest) 한다.
    candidate_hash, _ = hash_password(password, stored_salt)
    return hmac.compare_digest(candidate_hash, stored_hash)


def create_access_token(user: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    # JWT payload 에는 최소한의 정보만 넣는다.
    # sub: 사용자 식별용 id
    # username: 클라이언트 표시에 유용
    # is_admin: 관리자 전용 화면/엔드포인트 구분
    # exp: 만료 시각
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "is_admin": bool(user.get("is_admin")),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return _encode_jwt(payload)


def decode_access_token(token: str) -> dict:
    # JWT 는 header.payload.signature 세 부분으로 나뉜다.
    # 여기서는 직접 서명 검증과 만료 검사를 수행한다.
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise _unauthorized("유효하지 않은 인증 토큰 형식입니다.") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = _sign(signing_input)
    actual_signature = _urlsafe_b64decode(signature_b64)

    if not hmac.compare_digest(expected_signature, actual_signature):
        raise _unauthorized("토큰 서명이 일치하지 않습니다.")

    # 서명 검증이 끝난 뒤에만 payload JSON 을 신뢰한다.
    payload = json.loads(_urlsafe_b64decode(payload_b64).decode("utf-8"))
    exp = int(payload.get("exp", 0))
    now_timestamp = int(datetime.now(timezone.utc).timestamp())
    if exp <= now_timestamp:
        raise _unauthorized("토큰이 만료되었습니다.")

    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    # 이 함수가 "토큰 -> 실제 사용자 계정" 연결의 핵심이다.
    # 1) Authorization 헤더에서 Bearer 토큰 추출
    # 2) JWT 서명/만료 검증
    # 3) payload.sub 로 DB 에서 app_user 조회
    # 4) 비활성 계정이면 차단
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("로그인이 필요합니다.")

    payload = decode_access_token(credentials.credentials)
    user_id = int(payload.get("sub", 0) or 0)
    user = get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        raise _unauthorized("사용할 수 없는 계정입니다.")

    return user


def require_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    # 관리자 전용 API 는 먼저 일반 인증을 통과한 뒤,
    # app_user.is_admin 값으로 한 번 더 권한을 확인한다.
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return current_user


def get_jwt_secret() -> str:
    # 서버 서명키는 로컬 파일(server/.jwt_secret)에 저장해 재시작 후에도 유지한다.
    # 이 파일은 gitignore 에 포함되어 있으므로 배포 서버마다 별도 비밀키를 갖게 된다.
    if JWT_SECRET_FILE.exists():
        return JWT_SECRET_FILE.read_text(encoding="utf-8").strip()

    secret = secrets.token_urlsafe(48)
    JWT_SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret


def _encode_jwt(payload: dict) -> str:
    # JWT 직렬화:
    # 1) header JSON
    # 2) payload JSON
    # 3) header.payload 에 대해 HMAC-SHA256 서명
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_b64 = _urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_b64 = _urlsafe_b64encode(_sign(signing_input))
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _sign(message: bytes) -> bytes:
    # 실제 서명 계산은 오직 이 함수 하나에서만 수행한다.
    secret = get_jwt_secret().encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).digest()


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
