"""
XRPL DEX API MCP 서버

XRPL DEX API와 상호작용하기 위한 MCP(Model Context Protocol) 서버입니다.
"""

from mcp.server.fastmcp import FastMCP
import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("xagent-dex-api")
API_BASE = "http://localhost:8000"
API_KEY = os.getenv("MCP_API_KEY", "test-api-key-1")


@mcp.tool()
def get_tokens() -> str:
    """지원 토큰 목록 조회"""
    response = httpx.get(
        f"{API_BASE}/dex/tokens",
        headers={"X-API-Key": API_KEY},
        timeout=30.0
    )
    return json.dumps(response.json(), ensure_ascii=False, indent=2)


@mcp.tool()
def get_orderbook(base: str, quote: str, limit: int = 20) -> str:
    """오더북 조회

    Args:
        base: 기본 통화 (예: XRP, USD)
        quote: 상대 통화 (예: XRP, USD)
        limit: 반환할 호가 수 (기본값: 20, 최대: 100)

    Returns:
        오더북 정보 (bids, asks)
    """
    response = httpx.get(
        f"{API_BASE}/dex/orderbook",
        params={
            "base": base.upper(),
            "quote": quote.upper(),
            "limit": min(limit, 100)
        },
        headers={"X-API-Key": API_KEY},
        timeout=30.0
    )
    return json.dumps(response.json(), ensure_ascii=False, indent=2)


@mcp.tool()
def get_quote(from_currency: str, to_currency: str, amount: str) -> str:
    """스왑 견적 조회

    Args:
        from_currency: 출금 통화 (예: XRP, USD)
        to_currency: 입금 통화 (예: XRP, USD)
        amount: 조회 금액

    Returns:
        스왑 견적 정보 (수수료 포함)
    """
    response = httpx.get(
        f"{API_BASE}/dex/quote",
        params={
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "amount": amount
        },
        headers={"X-API-Key": API_KEY},
        timeout=30.0
    )
    return json.dumps(response.json(), ensure_ascii=False, indent=2)


@mcp.tool()
def swap_tokens(from_currency: str, to_currency: str, amount: str) -> str:
    """토큰 스왑 실행

    Args:
        from_currency: 출금 통화 (예: XRP, USD)
        to_currency: 입금 통화 (예: XRP, USD)
        amount: 스왑 금액

    Returns:
        스왑 실행 결과 (트랜잭션 해시 포함)
    """
    response = httpx.post(
        f"{API_BASE}/dex/swap",
        json={
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "amount": amount
        },
        headers={"X-API-Key": API_KEY},
        timeout=30.0
    )
    return json.dumps(response.json(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
