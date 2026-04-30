"""XRP → USD OfferCreate 트랜잭션 제출 (개선된 버전 - tx_hash 추출)"""

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
    XRP → USD OfferCreate 트랜잭션 제출 (tx_hash 추출 개선)

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
        from xrpl.models.requests import AccountInfo, Submit, Ledger, Fee
        from xrpl.transaction import sign
        from decimal import Decimal

        # 1. 지갑 생성
        wallet = Wallet.from_seed(sender_secret)

        # 2. XRP 금액을 drops로 변환 (1 XRP = 1,000,000 drops)
        xrp_amount_decimal = Decimal(xrp_amount)
        xrp_drops = str(int(xrp_amount_decimal * 1_000_000))

        # 3. USD 금액 설정 (수수료 차감 후)
        usd_amount_decimal = Decimal(usd_amount)
        usd_value = str(usd_amount_decimal.quantize(Decimal("0.000001")))

        print(f"[DEBUG] OfferCreate 트랜잭션 생성:")
        print(f"  TakerPays: {xrp_drops} drops ({xrp_amount} XRP)")
        print(f"  TakerGets: {usd_value} USD (issuer: rfG1snqykpjYjNH2Ve5NrwsbEjpiEtA9Ya)")

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

            # 7. 계정 정보 조회 (시퀀스 얻기)
            acct_info_req = AccountInfo(account=sender_address)
            acct_info = client.request(acct_info_req)

            if not acct_info.is_successful():
                raise Exception(f"계정 정보 조회 실패: {acct_info.result.get('error_message')}")

            sequence = acct_info.result["account_data"]["Sequence"]
            print(f"[DEBUG] 계정 시퀀스: {sequence}")

            # 8. OfferCreate 트랜잭션 재생성 (시퀀스 포함)
            offer_create = OfferCreate(
                account=sender_address,
                sequence=sequence,
                taker_pays=xrp_drops,  # XRP를 지불 (drops 단위)
                taker_gets=taker_gets_amount
            )

            # 8. 트랜잭션 서명 및 제출 (tx_hash 추출을 위해 별도 처리)
            print(f"[DEBUG] 트랜잭션 서명 및 제출 시작...")

            # 트랜잭션 직접 서명
            signed_tx = sign(offer_create, wallet)

            # 서명된 트랜잭션에서 해시 추출
            if hasattr(signed_tx, 'result'):
                tx_hash = signed_tx.result.get("hash")
            elif hasattr(signed_tx, 'get_hash'):
                tx_hash = signed_tx.get_hash()
            else:
                # 마지막 수단: 트랜잭션 계산
                from xrpl.core.keypairs import sign
                from xrpl.core.binarycodec import encode
                tx_blob = encode(signed_tx.to_dict())
                import hashlib
                tx_hash = hashlib.sha256(tx_blob).hexdigest().upper()

            print(f"[DEBUG] 서명된 트랜잭션 해시: {tx_hash}")
            print(f"[DEBUG] signed_tx 타입: {type(signed_tx)}")
            print(f"[DEBUG] signed_tx 속성: {dir(signed_tx)[:20]}")  # 처음 20개 속성만

            # 9. 트랜잭션 제출
            print(f"[DEBUG] 트랜잭션 제출 시작...")

            # 트랜잭션을 blob으로 변환
            from xrpl.core.binarycodec import encode
            tx_blob = encode(signed_tx.to_dict())

            print(f"[DEBUG] 트랜잭션 blob (처음 100자): {tx_blob[:100]}...")

            submit_result = client.request(Submit(tx_blob=tx_blob))

            print(f"[DEBUG] 제출 결과 성공 여부: {submit_result.is_successful()}")
            print(f"[DEBUG] 제출 결과: {submit_result.result}")

            if submit_result.is_successful():
                engine_result = submit_result.result.get("engine_result", "Unknown")
                engine_result_message = submit_result.result.get("engine_result_message", "Unknown")

                # 제출 응답에서 tx_hash 추출 (여러 가능한 위치 확인)
                final_tx_hash = submit_result.result.get("hash") or \
                                submit_result.result.get("tx_json", {}).get("hash") or \
                                tx_hash  # 서명된 트랜잭션의 해시 사용

                print(f"[SUCCESS] 트랜잭션 제출 성공:")
                print(f"  최종 TX Hash: {final_tx_hash}")
                print(f"  Engine Result: {engine_result}")
                print(f"  Message: {engine_result_message}")

                # 결과 판정
                if engine_result == "tesSUCCESS":
                    # 완전한 성공
                    return {
                        "success": True,
                        "tx_hash": final_tx_hash,
                        "engine_result": engine_result,
                        "engine_result_message": engine_result_message,
                        "error": None
                    }
                elif engine_result.startswith("tec"):  # tecUNFUNDED_OFFER 등
                    # 트랜잭션은 제출되었으나 체결되지 않음 (정상적인 결과)
                    return {
                        "success": True,  # 트랜잭션 제출 성공으로 처리
                        "tx_hash": final_tx_hash,
                        "engine_result": engine_result,
                        "engine_result_message": engine_result_message,
                        "error": None
                    }
                else:
                    # 트랜잭션 실패 (제출은 됐으나 실패)
                    return {
                        "success": False,
                        "tx_hash": final_tx_hash,
                        "engine_result": engine_result,
                        "engine_result_message": engine_result_message,
                        "error": engine_result_message
                    }
            else:
                # 제출 자체가 실패
                error_msg = submit_result.result.get("error_message", "Unknown error")
                print(f"[FAILED] 트랜잭션 제출 실패:")
                print(f"  Error: {error_msg}")

                return {
                    "success": False,
                    "tx_hash": tx_hash,  # 서명된 트랜잭션의 해시 반환
                    "engine_result": "Unknown",
                    "engine_result_message": error_msg,
                    "error": error_msg
                }

            print(f"[DEBUG] 제출 결과 성공 여부: {submit_result.is_successful()}")
            print(f"[DEBUG] 제출 결과: {submit_result.result}")

            if submit_result.is_successful():
                engine_result = submit_result.result.get("engine_result", "Unknown")
                engine_result_message = submit_result.result.get("engine_result_message", "Unknown")

                # 제출 응답에서 tx_hash 추출 (여러 가능한 위치 확인)
                final_tx_hash = submit_result.result.get("hash") or \
                                submit_result.result.get("tx_json", {}).get("hash") or \
                                tx_hash  # 서명된 트랜잭션의 해시 사용

                print(f"[SUCCESS] 트랜잭션 제출 성공:")
                print(f"  최종 TX Hash: {final_tx_hash}")
                print(f"  Engine Result: {engine_result}")
                print(f"  Message: {engine_result_message}")

                # 결과 판정
                if engine_result == "tesSUCCESS":
                    # 완전한 성공
                    return {
                        "success": True,
                        "tx_hash": final_tx_hash,
                        "engine_result": engine_result,
                        "engine_result_message": engine_result_message,
                        "error": None
                    }
                elif engine_result.startswith("tec"):  # tecUNFUNDED_OFFER 등
                    # 트랜잭션은 제출되었으나 체결되지 않음 (정상적인 결과)
                    return {
                        "success": True,  # 트랜잭션 제출 성공으로 처리
                        "tx_hash": final_tx_hash,
                        "engine_result": engine_result,
                        "engine_result_message": engine_result_message,
                        "error": None
                    }
                else:
                    # 트랜잭션 실패 (제출은 됐으나 실패)
                    return {
                        "success": False,
                        "tx_hash": final_tx_hash,
                        "engine_result": engine_result,
                        "engine_result_message": engine_result_message,
                        "error": engine_result_message
                    }
            else:
                # 제출 자체가 실패
                error_msg = submit_result.result.get("error_message", "Unknown error")
                print(f"[FAILED] 트랜잭션 제출 실패:")
                print(f"  Error: {error_msg}")

                return {
                    "success": False,
                    "tx_hash": tx_hash,  # 서명된 트랜잭션의 해시 반환
                    "engine_result": "Unknown",
                    "engine_result_message": error_msg,
                    "error": error_msg
                }

        except Exception as e:
            # 트랜잭션 예외 처리
            import traceback
            error_details = traceback.format_exc()

            print(f"[ERROR] 트랜잭션 예외:")
            print(f"  {str(e)}")
            print(f"  Traceback:\n{error_details}")

            return {
                "success": False,
                "tx_hash": None,
                "engine_result": None,
                "engine_result_message": str(e),
                "error": f"{str(e)}\n{error_details}"
            }

        finally:
            # WebSocket 연결 종료
            client.close()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        print(f"[ERROR] 예외 발생:")
        print(f"  {str(e)}")
        print(f"  Traceback:\n{error_details}")

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
