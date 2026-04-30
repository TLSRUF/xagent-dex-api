"""
XRPL DEX API MCP 서버

XRPL DEX API와 상호작용하기 위한 MCP(Model Context Protocol) 서버입니다.
JSON-RPC 2.0 기반으로 stdio 통해 통신합니다.
"""

import os
import sys
import json
import asyncio
import httpx
from typing import Optional, Any

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


async def call_api(method: str, endpoint: str, params: dict = None, payload: dict = None) -> dict:
    """DEX API 호출 헬퍼 함수"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"{API_BASE_URL}{endpoint}"

            if method == "GET":
                response = await client.get(url, params=params, headers=get_headers())
            elif method == "POST":
                response = await client.post(url, json=payload, headers=get_headers())
            else:
                return {"error": f"지원하지 않는 HTTP 메서드: {method}"}

            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        return {"error": f"HTTP 오류 발생: {str(e)}"}
    except Exception as e:
        return {"error": f"API 호출 실패: {str(e)}"}


async def get_orderbook(base: str, quote: str, limit: int = 20) -> dict:
    """오더북 조회"""
    return await call_api(
        "GET",
        "/dex/orderbook",
        params={
            "base": base.upper(),
            "quote": quote.upper(),
            "limit": min(limit, 100)
        }
    )


async def get_quote(from_currency: str, to_currency: str, amount: str) -> dict:
    """스왑 견적 조회"""
    return await call_api(
        "GET",
        "/dex/quote",
        params={
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "amount": amount
        }
    )


async def swap_tokens(from_currency: str, to_currency: str, amount: str) -> dict:
    """토큰 스왑 실행"""
    return await call_api(
        "POST",
        "/dex/swap",
        payload={
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "amount": amount
        }
    )


async def get_tokens() -> dict:
    """지원 토큰 목록 조회"""
    return await call_api("GET", "/dex/tokens")


def send_response(response: dict):
    """JSON-RPC 응답 전송"""
    json.dump(response, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


async def handle_request(request: dict):
    """MCP 요청 처리"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        # MCP 초기화
        send_response({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "xrpl-dex-api",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        })

    elif method == "tools/list":
        # 사용 가능한 툴 목록
        send_response({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "get_orderbook",
                        "description": "XRPL DEX 오더북 조회",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "base": {"type": "string", "description": "기본 통화 (예: XRP, USD)"},
                                "quote": {"type": "string", "description": "상대 통화 (예: XRP, USD)"},
                                "limit": {"type": "integer", "description": "반환할 호가 수", "default": 20}
                            },
                            "required": ["base", "quote"]
                        }
                    },
                    {
                        "name": "get_quote",
                        "description": "스왑 견적 조회",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "from_currency": {"type": "string", "description": "출금 통화"},
                                "to_currency": {"type": "string", "description": "입금 통화"},
                                "amount": {"type": "string", "description": "조회 금액"}
                            },
                            "required": ["from_currency", "to_currency", "amount"]
                        }
                    },
                    {
                        "name": "swap_tokens",
                        "description": "토큰 스왑 실행",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "from_currency": {"type": "string", "description": "출금 통화"},
                                "to_currency": {"type": "string", "description": "입금 통화"},
                                "amount": {"type": "string", "description": "스왑 금액"}
                            },
                            "required": ["from_currency", "to_currency", "amount"]
                        }
                    },
                    {
                        "name": "get_tokens",
                        "description": "지원 토큰 목록 조회",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
            }
        })

    elif method == "tools/call":
        # 툴 호출
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "get_orderbook":
                result = await get_orderbook(
                    arguments.get("base", ""),
                    arguments.get("quote", ""),
                    arguments.get("limit", 20)
                )
            elif tool_name == "get_quote":
                result = await get_quote(
                    arguments.get("from_currency", ""),
                    arguments.get("to_currency", ""),
                    arguments.get("amount", "")
                )
            elif tool_name == "swap_tokens":
                result = await swap_tokens(
                    arguments.get("from_currency", ""),
                    arguments.get("to_currency", ""),
                    arguments.get("amount", "")
                )
            elif tool_name == "get_tokens":
                result = await get_tokens()
            else:
                result = {"error": f"알 수 없는 툴: {tool_name}"}

            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False)
                        }
                    ]
                }
            })

        except Exception as e:
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"툴 실행 실패: {str(e)}"
                }
            })

    else:
        send_response({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"알 수 없는 메서드: {method}"
            }
        })


async def main():
    """MCP 서버 메인 루프"""
    # stdio 통해 JSON-RPC 메시지 수신
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            request = json.loads(line.strip())
            await handle_request(request)

        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            send_response(error_response)


if __name__ == "__main__":
    asyncio.run(main())
