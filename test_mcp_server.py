"""MCP 서버 테스트 스크립트"""

import asyncio
import subprocess
import json
import sys


async def test_mcp_server():
    """MCP 서버 테스트"""

    # MCP 서버 프로세스 시작
    process = subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # 라인 버퍼링
    )

    try:
        # 초기화 요청 전송
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()

        # 응답 수신
        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print("✅ 초기화 응답:")
            print(json.dumps(response, indent=2, ensure_ascii=False))

        # 툴 목록 요청
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print("\n✅ 사용 가능한 툴:")
            for tool in response.get("result", {}).get("tools", []):
                print(f"  - {tool['name']}: {tool['description']}")

        # get_tokens 툴 호출 테스트
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_tokens",
                "arguments": {}
            }
        }

        process.stdin.write(json.dumps(call_request) + "\n")
        process.stdin.flush()

        response_line = process.stdout.readline()
        if response_line:
            response = json.loads(response_line.strip())
            print("\n✅ get_tokens 호출 결과:")
            result = json.loads(response["result"]["content"][0]["text"])
            print(json.dumps(result, indent=2, ensure_ascii=False))

        print("\n✅ MCP 서버 테스트 완료!")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
    finally:
        # 프로세스 종료
        process.stdin.close()
        process.terminate()
        process.wait()


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
