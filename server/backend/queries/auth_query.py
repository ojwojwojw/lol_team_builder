from __future__ import annotations

from ..database import get_connection


def count_users() -> int:
    # 최초 관리자 생성 가능 여부를 판단할 때 사용한다.
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM app_user")
        row = cursor.fetchone()
        return int(row[0] if row else 0)
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    # 로그인 단계에서 아이디로 app_user 를 조회한다.
    conn = get_connection()
    conn.row_factory = _row_factory
    try:
        cursor = conn.execute(
            """
            SELECT id, username, password_hash, password_salt, is_admin, is_active, created_at
            FROM app_user
            WHERE lower(username) = lower(?)
            """,
            (username,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    # JWT payload.sub 를 실제 DB 사용자로 다시 매핑할 때 사용한다.
    conn = get_connection()
    conn.row_factory = _row_factory
    try:
        cursor = conn.execute(
            """
            SELECT id, username, password_hash, password_salt, is_admin, is_active, created_at
            FROM app_user
            WHERE id = ?
            """,
            (user_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def create_user(
    username: str,
    password_hash: str,
    password_salt: str,
    is_admin: bool = False,
) -> dict:
    # 계정 생성은 이 함수 하나로 모아서 app_user 쓰기 경로를 단순화한다.
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO app_user (username, password_hash, password_salt, is_admin, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (username, password_hash, password_salt, int(is_admin)),
        )
        conn.commit()
        user_id = cursor.lastrowid
    finally:
        conn.close()

    return get_user_by_id(user_id) or {}


def list_users() -> list[dict]:
    # 관리자 UI 에서 app_user 목록을 표로 보여줄 때 사용한다.
    conn = get_connection()
    conn.row_factory = _row_factory
    try:
        cursor = conn.execute(
            """
            SELECT id, username, is_admin, is_active, created_at
            FROM app_user
            ORDER BY created_at ASC, id ASC
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def _row_factory(cursor, row):
    return {
        cursor.description[index][0]: row[index]
        for index in range(len(cursor.description))
    }
