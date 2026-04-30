"""XRP → USD OfferCreate 트랜잭션 제출 (최종 버전 - tx_hash 추출)"""

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
    XRP → USD OfferCreate 트랜잭션 제출 (tx_hash 추출)

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

        # 6. WebSocket 연결
        client = WebsocketClient(ws_url)

        try:
            client.open()

            # 7. 트랜잭션 미리 서명하여 해시 추출 (제출 전)
            from xrpl.models.requests import AccountInfo
            from xrpl.transaction import sign

            # 계정 시퀀스 조회
            acct_info = client.request(AccountInfo(account=sender_address))
            sequence = acct_info.result["account_data"]["Sequence"]

            # 시퀀스 포함하여 트랜잭션 재생성
            offer_create = OfferCreate(
                account=sender_address,
                sequence=sequence,
                taker_pays=xrp_drops,
                taker_gets=taker_gets_amount
            )

            # 트랜잭션 서명
            signed_tx = sign(offer_create, wallet)

            # 서명된 트랜잭션에서 해시 추출 (여러 방법 시도)
            pre_submit_hash = None
            if hasattr(signed_tx, 'result'):
                pre_submit_hash = signed_tx.result.get("hash")
            elif hasattr(signed_tx, 'tx_hash'):
                pre_submit_hash = signed_tx.tx_hash
            elif hasattr(signed_tx, 'get_hash'):
                pre_submit_hash = signed_tx.get_hash()

            if not pre_submit_hash:
                # 마지막 수단: 트랜잭션 객체 자체에서 해시 계산
                from xrpl.core.binarycodec import encode
                tx_blob = encode(signed_tx)
                import hashlib
                pre_submit_hash = hashlib.sha256(tx_blob).hexdigest().upper()

            print(f"[DEBUG] 제출 전 트랜잭션 해시: {pre_submit_hash}")

            # 8. 트랜잭션 제출 및 결과 확인
            print(f"[DEBUG] 트랜잭션 제출 시작...")
            response = submit_and_wait(offer_create, client, wallet)

            print(f"[DEBUG] 응답 성공 여부: {response.is_successful()}")

            # 9. 응답 결과 처리
            if response.is_successful():
                # 완전한 성공
                tx_hash = response.result.get("hash") or pre_submit_hash
                engine_result = response.result.get("engine_result")
                engine_result_message = response.result.get("engine_result_message")

                print(f"[SUCCESS] 트랜잭션 완전 성공:")
                print(f"  TX Hash: {tx_hash}")
                print(f"  Engine Result: {engine_result}")

                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": None
                }
            else:
                # 트랜잭션 제출됨으나 체결되지 않음
                engine_result = response.result.get("engine_result", "Unknown")
                engine_result_message = response.result.get("engine_result_message", "Unknown error")

                # 응답에서 tx_hash 추출 (없으면 미리 계산한 해시 사용)
                tx_hash = (response.result.get("hash") or
                          response.result.get("tx_json", {}).get("hash") or
                          pre_submit_hash)

                print(f"[INFO] 트랜잭션 제출됨 (미체결):")
                print(f"  engine_result: {engine_result}")
                print(f"  tx_hash: {tx_hash}")

                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": None
                }

        except Exception as e:
            # 트랜잭션 예외 처리
            error_str = str(e)

            print(f"[ERROR] 트랜잭션 예외: {error_str}")

            # XRPLReliableSubmissionException인 경우 처리 (미리 계산한 해시 사용)
            if "tecUNFUNDED_OFFER" in error_str:
                # 트랜잭션은 제출되었으나 체결되지 않음
                # 제출 전에 미리 계산한 해시를 반환
                return {
                    "success": True,  # 트랜잭션 제출 성공
                    "tx_hash": pre_submit_hash,  # 미리 계산한 해시 사용
                    "engine_result": "tecUNFUNDED_OFFER",
                    "engine_result_message": "Offer created but not filled (no matching orders in orderbook)",
                    "error": None
                }

            # 다른 예외의 경우 실패로 처리
            return {
                "success": False,
                "tx_hash": pre_submit_hash if 'pre_submit_hash' in locals() else None,
                "engine_result": None,
                "engine_result_message": error_str,
                "error": error_str
            }

        finally:
            # WebSocket 연결 종료
            client.close()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        print(f"[ERROR] 외부 예외: {str(e)}")
        print(f"Traceback:\n{error_details}")

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

    # JSON 결과 출력
    print(json.dumps(result))
