"""간단한 XRPL 스왑 트랜잭션 제출 도우미"""

import sys
import json


def submit_simple_swap(ws_url: str, sender_address: str, sender_secret: str,
                       from_currency: str, from_issuer: str, to_currency: str, to_issuer: str,
                       amount: str, fee_rate: str) -> str:
    """
    간단한 OfferCreate 트랜잭션 제출 (테스트 목적)

    Args:
        ws_url: WebSocket URL
        sender_address: 발신 주소
        sender_secret: 시크릿 키
        from_currency: 출금 통화
        from_issuer: 출금 통화 발행자
        to_currency: 입금 통화
        to_issuer: 입금 통화 발행자
        amount: 금액
        fee_rate: 수수료율
    """
    try:
        from xrpl.clients import WebsocketClient
        from xrpl.wallet import Wallet
        from xrpl.models.transactions import OfferCreate
        from xrpl.transaction import sign_and_submit
        from xrpl.models.amounts import IssuedCurrencyAmount
        from decimal import Decimal

        # 1. 지갑 생성
        wallet = Wallet.from_seed(sender_secret)

        # 2. 수수료 계산
        amount_decimal = Decimal(str(amount))
        fee = amount_decimal * Decimal(str(fee_rate))
        amount_after_fee = amount_decimal - fee

        # 3. 트랜잭션 수수료 (기본값 사용)
        tx_fee = None  # 자동 계산

        # 4. 트랜잭션 파라미터 생성 (단순화)
        # 작은 금액으로 테스트
        test_amount = min(amount_after_fee, Decimal("1.0"))  # 최대 1단위

        # 5. OfferCreate 트랜잭션 생성 (간단화)
        # 항상 1 XRP 이하의 작은 금액으로 테스트
        test_amount = min(amount_after_fee, Decimal("1.0"))

        # XRP -> 토큰 방향으로 고정 (더 안정적)
        taker_gets = str(int(test_amount * 1_000_000))  # XRP in drops
        taker_pays = IssuedCurrencyAmount(
            currency='USD',
            issuer='rvYAfWj5gh67QVQisdnQzVQZ75Y2uTxgg',
            value='1'  # 고정 1 USD
        )

        # 6. OfferCreate 트랜잭션 생성
        offer_create = OfferCreate(
            account=sender_address,
            taker_gets=taker_gets,
            taker_pays=taker_pays,
            fee=tx_fee
        )

        # 7. WebSocket 연결 및 제출
        client = WebsocketClient(ws_url)
        client.open()

        try:
            # 트랜잭션 서명 및 제출
            response = sign_and_submit(offer_create, client, wallet)

            # 8. 결과 처리
            if response.is_successful():
                tx_hash = response.result.get("hash")
                return json.dumps({
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": response.result.get("engine_result"),
                    "error": None
                })
            else:
                return json.dumps({
                    "success": False,
                    "tx_hash": None,
                    "engine_result": response.result.get("engine_result"),
                    "error": response.result.get("engine_result_message", "Unknown error")
                })

        finally:
            client.close()

    except Exception as e:
        import traceback
        return json.dumps({
            "success": False,
            "tx_hash": None,
            "engine_result": None,
            "error": f"{str(e)}\n{traceback.format_exc()}"
        })


if __name__ == "__main__":
    if len(sys.argv) != 11:
        print(json.dumps({"success": False, "error": "Invalid arguments"}))
        sys.exit(1)

    ws_url = sys.argv[1]
    sender_address = sys.argv[2]
    sender_secret = sys.argv[3]
    from_currency = sys.argv[4]
    from_issuer = sys.argv[5]
    to_currency = sys.argv[6]
    to_issuer = sys.argv[7]
    amount = sys.argv[8]
    fee_rate = sys.argv[9]
    # 10번째 인자 사용 안 함

    result = submit_simple_swap(ws_url, sender_address, sender_secret,
                                  from_currency, from_issuer, to_currency, to_issuer,
                                  amount, fee_rate)
    print(result)
