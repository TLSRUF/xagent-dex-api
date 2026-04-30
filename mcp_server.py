"""
XRPL DEX API MCP 서버

XRPL DEX API와 상호작용하기 위한 MCP(Model Context Protocol) 서버입니다.
"""

from mcp.server.fastmcp import FastMCP
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("xagent-dex-api")
API_BASE = "http://localhost:8000"
API_KEY = os.getenv("MCP_API_KEY", "test-api-key-1")


@mcp.tool()
def get_tokens() -> str:
    """지원 토큰 목록 조회"""
    response = httpx.get(f"{API_BASE}/dex/tokens")
    return str(response.json())


@mcp.tool()
def get_orderbook(base: str, quote: str) -> str:
    """오더북 조회"""
    response = httpx.get(
        f"{API_BASE}/dex/orderbook",
        params={"base": base, "quote": quote}
    )
    return str(response.json())


@mcp.tool()
def get_quote(from_currency: str, to_currency: str, amount: float) -> str:
    """스왑 견적 조회"""
    response = httpx.get(
        f"{API_BASE}/dex/quote",
        params={"from_currency": from_currency, "to_currency": to_currency, "amount": amount}
    )
    return str(response.json())


@mcp.tool()
def swap_tokens(from_currency: str, to_currency: str, amount: float) -> str:
    """토큰 스왑 실행"""
    response = httpx.post(
        f"{API_BASE}/dex/swap",
        headers={"X-API-Key": API_KEY},
        json={"from_currency": from_currency, "to_currency": to_currency, "amount": amount}
    )
    return str(response.json())


if __name__ == "__main__":
    mcp.run()
