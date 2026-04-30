"""XRPL DEX API FastAPI 메인 애플리케이션"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.dex_client import XrplDexClient
from app.models import (
    OrderBookRequest,
    OrderBookResponse,
    SwapRequest,
    SwapResponse,
    QuoteRequest,
    QuoteResponse,
    TokensResponse,
    ErrorResponse
)
from app.auth import auth_middleware, get_optional_api_key

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# XRPL DEX 클라이언트 초기화
dex_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 라이프사이클 관리"""
    global dex_client

    # 시작 시 실행
    logger.info("XRPL DEX API 서버 시작 중...")

    try:
        dex_client = XrplDexClient(
            node_url=os.getenv("XRPL_NODE", "wss://s.altnet.rippletest.net:51233"),
            sender_address=os.getenv("SENDER_ADDRESS"),
            sender_secret=os.getenv("SENDER_SECRET"),
            fee_account=os.getenv("FEE_ACCOUNT"),
            dex_fee_rate=Decimal(os.getenv("DEX_FEE_RATE", "0.003"))
        )
        logger.info("XRPL DEX 클라이언트 초기화 완료")
    except Exception as e:
        logger.error(f"XRPL DEX 클라이언트 초기화 실패: {e}")
        raise

    yield

    # 종료 시 실행
    logger.info("XRPL DEX API 서버 종료 중...")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="XRPL DEX API",
    description="XRPL 내장 DEX를 활용한 토큰 스왑 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체 origins로 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "XRPL DEX API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "xrpl_connection": "connected" if dex_client else "disconnected"
    }


@app.get(
    "/dex/tokens",
    response_model=TokensResponse,
    tags=["DEX"],
    summary="지원 토큰 목록 조회",
    description="XRPL DEX에서 지원하는 토큰 목록을 반환합니다."
)
async def get_tokens(
    api_key: Optional[str] = Depends(get_optional_api_key)
):
    """
    지원 토큰 목록 조회

    Returns:
        TokensResponse: 지원 토큰 목록
    """
    try:
        tokens = dex_client.get_supported_tokens()

        logger.info(f"토큰 목록 조회: {len(tokens)}개 토큰")

        return TokensResponse(
            tokens=tokens,
            count=len(tokens)
        )

    except Exception as e:
        logger.error(f"토큰 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"토큰 목록 조회 실패: {str(e)}"
        )


@app.get(
    "/dex/orderbook",
    response_model=OrderBookResponse,
    tags=["DEX"],
    summary="오더북 조회",
    description="XRPL DEX 오더북을 조회하여 매수/매도 호가를 반환합니다."
)
def get_orderbook(
    base: str,
    quote: str,
    limit: int = 20,
    api_key: Optional[str] = Depends(get_optional_api_key)
):
    """
    오더북 조회

    Args:
        base: 기본 통화 (예: XRP, RLUSD)
        quote: 상대 통화 (예: XRP, RLUSD)
        limit: 반환할 호가 수 (기본값: 20)

    Returns:
        OrderBookResponse: 오더북 정보
    """
    try:
        if not dex_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DEX 클라이언트가 초기화되지 않았습니다."
            )

        # 파라미터 검증
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit은 1~100 사이여야 합니다."
            )

        # 오더북 조회 (동기 방식)
        orderbook_data = dex_client.get_orderbook(base, quote, limit)

        logger.info(f"오더북 조회: {base}/{quote}, 매도:{len(orderbook_data['asks'])}건, 매수:{len(orderbook_data['bids'])}건")

        return OrderBookResponse(
            base=base.upper(),
            quote=quote.upper(),
            bids=orderbook_data["bids"],
            asks=orderbook_data["asks"]
        )

    except ValueError as e:
        logger.error(f"오더북 조회 실패 (ValidationError): {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"오더북 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"오더북 조회 실패: {str(e)}"
        )


@app.get(
    "/dex/quote",
    response_model=QuoteResponse,
    tags=["DEX"],
    summary="스왑 견적 조회",
    description="실제 스왑 전 예상 금액을 조회합니다. 수수료가 포함된 예상 수령액을 반환합니다."
)
def get_quote(
    from_currency: str,
    to_currency: str,
    amount: str,
    api_key: Optional[str] = Depends(get_optional_api_key)
):
    """
    스왑 견적 조회

    Args:
        from_currency: 출금 통화 (예: XRP, RLUSD)
        to_currency: 입금 통화 (예: XRP, RLUSD)
        amount: 조회 금액

    Returns:
        QuoteResponse: 견적 정보
    """
    try:
        if not dex_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DEX 클라이언트가 초기화되지 않았습니다."
            )

        # 금액 변환
        try:
            amount_decimal = Decimal(str(amount))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 금액 형식입니다."
            )

        # 금액 검증
        if amount_decimal <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="금액은 0보다 커야 합니다."
            )

        # 견적 조회
        quote_data = dex_client.get_quote(
            from_currency,
            to_currency,
            amount_decimal
        )

        logger.info(f"견적 조회: {amount_decimal} {from_currency} → {to_currency}, 예상 수령: {quote_data['estimated_amount']}")

        return QuoteResponse(**quote_data)

    except ValueError as e:
        logger.error(f"견적 조회 실패 (ValidationError): {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"견적 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"견적 조회 실패: {str(e)}"
        )


@app.post(
    "/dex/swap",
    response_model=SwapResponse,
    tags=["DEX"],
    summary="토큰 스왑 실행",
    description="XRPL DEX에서 토큰 스왑을 실행합니다. X-API-Key 인증이 필요합니다."
)
def execute_swap(
    request: SwapRequest,
    api_key: str = Depends(auth_middleware.verify_api_key)
):
    """
    토큰 스왑 실행

    Args:
        request: 스왑 요청 (from_currency, to_currency, amount)
        api_key: API 키 (X-API-Key 헤더)

    Returns:
        SwapResponse: 스왑 결과
    """
    try:
        if not dex_client:
            # 동기 방식으로 로깅
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 별도 스레드에서 실행
                    import threading
                    def log_request():
                        import asyncio
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(
                            auth_middleware.log_request(api_key, "/dex/swap", False)
                        )
                        new_loop.close()
                    thread = threading.Thread(target=log_request)
                    thread.start()
                    thread.join()
            except:
                pass  # 로깅 실패해도 계속 진행

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DEX 클라이언트가 초기화되지 않았습니다."
            )

        logger.info(f"스왑 요청: {request.amount} {request.from_currency} → {request.to_currency}")

        # 스왑 실행
        swap_result = dex_client.execute_swap(
            request.from_currency,
            request.to_currency,
            request.amount
        )

        # 사용량 로깅 (간단한 처리)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 별도 스레드에서 실행
                import threading
                def log_request():
                    import asyncio
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_until_complete(
                        auth_middleware.log_request(api_key, "/dex/swap", swap_result["success"])
                    )
                    new_loop.close()
                thread = threading.Thread(target=log_request)
                thread.start()
                thread.join()
        except:
            pass  # 로깅 실패해도 계속 진행

        if swap_result["success"]:
            logger.info(f"스왑 성공: tx_hash={swap_result['tx_hash']}")
        else:
            logger.error(f"스왑 실패: {swap_result['error']}")

        return SwapResponse(**swap_result)

    except ValueError as e:
        logger.error(f"스왑 실패 (ValidationError): {e}")
        # 간단한 에러 처리
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"스왑 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스왑 실패: {str(e)}"
        )


@app.get(
    "/dex/usage",
    tags=["Admin"],
    summary="API 사용량 조회",
    description="현재 API 키의 사용량 통계를 조회합니다."
)
async def get_usage_stats(
    api_key: str = Depends(auth_middleware.verify_api_key)
):
    """
    API 사용량 조회

    Args:
        api_key: API 키 (X-API-Key 헤더)

    Returns:
        사용량 통계
    """
    try:
        stats = await auth_middleware.get_usage_stats(api_key)
        logger.info(f"사용량 조회: {api_key[:10]}... - 이번 달: {stats['this_month']}/{stats['monthly_limit']}")
        return stats

    except Exception as e:
        logger.error(f"사용량 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용량 조회 실패: {str(e)}"
        )


# 예외 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 핸들러"""
    logger.error(f"처리되지 않은 예외: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "내부 서버 오류가 발생했습니다.",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload
    )
