"""Pydantic 데이터 모델 정의"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class OrderBookRequest(BaseModel):
    """오더북 조회 요청"""
    base: str = Field(..., description="기본 통화 (예: XRP, RLUSD)")
    quote: str = Field(..., description="상대 통화 (예: XRP, RLUSD)")

    @validator('base', 'quote')
    def validate_currency(cls, v):
        """통화 코드 검증"""
        if not v or len(v) > 40:
            raise ValueError('유효하지 않은 통화 코드')
        return v.upper()


class OrderBookResponse(BaseModel):
    """오더북 조회 응답"""
    base: str
    quote: str
    bids: List[dict] = Field(default_factory=list, description="매수 호가")
    asks: List[dict] = Field(default_factory=list, description="매도 호가")
    timestamp: datetime = Field(default_factory=datetime.now)


class SwapRequest(BaseModel):
    """스왑 요청"""
    from_currency: str = Field(..., description="출금 통화")
    to_currency: str = Field(..., description="입금 통화")
    amount: Decimal = Field(..., gt=0, description="스왑 금액")

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        """통화 코드 검증"""
        if not v or len(v) > 40:
            raise ValueError('유효하지 않은 통화 코드')
        return v.upper()


class SwapResponse(BaseModel):
    """스왑 응답"""
    success: bool
    tx_hash: Optional[str] = None
    from_currency: str
    to_currency: str
    from_amount: Decimal
    to_amount: Optional[Decimal] = None
    fee: Decimal
    fee_rate: Decimal
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class QuoteRequest(BaseModel):
    """견적 조회 요청"""
    from_currency: str = Field(..., description="출금 통화")
    to_currency: str = Field(..., description="입금 통화")
    amount: Decimal = Field(..., gt=0, description="조회 금액")

    @validator('from_currency', 'to_currency')
    def validate_currency(cls, v):
        """통화 코드 검증"""
        if not v or len(v) > 40:
            raise ValueError('유효하지 않은 통화 코드')
        return v.upper()


class QuoteResponse(BaseModel):
    """견적 조회 응답"""
    from_currency: str
    to_currency: str
    from_amount: Decimal
    to_amount: Decimal
    fee: Decimal
    fee_rate: Decimal
    estimated_amount: Decimal
    price_impact: Optional[Decimal] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class TokenInfo(BaseModel):
    """토큰 정보"""
    currency: str = Field(..., description="통화 코드")
    issuer: Optional[str] = Field(None, description="발행자 주소 (XRP인 경우 None)")
    name: str = Field(..., description="토큰 이름")
    decimals: int = Field(default=6, description="소수점 자리수")


class TokensResponse(BaseModel):
    """지원 토큰 목록 응답"""
    tokens: List[TokenInfo]
    count: int
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
