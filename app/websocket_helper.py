"""WebSocket 기반 XRQL 도우미 스크립트 (별도 프로세스)"""

import sys
import json


def fetch_orderbook_websocket(ws_url: str, base_currency: str, base_issuer: str,
                              quote_currency: str, quote_issuer: str, limit: int) -> str:
    """WebSocket으로 오더북 조회 (별도 프로세스)"""
    try:
        from xrpl.clients import WebsocketClient
        from xrpl.models.requests import BookOffers
        from xrpl.models.currencies import XRP, IssuedCurrency
        from decimal import Decimal

        # WebSocket 클라이언트 생성
        client = WebsocketClient(ws_url)
        client.open()

        try:
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
            response = client.request(book_offers_request)
            offers = response.result.get("offers", [])

            # 결과 포맷팅
            formatted_offers = []
            for offer in offers:
                # TakerGets 값 추출
                taker_gets_value = offer.get("TakerGets")
                if isinstance(taker_gets_value, str):
                    amount = str(taker_gets_value)
                elif isinstance(taker_gets_value, dict):
                    amount = str(taker_gets_value.get("value", "0"))
                else:
                    amount = "0"

                formatted_offer = {
                    "price": str(offer.get("quality", "0")),
                    "amount": amount,
                    "account": offer.get("Account", ""),
                    "sequence": offer.get("Sequence", 0)
                }
                formatted_offers.append(formatted_offer)

            return json.dumps({
                "success": True,
                "offers": formatted_offers
            })

        finally:
            client.close()

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "offers": []
        })


if __name__ == "__main__":
    if len(sys.argv) != 8:
        print(json.dumps({"success": False, "error": "Invalid arguments", "offers": []}))
        sys.exit(1)

    ws_url = sys.argv[1]
    base_currency = sys.argv[2]
    base_issuer = sys.argv[3]
    quote_currency = sys.argv[4]
    quote_issuer = sys.argv[5]
    limit = int(sys.argv[6])
    # 7번째 인자는 사용하지 않음

    result = fetch_orderbook_websocket(ws_url, base_currency, base_issuer,
                                       quote_currency, quote_issuer, limit)
    print(result)