"""USD trustline 설정 스크립트"""

import sys
import json


def setup_usd_trustline(
    ws_url: str,
    sender_address: str,
    sender_secret: str,
    issuer_address: str = "rfG1snqykpjYjNH2Ve5NrwsbEjpiEtA9Ya"
) -> str:
    """
    USD trustline 설정

    Args:
        ws_url: XRPL WebSocket URL
        sender_address: 발신 주소
        sender_secret: 시크릿 키
        issuer_address: USD issuer 주소

    Returns:
        JSON 형식 트랜잭션 결과
    """
    try:
        from xrpl.clients import WebsocketClient
        from xrpl.wallet import Wallet
        from xrpl.models.transactions import TrustSet
        from xrpl.models.amounts import IssuedCurrencyAmount
        from xrpl.transaction import submit_and_wait

        # 1. 지갑 생성
        wallet = Wallet.from_seed(sender_secret)

        print(f"[DEBUG] TrustSet 트랜잭션 생성:")
        print(f"  Account: {sender_address}")
        print(f"  Currency: USD")
        print(f"  Issuer: {issuer_address}")

        # 2. TrustSet 트랜잭션 생성
        trust_set = TrustSet(
            account=sender_address,
            limit_amount=IssuedCurrencyAmount(
                currency="USD",
                issuer=issuer_address,
                value="1000000"  # 1백만 USD 한도
            )
        )

        print(f"[DEBUG] 트랜잭션 객체 생성 완료:")
        print(f"  Account: {trust_set.account}")
        print(f"  LimitAmount: {trust_set.limit_amount}")

        # 3. WebSocket 연결 및 트랜잭션 제출
        print(f"[DEBUG] WebSocket 연결 및 트랜잭션 제출 시작...")

        with WebsocketClient(ws_url) as client:
            # 트랜잭션 제출 및 검증 대기
            response = submit_and_wait(trust_set, client, wallet)

            print(f"[DEBUG] 트랜잭션 응답 수신:")
            print(f"  성공 여부: {response.is_successful()}")

            if response.is_successful():
                tx_hash = response.result.get("hash")
                engine_result = response.result.get("engine_result")
                engine_result_message = response.result.get("engine_result_message")

                print(f"[SUCCESS] TrustLine 설정 성공:")
                print(f"  TX Hash: {tx_hash}")
                print(f"  Engine Result: {engine_result}")
                print(f"  Message: {engine_result_message}")

                return json.dumps({
                    "success": True,
                    "tx_hash": tx_hash,
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": None
                }, indent=2)
            else:
                # 트랜잭션 실패
                engine_result = response.result.get("engine_result", "Unknown")
                engine_result_message = response.result.get("engine_result_message", "Unknown error")

                print(f"[FAILED] TrustLine 설정 실패:")
                print(f"  Engine Result: {engine_result}")
                print(f"  Message: {engine_result_message}")

                return json.dumps({
                    "success": False,
                    "tx_hash": response.result.get("hash"),
                    "engine_result": engine_result,
                    "engine_result_message": engine_result_message,
                    "error": engine_result_message
                }, indent=2)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        print(f"[ERROR] 예외 발생:")
        print(f"  {str(e)}")
        print(f"  Traceback:\n{error_details}")

        return json.dumps({
            "success": False,
            "tx_hash": None,
            "engine_result": None,
            "engine_result_message": str(e),
            "error": f"{str(e)}\n{error_details}"
        }, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(json.dumps({
            "success": False,
            "error": "Invalid arguments. Expected: ws_url, sender_address, sender_secret, [issuer_address]"
        }))
        sys.exit(1)

    # 인자 파싱
    ws_url = sys.argv[1]
    sender_address = sys.argv[2]
    sender_secret = sys.argv[3]
    issuer_address = sys.argv[4] if len(sys.argv) > 4 else "rfG1snqykpjYjNH2Ve5NrwsbEjpiEtA9Ya"

    # USD trustline 설정
    result = setup_usd_trustline(
        ws_url,
        sender_address,
        sender_secret,
        issuer_address
    )

    print(result)
