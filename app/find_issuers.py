"""XRPL 테스트넷에서 USD 발행자 찾기"""

import json
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountObjects, AccountLines

def find_usd_issuers(testnet_url="https://s.altnet.rippletest.net:51233"):
    """테스트넷에서 USD issuer 찾기"""
    client = JsonRpcClient(testnet_url)

    # 일반적인 테스트넷 게이트웨이 주소들
    common_gateways = [
        "rMBzp8CgpE441cp5PVyA9rpVV7oT8hP3ys",  # Gatehub
        "rhub8VRN55s94qWKDv6jmDc1roQzK4J775",  # Bitstamp testnet
        "razqQKzJRdB4UxFPWf5NEsEG4XosseLD",    # Hot wallet
    ]

    print("일반적인 테스트넷 게이트웨이에서 USD 찾기...")

    for gateway in common_gateways:
        try:
            # 계정의 trustlines 조회
            account_lines = AccountLines(
                account=gateway,
                peer="",
            )

            response = client.request(account_lines)

            if response.is_successful():
                lines = response.result.get("lines", [])

                for line in lines:
                    if line.get("currency") == "USD":
                        issuer = line.get("account")
                        print(f"USD issuer 발견: {issuer}")
                        print(f"  Balance: {line.get('balance')}")
                        print(f"  Limit: {line.get('limit')}")
                        return issuer

        except Exception as e:
            print(f"Error checking {gateway}: {e}")
            continue

    print("\n테스트넷에서 USD issuer를 찾지 못했습니다.")
    print("직접 USD를 발행해야 합니다.")
    return None

if __name__ == "__main__":
    issuer = find_usd_issuers()

    if issuer:
        print(f"\n추천 USD issuer: {issuer}")
    else:
        print("\nUSD issuer를 찾지 못했습니다.")
        print("테스트넷 faucet에서 USD를 발행하거나, XRP만 사용해야 합니다.")
