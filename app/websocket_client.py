"""WebSocket 기반 XRPL DEX 클라이언트 (스레드풀 실행)"""

import json
import asyncio
import websockets
from typing import List, Optional, Dict, Any
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import threading


class WebSocketXRPLClient:
    """WebSocket 기반 XRPL 클라이언트 (스레드풀 사용)"""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url

    def get_orderbook_sync(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str],
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        오더북 조회 (동기 메서드 - 내부적으로 async 실행)
        """
        def run_async():
            # 새로운 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self._get_orderbook_async(
                        base_currency, base_issuer,
                        quote_currency, quote_issuer, limit
                    )
                )
            finally:
                loop.close()

        # 현재 스레드에서 실행
        return run_async()

    async def _get_orderbook_async(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str],
        limit: int
    ) -> Dict[str, Any]:
        """비동기 오더북 조회"""
        try:
            # WebSocket 연결
            async with websockets.connect(self.ws_url) as websocket:
                # book_offers 요청 생성
                request_data = {
                    "command": "book_offers",
                    "taker_gets": {
                        "currency": base_currency
                    },
                    "taker_pays": {
                        "currency": quote_currency
                    },
                    "limit": limit
                }

                # issuer 추가
                if base_issuer:
                    request_data["taker_gets"]["issuer"] = base_issuer
                if quote_issuer:
                    request_data["taker_pays"]["issuer"] = quote_issuer

                # 요청 전송
                await websocket.send(json.dumps(request_data))

                # 응답 수신
                response_text = await websocket.recv()
                response_data = json.loads(response_text)

                offers = response_data.get("result", {}).get("offers", [])

                # 결과 포맷팅
                bids = []
                asks = []

                for offer in offers:
                    offer_data = {
                        "price": Decimal(str(offer.get("quality", "0"))),
                        "amount": Decimal(str(
                            offer.get("TakerGets", "0") if isinstance(offer.get("TakerGets"), str)
                            else offer.get("TakerGets", {}).get("value", "0")
                        )),
                        "account": offer.get("Account", ""),
                        "sequence": offer.get("Sequence", 0)
                    }

                    # 매수/매도 구분
                    if Decimal(str(offer.get("quality", "0"))) > 0:
                        bids.append(offer_data)
                    else:
                        asks.append(offer_data)

                # 정렬
                bids.sort(key=lambda x: x["price"], reverse=True)
                asks.sort(key=lambda x: x["price"])

                return {
                    "bids": bids[:limit],
                    "asks": asks[:limit],
                    "success": True
                }

        except Exception as e:
            return {
                "bids": [],
                "asks": [],
                "success": False,
                "error": str(e)
            }