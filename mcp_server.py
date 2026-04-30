"""
XRPL DEX API MCP 서버

XRPL DEX API와 상호작용하기 위한 MCP(Model Context Protocol) 서버입니다.
"""

import os
import httpx
from typing import Optional
from fastmcp import FastMCP

# MCP 서버 인스턴스 생성
mcp = FastMCP("XRPL DEX API")

# 환경변수 설정
API_BASE_URL = os.getenv("MCP_API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("MCP_API_KEY", "")

# HTTP 클라이언트 설정
timeout = httpx.Timeout(30.0)


def get_headers() -> dict:
    """API 요청 헤더 생성"""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    return headers


@mcp.tool()
async def get_orderbook(base: str, quote: str, limit: Optional[int] = 20) -> dict:
    """
    XRPL DEX 오더북 조회

    Args:
        base: 기본 통화 (예: XRP, USD)
        quote: 상대 통화 (예: XRP, USD)
        limit: 반환할 호가 수 (기본값: 20, 최대: 100)

    Returns:
        오더북 정보 (bids, asks)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            params = {
                "base": base.upper(),
                "quote": quote.upper(),
                "limit": min(limit, 100)  # 최대 100개 제한
            }

            response = await client.get(
                f"{API_BASE_URL}/dex/orderbook",
                params=params,
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {
            "error": f"HTTP 오류 발생: {str(e)}",
            "base": base,
            "quote": quote
        }
    except Exception as e:
        return {
            "error": f"오더북 조회 실패: {str(e)}",
            "base": base,
            "quote": quote
        }


@mcp.tool()
async def get_quote(from_currency: str, to_currency: str, amount: str) -> dict:
    """
    스왑 견적 조회

    Args:
        from_currency: 출금 통화 (예: XRP, USD)
        to_currency: 입금 통화 (예: XRP, USD)
        amount: 조회 금액

    Returns:
        스왑 견적 정보 (수수료 포함)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            params = {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "amount": amount
            }

            response = await client.get(
                f"{API_BASE_URL}/dex/quote",
                params=params,
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {
            "error": f"HTTP 오류 발생: {str(e)}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount
        }
    except Exception as e:
        return {
            "error": f"견적 조회 실패: {str(e)}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount
        }


@mcp.tool()
async def swap_tokens(from_currency: str, to_currency: str, amount: str) -> dict:
    """
    토큰 스왑 실행

    Args:
        from_currency: 출금 통화 (예: XRP, USD)
        to_currency: 입금 통화 (예: XRP, USD)
        amount: 스왑 금액

    Returns:
        스왑 실행 결과 (트랜잭션 해시 포함)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            payload = {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "amount": amount
            }

            response = await client.post(
                f"{API_BASE_URL}/dex/swap",
                json=payload,
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {
            "error": f"HTTP 오류 발생: {str(e)}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "success": False
        }
    except Exception as e:
        return {
            "error": f"스왑 실행 실패: {str(e)}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "success": False
        }


@mcp.tool()
async def get_tokens() -> dict:
    """
    지원 토큰 목록 조회

    Returns:
        지원 토큰 목록 (currency, issuer, name, decimals)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{API_BASE_URL}/dex/tokens",
                headers=get_headers()
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {
            "error": f"HTTP 오류 발생: {str(e)}",
            "tokens": [],
            "count": 0
        }
    except Exception as e:
        return {
            "error": f"토큰 목록 조회 실패: {str(e)}",
            "tokens": [],
            "count": 0
        }


if __name__ == "__main__":
    # MCP 서버 실행
    mcp.run()
