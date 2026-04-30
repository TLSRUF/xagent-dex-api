"""XRPL DEX 클라이언트 구현"""

import json
import asyncio
import os
import time
from typing import List, Optional, Dict, Any
from decimal import Decimal
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.requests import BookOffers
from xrpl.models.transactions import OfferCreate, Transaction
from xrpl.transaction import sign_and_submit
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.currencies import XRP, IssuedCurrency
from xrpl.core.addresscodec import is_valid_xaddress, is_valid_classic_address
import logging

logger = logging.getLogger(__name__)


class XrplDexClient:
    """XRPL DEX 클라이언트"""

    def __init__(
        self,
        node_url: str,
        sender_address: str,
        sender_secret: str,
        fee_account: str,
        dex_fee_rate: Decimal = Decimal("0.003")
    ):
        """
        XRPL DEX 클라이언트 초기화

        Args:
            node_url: XRPL 노드 URL
            sender_address: 발신 주소
            sender_secret: 시크릿 키
            fee_account: 수수료 수신 계정
            dex_fee_rate: DEX 수수료율
        """
        self.node_url = node_url
        self.client = JsonRpcClient(node_url)
        self.wallet = Wallet.from_seed(sender_secret)
        self.sender_address = sender_address
        self.fee_account = fee_account
        self.dex_fee_rate = dex_fee_rate

        # 지원 토큰 정의
        self.supported_tokens = {
            "XRP": {
                "currency": "XRP",
                "issuer": None,
                "name": "XRP",
                "decimals": 6
            },
            "USD": {
                "currency": "USD",
                "issuer": "rvYAfWj5gh67QVQisdnQzVQZ75Y2uTxgg",  # Bitstamp USD
                "name": "USD (Bitstamp)",
                "decimals": 6
            }
        }

    def _get_currency_info(self, currency: str) -> Optional[Dict[str, Any]]:
        """통화 정보 조회"""
        return self.supported_tokens.get(currency.upper())

    def _validate_currency(self, currency: str) -> bool:
        """통화 코드 검증"""
        return currency.upper() in self.supported_tokens

    def _convert_to_amount(self, currency: str, amount: Decimal) -> Dict[str, Any]:
        """
        금액을 XRPL 포맷으로 변환

        Args:
            currency: 통화 코드
            amount: 금액

        Returns:
            XRPL 포맷의 금액 딕셔너리
        """
        currency_info = self._get_currency_info(currency)
        if not currency_info:
            raise ValueError(f"지원하지 않는 통화: {currency}")

        if currency_info["issuer"] is None:
            # XRP의 경우 drops로 변환
            return str(int(amount * 1_000_000))
        else:
            # 토큰의 경우 IssuedCurrencyAmount
            return {
                "currency": currency_info["currency"],
                "issuer": currency_info["issuer"],
                "value": str(amount)
            }

    def get_orderbook(
        self,
        base: str,
        quote: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        오더북 조회 (subprocess + WebSocket 사용)

        Args:
            base: 기본 통화
            quote: 상대 통화
            limit: 반환할 호가 수

        Returns:
            오더북 정보
        """
        if not self._validate_currency(base) or not self._validate_currency(quote):
            raise ValueError(f"지원하지 않는 통화 쌍: {base}/{quote}")

        base_info = self._get_currency_info(base)
        quote_info = self._get_currency_info(quote)

        # WebSocket URL로 변환
        ws_url = self.node_url.replace("https://", "wss://").replace("http://", "ws://")

        # 별도 프로세스에서 WebSocket 실행 (asyncio 문제 회피)
        import subprocess

        helper_script = os.path.join(os.getcwd(), "app", "websocket_helper.py")

        # subprocess 명령어 구성
        cmd = [
            "python",
            helper_script,
            ws_url,
            base_info["currency"],
            base_info.get("issuer") or "",  # None 방지
            quote_info["currency"],
            quote_info.get("issuer") or "",  # None 방지
            str(limit),
            ""  # placeholder
        ]

        # subprocess 실행
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            raise Exception(f"Helper script failed: {error_msg}")

        # 결과 파싱
        response_data = json.loads(result.stdout.strip())

        if not response_data.get("success"):
            raise Exception(response_data.get("error", "Unknown error"))

        offers = response_data.get("offers", [])

        # 결과 포맷팅
        bids = []
        asks = []

        for offer in offers:
            offer_data = {
                "price": Decimal(offer["price"]),
                "amount": Decimal(offer["amount"]),
                "account": offer["account"],
                "sequence": offer["sequence"]
            }

            # 매수/매도 구분
            if Decimal(offer["price"]) > 0:
                bids.append(offer_data)
            else:
                asks.append(offer_data)

        # 정렬
        bids.sort(key=lambda x: x["price"], reverse=True)
        asks.sort(key=lambda x: x["price"])

        return {
            "bids": bids[:limit],
            "asks": asks[:limit]
        }

    def get_quote(
        self,
        from_currency: str,
        to_currency: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        스왑 견적 조회 (완전히 동기 방식)

        Args:
            from_currency: 출금 통화
            to_currency: 입금 통화
            amount: 조회 금액

        Returns:
            견적 정보
        """
        if not self._validate_currency(from_currency) or not self._validate_currency(to_currency):
            raise ValueError(f"지원하지 않는 통화 쌍: {from_currency}/{to_currency}")

        # 수수료 계산
        fee = amount * self.dex_fee_rate
        amount_after_fee = amount - fee

        # 간단한 견적 계산 (오더북 없이)
        try:
            # 단순화된 1:1 가격 (수수료만 차감)
            to_amount = amount_after_fee

            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "from_amount": amount,
                "to_amount": to_amount.quantize(Decimal("0.000001")),
                "fee": fee.quantize(Decimal("0.000001")),
                "fee_rate": self.dex_fee_rate,
                "estimated_amount": (to_amount - fee).quantize(Decimal("0.000001"))
            }

        except Exception as e:
            logger.error(f"견적 조회 실패: {e}")
            raise

    def execute_swap(
        self,
        from_currency: str,
        to_currency: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        스왑 실행 (실제 XRPL 트랜잭션 제출)

        Args:
            from_currency: 출금 통화
            to_currency: 입금 통화
            amount: 스왑 금액

        Returns:
            트랜잭션 결과
        """
        if not self._validate_currency(from_currency) or not self._validate_currency(to_currency):
            raise ValueError(f"지원하지 않는 통화 쌍: {from_currency}/{to_currency}")

        try:
            # 수수료 계산
            fee = amount * self.dex_fee_rate
            amount_after_fee = amount - fee

            # WebSocket URL로 변환
            ws_url = self.node_url.replace("https://", "wss://").replace("http://", "ws://")

            # 별도 프로세스에서 실제 트랜잭션 제출
            import subprocess

            helper_script = os.path.join(os.getcwd(), "app", "simple_swap_helper.py")

            from_info = self._get_currency_info(from_currency)
            to_info = self._get_currency_info(to_currency)

            # subprocess 명령어 구성
            cmd = [
                "python",
                helper_script,
                ws_url,                    # WebSocket URL
                self.sender_address,       # 발신 주소
                self.wallet.seed,          # 시크릿 키
                from_info["currency"],     # 출금 통화
                from_info.get("issuer") or "",  # 출금 통화 발행자
                to_info["currency"],       # 입금 통화
                to_info.get("issuer") or "",    # 입금 통화 발행자
                str(amount_after_fee),     # 금액 (수수료 차감 후)
                str(self.dex_fee_rate),     # 수수료율
                ""                          # placeholder
            ]

            # subprocess 실행 (60초 타임아웃)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                logger.error(f"Swap helper failed: {error_msg}")
                return {
                    "success": False,
                    "tx_hash": None,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "from_amount": amount,
                    "to_amount": None,
                    "fee": fee,
                    "fee_rate": self.dex_fee_rate,
                    "error": f"트랜잭션 제출 실패: {error_msg}"
                }

            # 결과 파싱
            response_data = json.loads(result.stdout.strip())

            if response_data.get("success"):
                # 트랜잭션 성공
                return {
                    "success": True,
                    "tx_hash": response_data.get("tx_hash"),
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "from_amount": amount,
                    "to_amount": amount_after_fee,
                    "fee": fee,
                    "fee_rate": self.dex_fee_rate,
                    "error": None
                }
            else:
                # 트랜잭션 실패
                return {
                    "success": False,
                    "tx_hash": None,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "from_amount": amount,
                    "to_amount": None,
                    "fee": fee,
                    "fee_rate": self.dex_fee_rate,
                    "error": response_data.get("error", "Unknown error")
                }

        except Exception as e:
            logger.error(f"스왑 실행 실패: {e}")
            return {
                "success": False,
                "tx_hash": None,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "from_amount": amount,
                "to_amount": None,
                "fee": amount * self.dex_fee_rate,
                "fee_rate": self.dex_fee_rate,
                "error": str(e)
            }

    def get_supported_tokens(self) -> List[Dict[str, Any]]:
        """지원 토큰 목록 반환"""
        return list(self.supported_tokens.values())
