"""API 인증 및 사용량 제한 미들웨어"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from aiosqlite import connect, Connection
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# API Key 헤더 정의
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthMiddleware:
    """API 인증 및 사용량 제한 관리"""

    def __init__(self, db_path: str = "./usage.db", monthly_limit: int = 100):
        """
        인증 미들웨어 초기화

        Args:
            db_path: 데이터베이스 파일 경로
            monthly_limit: 월 사용량 제한
        """
        self.db_path = db_path
        self.monthly_limit = monthly_limit
        self.valid_api_keys = self._load_api_keys()

    def _load_api_keys(self) -> set:
        """환경변수에서 API 키 로드"""
        api_keys_str = os.getenv("API_KEYS", "")
        return set(key.strip() for key in api_keys_str.split(",") if key.strip())

    async def _init_db(self):
        """데이터베이스 초기화"""
        async with connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_key_timestamp
                ON api_usage(api_key, timestamp)
            """)
            await db.commit()

    async def _check_usage_limit(self, api_key: str) -> tuple[bool, int]:
        """
        월 사용량 제한 확인

        Args:
            api_key: API 키

        Returns:
            (제한 통과 여부, 현재 사용량)
        """
        await self._init_db()

        # 현재 달의 시작과 끝
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        async with connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) as count
                FROM api_usage
                WHERE api_key = ? AND timestamp >= ?
                """,
                (api_key, month_start.isoformat())
            )
            row = await cursor.fetchone()
            usage_count = row[0] if row else 0

        is_under_limit = usage_count < self.monthly_limit
        return is_under_limit, usage_count

    async def _log_usage(
        self,
        api_key: str,
        endpoint: str,
        success: bool = True
    ):
        """
        API 사용량 로깅

        Args:
            api_key: API 키
            endpoint: 엔드포인트 경로
            success: 요청 성공 여부
        """
        await self._init_db()

        async with connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO api_usage (api_key, endpoint, success)
                VALUES (?, ?, ?)
                """,
                (api_key, endpoint, success)
            )
            await db.commit()

    async def verify_api_key(
        self,
        api_key: Optional[str] = Security(api_key_header)
    ) -> str:
        """
        API 키 검증

        Args:
            api_key: X-API-Key 헤더 값

        Returns:
            검증된 API 키

        Raises:
            HTTPException: 인증 실패 시
        """
        if not api_key:
            logger.warning("API 키가 제공되지 않음")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API 키가 필요합니다. X-API-Key 헤더를 포함해주세요."
            )

        if api_key not in self.valid_api_keys:
            logger.warning(f"유효하지 않은 API 키: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="유효하지 않은 API 키입니다."
            )

        # 사용량 제한 확인
        is_allowed, current_usage = await self._check_usage_limit(api_key)

        if not is_allowed:
            logger.warning(f"월 사용량 초과: {api_key[:10]}... ({current_usage}/{self.monthly_limit})")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"월 사용량 제한을 초과했습니다. 현재: {current_usage}/{self.monthly_limit}"
            )

        logger.info(f"API 인증 성공: {api_key[:10]}... (월 사용량: {current_usage}/{self.monthly_limit})")
        return api_key

    async def log_request(
        self,
        api_key: str,
        endpoint: str,
        success: bool = True
    ):
        """
        요청 로깅

        Args:
            api_key: API 키
            endpoint: 엔드포인트 경로
            success: 요청 성공 여부
        """
        await self._log_usage(api_key, endpoint, success)

    async def get_usage_stats(self, api_key: str) -> dict:
        """
        API 사용량 통계 조회

        Args:
            api_key: API 키

        Returns:
            사용량 통계
        """
        await self._init_db()

        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)

        async with connect(self.db_path) as db:
            # 이번 달 사용량
            cursor = await db.execute(
                """
                SELECT COUNT(*) as count
                FROM api_usage
                WHERE api_key = ? AND timestamp >= ?
                """,
                (api_key, month_start.isoformat())
            )
            this_month_row = await cursor.fetchone()
            this_month_count = this_month_row[0] if this_month_row else 0

            # 지난 달 사용량
            cursor = await db.execute(
                """
                SELECT COUNT(*) as count
                FROM api_usage
                WHERE api_key = ? AND timestamp >= ? AND timestamp < ?
                """,
                (api_key, last_month_start.isoformat(), month_start.isoformat())
            )
            last_month_row = await cursor.fetchone()
            last_month_count = last_month_row[0] if last_month_row else 0

            # 전체 사용량
            cursor = await db.execute(
                """
                SELECT COUNT(*) as count
                FROM api_usage
                WHERE api_key = ?
                """,
                (api_key,)
            )
            total_row = await cursor.fetchone()
            total_count = total_row[0] if total_row else 0

        return {
            "this_month": this_month_count,
            "last_month": last_month_count,
            "total": total_count,
            "monthly_limit": self.monthly_limit,
            "remaining": max(0, self.monthly_limit - this_month_count)
        }


# 전역 인증 미들웨어 인스턴스
auth_middleware = AuthMiddleware()


async def get_optional_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    선택적 API 키 검증 (공개 엔드포인트용)

    Args:
        api_key: X-API-Key 헤더 값

    Returns:
        API 키 또는 None
    """
    if api_key and api_key in auth_middleware.valid_api_keys:
        return api_key
    return None
