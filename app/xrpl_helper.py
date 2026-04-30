"""XRPL 도우미 스크립트 (별도 프로세스에서 실행)"""

import sys
import json


def fetch_orderbook(node_url: str, taker_gets_currency: str, taker_gets_issuer: str,
                    taker_pays_currency: str, taker_pays_issuer: str, limit: int) -> str:
    """오더북 조회 (별도 프로세스에서 실행)"""
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.models.requests import BookOffers
        from xrpl.models.currencies import XRP, IssuedCurrency

        # 클라이언트 생성
        client = JsonRpcClient(node_url)

        # taker_gets 생성
        if taker_gets_issuer:
            taker_gets = IssuedCurrency(
                currency=taker_gets_currency,
                issuer=taker_gets_issuer
            )
        else:
            taker_gets = XRP()

        # taker_pays 생성
        if taker_pays_issuer:
            taker_pays = IssuedCurrency(
                currency=taker_pays_currency,
                issuer=taker_pays_issuer
            )
        else:
            taker_pays = XRP()

        # BookOffers 요청 생성
        book_offers_request = BookOffers(
            taker_gets=taker_gets,
            taker_pays=taker_pays,
            limit=limit
        )

        # 요청 실행
        response = client.request(book_offers_request)
        offers = response.result.get("offers", [])

        return json.dumps({
            "success": True,
            "offers": offers
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "offers": []
        })


def submit_swap(node_url: str, sender_address: str, sender_secret: str,
               from_currency: str, from_issuer: str, to_currency: str, to_issuer: str,
               amount: str, fee_rate: str) -> str:
    """스왑 트랜잭션 제출 (별도 프로세스에서 실행)"""
    try:
        from xrpl.clients import JsonRpcClient
        from xrpl.wallet import Wallet
        from xrpl.models.transactions import OfferCreate
        from xrpl.transaction import sign_and_submit
        from xrpl.models.currencies import XRP, IssuedCurrency
        from decimal import Decimal

        # 클라이언트와 지갑 생성
        client = JsonRpcClient(node_url)
        wallet = Wallet.from_seed(sender_secret)

        # amount 변환
        amount_decimal = Decimal(str(amount))

        # taker_gets 생성 (from_currency)
        if from_issuer:
            taker_gets = IssuedCurrency(
                currency=from_currency,
                issuer=from_issuer
            )
        else:
            taker_gets = XRP()

        # taker_pays 생성 (to_currency)
        if to_issuer:
            taker_pays = IssuedCurrency(
                currency=to_currency,
                issuer=to_issuer
            )
        else:
            taker_pays = XRP()

        # OfferCreate 트랜잭션 생성
        offer_create = OfferCreate(
            account=sender_address,
            taker_gets=taker_gets,
            taker_pays=taker_pays
        )

        # 트랜잭션 제출
        response = sign_and_submit(offer_create, client, wallet)

        if response.is_successful():
            return json.dumps({
                "success": True,
                "tx_hash": response.result.get("hash"),
                "error": None
            })
        else:
            return json.dumps({
                "success": False,
                "tx_hash": None,
                "error": response.result.get("engine_result_message", "Unknown error")
            })

    except Exception as e:
        return json.dumps({
            "success": False,
            "tx_hash": None,
            "error": str(e)
        })


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""

    if command == "orderbook":
        # 오더북 조회 명령
        if len(sys.argv) != 8:
            print(json.dumps({"success": False, "error": "Invalid arguments", "offers": []}))
            sys.exit(1)

        node_url = sys.argv[2]
        taker_gets_currency = sys.argv[3]
        taker_gets_issuer = sys.argv[4]
        taker_pays_currency = sys.argv[5]
        taker_pays_issuer = sys.argv[6]
        limit = int(sys.argv[7])

        result = fetch_orderbook(node_url, taker_gets_currency, taker_gets_issuer,
                                taker_pays_currency, taker_pays_issuer, limit)
        print(result)

    elif command == "swap":
        # 스왑 명령
        if len(sys.argv) != 11:
            print(json.dumps({"success": False, "tx_hash": None, "error": "Invalid arguments"}))
            sys.exit(1)

        node_url = sys.argv[2]
        sender_address = sys.argv[3]
        sender_secret = sys.argv[4]
        from_currency = sys.argv[5]
        from_issuer = sys.argv[6]
        to_currency = sys.argv[7]
        to_issuer = sys.argv[8]
        amount = sys.argv[9]
        fee_rate = sys.argv[10]

        result = submit_swap(node_url, sender_address, sender_secret,
                           from_currency, from_issuer, to_currency, to_issuer,
                           amount, fee_rate)
        print(result)

    else:
        print(json.dumps({"success": False, "error": "Invalid command", "offers": []}))
        sys.exit(1)
