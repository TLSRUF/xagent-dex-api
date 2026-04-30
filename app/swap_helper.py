"""실제 XRPL 트랜잭션 제출 도우미 스크립트"""

import sys
import json
import time


def submit_swap_transaction(ws_url: str, sender_address: str, sender_secret: str,
                           from_currency: str, from_issuer: str, to_currency: str, to_issuer: str,
                           amount: str, fee_rate: str) -> str:
    """
    실제 OfferCreate 트랜잭션 제출

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

    Returns:
        JSON 형식 트랜잭션 결과
    """
    try:
        from xrpl.clients import WebsocketClient
        from xrpl.wallet import Wallet
        from xrpl.models.transactions import OfferCreate
        from xrpl.transaction import sign_and_submit
        from xrpl.models.amounts import IssuedCurrencyAmount
        from xrpl.models.currencies import XRP, IssuedCurrency
        from decimal import Decimal

        # 1. 지갑 생성 (시크릿 키로)
        wallet = Wallet.from_seed(sender_secret)

        # 2. 수수료 계산
        amount_decimal = Decimal(str(amount))
        fee = amount_decimal * Decimal(str(fee_rate))
        amount_after_fee = amount_decimal - fee

        # 3. 트랜잭션 수수료 계산 (XRPL 네트워크 수수료)
        # OfferCreate는 트랜잭션 수수료가 필요합니다
        # 최소 수수료로 설정하거나 자동 계산
        tx_fee = "10"  # 기본 10 drops (0.00001 XRP)

        # 4. taker_gets 생성 (출금 통화 - 수수료 차감 후)
        if from_issuer:
            # 토큰인 경우 IssuedCurrencyAmount 사용
            from xrpl.models.amounts import IssuedCurrencyAmount
            taker_gets = IssuedCurrencyAmount(
                currency=from_currency,
                issuer=from_issuer,
                value=str(amount_after_fee.quantize(Decimal("0.000001")))
            )
        else:
            # XRP인 경우 drops를 문자열로 변환
            taker_gets_amount = int(amount_after_fee * 1_000_000)  # XRP to drops
            taker_gets = str(taker_gets_amount)  # 문자열로 전달

        # 5. taker_pays 생성 (입금 통화)
        if to_issuer:
            # 토큰인 경우 IssuedCurrencyAmount 사용
            from xrpl.models.amounts import IssuedCurrencyAmount
            # 입금 통화는 수수료 차감 안 함
            taker_pays = IssuedCurrencyAmount(
                currency=to_currency,
                issuer=to_issuer,
                value=str(amount_after_fee.quantize(Decimal("0.000001")))
            )
        else:
            # XRP인 경우 drops를 문자열로 변환
            taker_pays_amount = int(amount_after_fee * 1_000_000)
            taker_pays = str(taker_pays_amount)  # 문자열로 전달

        # 6. OfferCreate 트랜잭션 생성
        offer_create = OfferCreate(
            account=sender_address,
            taker_gets=taker_gets,
            taker_pays=taker_pays,
            fee=tx_fee  # 트랜잭션 수수료
        )

        # 7. WebSocket 연결 및 트랜잭션 제출
        client = WebsocketClient(ws_url)
        client.open()

        try:
            # 트랜잭션 서명 및 제출
            response = sign_and_submit(offer_create, client, wallet)

            # 8. 결과 확인
            if response.is_successful():
                # 트랜잭션 해시 추출
                tx_hash = response.result.get("hash")
                engine_result = response.result.get("engine_result")
                engine_result_message = response.result.get("engine_result_message")

                return json.dumps({
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": None
                })
            else:
                # 트랜잭션 실패
                engine_result = response.result.get("engine_result", "Unknown")
                engine_result_message = response.result.get("engine_result_message", "Unknown error")

                return json.dumps({
                    "success": False,
                    "tx_hash": None,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": engine_result_message
                })

        finally:
            client.close()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        return json.dumps({
            "success": False,
            "tx_hash": None,
            "engine_result": None,
            "engine_result_message": str(e),
            "error": f"{str(e)}\n{error_details}"
        })


if __name__ == "__main__":
    if len(sys.argv) != 11:
        print(json.dumps({
            "success": False,
            "tx_hash": None,
            "error": "Invalid arguments"
        }))
        sys.exit(1)

    # 인자 파싱
    ws_url = sys.argv[1]
    sender_address = sys.argv[2]
    sender_secret = sys.argv[3]
    from_currency = sys.argv[4]
    from_issuer = sys.argv[5]
    to_currency = sys.argv[6]
    to_issuer = sys.argv[7]
    amount = sys.argv[8]
    fee_rate = sys.argv[9]
    # 10번째 인자는 사용하지 않음

    # 스왑 트랜잭션 제출
    result = submit_swap_transaction(
        ws_url, sender_address, sender_secret,
        from_currency, from_issuer, to_currency, to_issuer,
        amount, fee_rate
    )

    print(result)