from __future__ import annotations

import os
import time
from datetime import date
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

DB_DSN = os.getenv("DB_DSN", "postgresql://app:app@db:5432/app")
CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
"""


CREATE_OBJECTIVES_SQL = """
CREATE TABLE IF NOT EXISTS objectives (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    period DATE NOT NULL
);
"""

CREATE_KEY_RESULTS_SQL = """
CREATE TABLE IF NOT EXISTS key_results (
    id SERIAL PRIMARY KEY,
    objective_id INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    metric TEXT NOT NULL,
    progress NUMERIC(5,2) NOT NULL DEFAULT 0
);
"""


def get_conn():
    return psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor)


def init_db(retries: int = 10, delay: float = 1.0):
    for _ in range(retries):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(CREATE_USERS_SQL)
                    cur.execute(CREATE_OBJECTIVES_SQL)
                    cur.execute(CREATE_KEY_RESULTS_SQL)
                conn.commit()
            return
        except psycopg2.OperationalError:
            time.sleep(delay)
    raise RuntimeError("DB is not ready")


def get_user_by_id(cur, user_id: Any) -> dict[str, Any] | None:
    cur.execute(
        "SELECT id, name FROM users WHERE id = %s",
        (user_id,),
    )
    return cur.fetchone()


def create_user_db(name: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name)
                VALUES (%s)
                RETURNING id, name
                """,
                (name,),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def get_user_db(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name FROM users WHERE id = %s",
                (user_id,),
            )
            return cur.fetchone()


def create_objective_db(user_id: int, title: str, period: date) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO objectives (user_id, title, period)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, title, period
                """,
                (user_id, title, period),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def list_objectives_for_user_db(user_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, title, period
                FROM objectives
                WHERE user_id = %s
                ORDER BY id
                """,
                (user_id,),
            )
            return cur.fetchall()


def get_objective_db(obj_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, title, period
                FROM objectives
                WHERE id = %s
                """,
                (obj_id,),
            )
            return cur.fetchone()


def create_key_result_db(
    objective_id: int,
    title: str,
    metric: str,
    progress: float,
) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO key_results (objective_id, title, metric, progress)
                VALUES (%s, %s, %s, %s)
                RETURNING id, objective_id, title, metric, progress
                """,
                (objective_id, title, metric, progress),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def list_key_results_for_objective_db(obj_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, objective_id, title, metric, progress
                FROM key_results
                WHERE objective_id = %s
                ORDER BY id
                """,
                (obj_id,),
            )
            return cur.fetchall()
