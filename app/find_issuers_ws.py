"""WebSocket을 사용한 USD issuer 찾기"""

import json
from xrpl.clients import WebsocketClient
from xrpl.models.requests import AccountLines

def find_usd_issuers_websocket(ws_url="wss://s.altnet.rippletest.net:51233"):
    """WebSocket을 사용하여 USD issuer 찾기"""
    print("WebSocket을 사용하여 USD issuer 찾기...")

    # 일반적인 테스트넷 게이트웨이 주소들
    common_gateways = [
        "rMBzp8CgpE441cp5PVyA9rpVV7oT8hP3ys",  # Gatehub
        "rhub8VRN55s94qWKDv6jmDc1roQzK4J775",  # Bitstamp testnet
        "razqQKzJRdB4UxFPWf5NEsEG4XosseLD",    # Hot wallet
        "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",  # Ripple
    ]

    with WebsocketClient(ws_url) as client:
        for gateway in common_gateways:
            try:
                # 계정의 trustlines 조회
                account_lines = AccountLines(
                    account=gateway,
                )

                response = client.request(account_lines)

                if response.is_successful():
                    lines = response.result.get("lines", [])

                    print(f"\n{gateway}의 trustlines:")

                    for line in lines:
                        currency = line.get("currency")
                        if currency == "USD":
                            issuer = line.get("account")
                            balance = line.get("balance")
                            print(f"  USD 발견!")
                            print(f"    Account: {issuer}")
                            print(f"    Balance: {balance}")
                            return issuer
                        else:
                            print(f"  {currency}: {line.get('balance')}")

                else:
                    print(f"Error checking {gateway}: {response.result.get('error_message')}")

            except Exception as e:
                print(f"Error checking {gateway}: {e}")
                continue

    print("\n테스트넷에서 USD issuer를 찾지 못했습니다.")
    return None

if __name__ == "__main__":
    issuer = find_usd_issuers_websocket()

    if issuer:
        print(f"\n추천 USD issuer: {issuer}")

        # 유효성 검사
        from xrpl.core.addresscodec import is_valid_classic_address
        if is_valid_classic_address(issuer):
            print("이 주소는 유효한 XRPL 주소입니다.")
        else:
            print("이 주소는 유효하지 않습니다.")
    else:
        print("\nUSD issuer를 찾지 못했습니다.")
        print("테스트넷 faucet에서 USD를 발행하거나, XRP만 사용해야 합니다.")
