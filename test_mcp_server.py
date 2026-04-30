"""MCP 서버 테스트 스크립트 (FastMCP)"""

# MCP 서버의 함수를 직접 import하여 테스트
from mcp_server import get_tokens, get_orderbook, get_quote, swap_tokens
import json


def test_mcp_tools():
    """MCP 툴 테스트"""

    print("🚀 MCP 서버 툴 테스트 시작...")

    # 1. get_tokens 테스트
    print("\n1. get_tokens 테스트...")
    try:
        tokens_result = get_tokens()
        tokens = json.loads(tokens_result)
        print("✅ get_tokens 성공:")
        print(f"   - 지원 토큰 수: {tokens.get('count', 0)}")
        for token in tokens.get('tokens', []):
            print(f"   - {token['name']} ({token['currency']})")
    except Exception as e:
        print(f"❌ get_tokens 실패: {e}")

    # 2. get_orderbook 테스트
    print("\n2. get_orderbook 테스트...")
    try:
        orderbook_result = get_orderbook("XRP", "USD", 5)
        orderbook = json.loads(orderbook_result)
        print("✅ get_orderbook 성공:")
        print(f"   - 매도 호가 수: {len(orderbook.get('asks', []))}")
        print(f"   - 매수 호가 수: {len(orderbook.get('bids', []))}")
    except Exception as e:
        print(f"❌ get_orderbook 실패: {e}")

    # 3. get_quote 테스트
    print("\n3. get_quote 테스트...")
    try:
        quote_result = get_quote("XRP", "USD", "100")
        quote = json.loads(quote_result)
        print("✅ get_quote 성공:")
        print(f"   - 출금: {quote.get('from_amount')} {quote.get('from_currency')}")
        print(f"   - 입금: {quote.get('to_amount')} {quote.get('to_currency')}")
        print(f"   - 수수료: {quote.get('fee')} ({quote.get('fee_rate')})")
    except Exception as e:
        print(f"❌ get_quote 실패: {e}")

    # 4. swap_tokens 테스트 (소액)
    print("\n4. swap_tokens 테스트...")
    try:
        swap_result = swap_tokens("XRP", "USD", "1")
        swap = json.loads(swap_result)
        print("✅ swap_tokens 성공:")
        print(f"   - 성공 여부: {swap.get('success')}")
        print(f"   - 트랜잭션 해시: {swap.get('tx_hash')}")
        if swap.get('error'):
            print(f"   - 에러: {swap['error']}")
    except Exception as e:
        print(f"❌ swap_tokens 실패: {e}")

    print("\n✅ MCP 서버 툴 테스트 완료!")


if __name__ == "__main__":
    test_mcp_tools()
