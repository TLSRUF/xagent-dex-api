"""xrpl-py WebsocketClient 기반 DEX 클라이언트"""

import json
from typing import List, Optional, Dict, Any
from decimal import Decimal
from xrpl.clients import WebsocketClient
from xrpl.models.requests import BookOffers
from xrpl.models.currencies import XRP, IssuedCurrency
import logging

logger = logging.getLogger(__name__)


class XRPLWebsocketClient:
    """xrpl-py WebsocketClient를 사용한 DEX 클라이언트"""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.client = None

    def __enter__(self):
        self.client = WebsocketClient(self.ws_url)
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.close()

    def open(self):
        """WebSocket 연결 열기"""
        if not self.client or not self.client.is_open():
            self.client = WebsocketClient(self.ws_url)
            self.client.open()

    def close(self):
        """WebSocket 연결 닫기"""
        if self.client and self.client.is_open():
            self.client.close()

    def get_orderbook(
        self,
        base_currency: str,
        base_issuer: Optional[str],
        quote_currency: str,
        quote_issuer: Optional[str],
        limit: int = 20
    ) -> Dict[str, Any]:
        """오더북 조회"""
        try:
            # 연결 열기
            self.open()

            # taker_gets 생성
            if base_issuer:
                taker_gets = IssuedCurrency(
                    currency=base_currency,
                    issuer=base_issuer
                )
            else:
                taker_gets = XRP()

            # taker_pays 생성
            if quote_issuer:
                taker_pays = IssuedCurrency(
                    currency=quote_currency,
                    issuer=quote_issuer
                )
            else:
                taker_pays = XRP()

            # BookOffers 요청 생성
            book_offers_request = BookOffers(
                taker_gets=taker_gets,
                taker_pays=taker_pays,
                limit=limit
            )

            # 요청 전송
            response = self.client.request(book_offers_request)
            offers = response.result.get("offers", [])

            # 결과 포맷팅
            bids = []
            asks = []

            for offer in offers:
                # TakerGets 값 추출
                taker_gets_value = offer.get("TakerGets")
                if isinstance(taker_gets_value, str):
                    amount = Decimal(taker_gets_value)
                elif isinstance(taker_gets_value, dict):
                    amount = Decimal(taker_gets_value.get("value", "0"))
                else:
                    amount = Decimal("0")

                offer_data = {
                    "price": Decimal(str(offer.get("quality", "0"))),
                    "amount": amount,
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
            logger.error(f"오더북 조회 실패: {e}")
            return {
                "bids": [],
                "asks": [],
                "success": False,
                "error": str(e)
            }
        finally:
            # 연결 닫기
            self.close()