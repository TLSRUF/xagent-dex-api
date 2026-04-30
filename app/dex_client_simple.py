"""간단한 XRPL DEX 클라이언트 (동기 방식)"""

import json
import time
import requests
from typing import List, Optional, Dict, Any
from decimal import Decimal

class SimpleXRPLClient:
    """간단한 XRPL 클라이언트 (동기 HTTP 요청)"""

    def __init__(self, node_url: str):
        self.node_url = node_url.replace("wss://", "https://").replace("ws://", "http://")

    def get_orderbook(self, base_currency: str, base_issuer: Optional[str],
                     quote_currency: str, quote_issuer: Optional[str],
                     limit: int = 20) -> Dict[str, Any]:
        """오더북 조회 (동기 방식)"""
        try:
            # JSON-RPC 요청 생성
            request_data = {
                "method": "book_offers",
                "params": [{
                    "taker_gets": {
                        "currency": base_currency
                    },
                    "taker_pays": {
                        "currency": quote_currency
                    },
                    "limit": limit
                }]
            }

            # issuer 추가
            if base_issuer:
                request_data["params"][0]["taker_gets"]["issuer"] = base_issuer
            if quote_issuer:
                request_data["params"][0]["taker_pays"]["issuer"] = quote_issuer

            # HTTP 요청 (여러 시도)
            for attempt in range(3):
                try:
                    response = requests.post(
                        self.node_url,
                        json=request_data,
                        timeout=10,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        offers = data.get("result", {}).get("offers", [])

                        # 결과 포맷팅
                        bids = []
                        asks = []

                        for offer in offers:
                            offer_data = {
                                "price": Decimal(str(offer.get("quality", "0"))),
                                "amount": Decimal(str(offer.get("TakerGets", "0") if isinstance(offer.get("TakerGets"), str) else offer.get("TakerGets", {}).get("value", "0"))),
                                "account": offer.get("Account", ""),
                                "sequence": offer.get("Sequence", 0)
                            }

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

                    elif attempt < 2:  # 재시도
                        time.sleep(1)
                    else:
                        return {
                            "bids": [],
                            "asks": [],
                            "success": False,
                            "error": f"HTTP {response.status_code}"
                        }

                except requests.exceptions.RequestException as e:
                    if attempt < 2:
                        time.sleep(1)
                    else:
                        return {
                            "bids": [],
                            "asks": [],
                            "success": False,
                            "error": str(e)
                        }

            return {
                "bids": [],
                "asks": [],
                "success": False,
                "error": "Max retries exceeded"
            }

        except Exception as e:
            return {
                "bids": [],
                "asks": [],
                "success": False,
                "error": str(e)
            }