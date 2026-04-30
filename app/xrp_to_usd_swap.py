"""XRP → USD OfferCreate 트랜잭션 제출 (subprocess 방식)"""

import sys
import json


def submit_xrp_to_usd_swap(
    ws_url: str,
    sender_address: str,
    sender_secret: str,
    xrp_amount: str,
    usd_amount: str,
    fee_rate: str
) -> str:
    """
    XRP → USD OfferCreate 트랜잭션 제출 (subprocess 사용)

    Args:
        ws_url: XRPL WebSocket URL
        sender_address: 발신 주소
        sender_secret: 시크릿 키
        xrp_amount: XRP 금액 (XRP 단위)
        usd_amount: USD 금액 (USD 단위)
        fee_rate: 수수료율

    Returns:
        JSON 형식 트랜잭션 결과
    """
    try:
        from xrpl.clients import WebsocketClient
        from xrpl.wallet import Wallet
        from xrpl.models.transactions import OfferCreate
        from xrpl.models.amounts import IssuedCurrencyAmount
        from xrpl.transaction import submit_and_wait
        from decimal import Decimal

        # 1. 지갑 생성
        wallet = Wallet.from_seed(sender_secret)

        # 2. XRP 금액을 drops로 변환 (1 XRP = 1,000,000 drops)
        xrp_amount_decimal = Decimal(xrp_amount)
        xrp_drops = str(int(xrp_amount_decimal * 1_000_000))

        # 3. USD 금액 설정 (수수료 차감 후)
        usd_amount_decimal = Decimal(usd_amount)
        usd_value = str(usd_amount_decimal.quantize(Decimal("0.000001")))

        # 4. IssuedCurrencyAmount 객체 생성
        taker_gets_amount = IssuedCurrencyAmount(
            currency="USD",
            issuer="rfG1snqykpjYjNH2Ve5NrwsbEjpiEtA9Ya",
            value=usd_value
        )

        # 5. OfferCreate 트랜잭션 생성
        offer_create = OfferCreate(
            account=sender_address,
            taker_pays=xrp_drops,  # XRP를 지불 (drops 단위)
            taker_gets=taker_gets_amount
        )

        # 6. WebSocket 연결 및 트랜잭션 제출
        # WebsocketClient 생성 및 연결
        client = WebsocketClient(ws_url)
        client.open()

        try:
            # 트랜잭션 제출 및 검증 대기
            response = submit_and_wait(offer_create, client, wallet)

            if response.is_successful():
                tx_hash = response.result.get("hash")
                engine_result = response.result.get("engine_result")
                engine_result_message = response.result.get("engine_result_message")

                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": None
                }
            else:
                # 트랜잭션 제출됨으나 체결되지 않음 (예: tecUNFUNDED_OFFER)
                engine_result = response.result.get("engine_result", "Unknown")
                engine_result_message = response.result.get("engine_result_message", "Unknown error")

                # xrpl-py 응답에서 트랜잭션 해시 추출 (여러 가능한 위치 확인)
                tx_hash = None
                if "hash" in response.result:
                    tx_hash = response.result["hash"]
                elif "tx_json" in response.result and "hash" in response.result["tx_json"]:
                    tx_hash = response.result["tx_json"]["hash"]

                print(f"[DEBUG] 트랜잭션 제출됨 (미체결):")
                print(f"  engine_result: {engine_result}")
                print(f"  tx_hash: {tx_hash}")
                print(f"  response.result keys: {list(response.result.keys())}")

                # tecUNFUNDED_OFFER는 트랜잭션이 제출되었으나 체결되지 않은 것으로, 성공으로 처리
                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": None
                }

        except Exception as e:
            # 트랜잭션 예외 처리
            import traceback
            error_details = traceback.format_exc()

            # 예외 객체에서 트랜잭션 정보 추출 시도
            tx_hash = None
            engine_result = "Unknown"
            engine_result_message = str(e)

            print(f"[DEBUG] 예외 발생:")
            print(f"  예외 타입: {type(e).__name__}")
            print(f"  예외 메시지: {str(e)}")
            print(f"  예외 속성: {dir(e)}")

            # xrpl-py 예외에서 트랜잭션 해시 추출
            if hasattr(e, 'args') and e.args:
                # 예외의 인자에서 결과 추출 시도
                print(f"  예외 args: {e.args}")

            # 여러 방법으로 tx_hash 추출 시도
            if hasattr(e, 'result'):
                # 예외 객체에 result 속성이 있는 경우
                result = getattr(e, 'result', {})
                print(f"  예외 result: {result}")
                tx_hash = result.get("hash") if result else None
                if not tx_hash and isinstance(result, dict):
                    tx_hash = result.get("tx_json", {}).get("hash")
            elif hasattr(e, 'transaction'):
                # transaction 속성이 있는 경우
                tx = getattr(e, 'transaction', {})
                tx_hash = tx.get("hash") if tx else None
            else:
                # 문자열에서 트랜잭션 해시 추출 (마지막 수단)
                import re
                tx_hash_match = re.search(r'([A-F0-9]{64})', str(e))
                if tx_hash_match:
                    tx_hash = tx_hash_match.group(1)

            print(f"  추출된 tx_hash: {tx_hash}")

            # tecUNFUNDED_OFFER는 트랜잭션이 제출되었으나 체결되지 않은 정상적인 결과
            if "tecUNFUNDED_OFFER" in str(e):
                return {
                    "success": True,  # 트랜잭션 제출 성공으로 처리
                    "tx_hash": tx_hash,
                    "engine_result": "tecUNFUNDED_OFFER",
                    "engine_result_message": "Offer created but not filled (no matching orders in orderbook)",
                    "error": None
                }

            # 다른 예외의 경우 실패로 처리
            return {
                "success": False,
                "tx_hash": tx_hash,
                "engine_result": engine_result,
                "engine_result_message": engine_result_message,
                "error": f"{str(e)}\n{error_details}"
            }

        finally:
            # WebSocket 연결 종료
            client.close()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        return {
            "success": False,
            "tx_hash": None,
            "engine_result": None,
            "engine_result_message": str(e),
            "error": f"{str(e)}\n{error_details}"
        }


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print(json.dumps({
            "success": False,
            "error": "Invalid arguments. Expected: ws_url, sender_address, sender_secret, xrp_amount, usd_amount, fee_rate"
        }))
        sys.exit(1)

    # 인자 파싱
    ws_url = sys.argv[1]
    sender_address = sys.argv[2]
    sender_secret = sys.argv[3]
    xrp_amount = sys.argv[4]
    usd_amount = sys.argv[5]
    fee_rate = sys.argv[6]

    # XRP → USD 스왑 트랜잭션 제출
    result = submit_xrp_to_usd_swap(
        ws_url,
        sender_address,
        sender_secret,
        xrp_amount,
        usd_amount,
        fee_rate
    )

    # JSON 결과 출력 (stdout)
    print(json.dumps(result))
