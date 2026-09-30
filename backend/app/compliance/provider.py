"""
KYC/AML compliance provider abstraction.

`MockComplianceProvider` never contacts a real identity-verification or
sanctions-screening service — it approves any KYC submission that looks
structurally complete and returns a low, deterministic risk score. A
`ProductionComplianceProvider` implementing the same interface would
plug in a real provider (Jumio, Onfido, ComplyAdvantage, etc.) later
without changing any calling code.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class KycCheckResult:
    approved: bool
    reason: Optional[str] = None


@dataclass
class RiskAssessment:
    risk_score: int  # 0 (lowest) - 100 (highest)
    is_high_risk: bool
    reason: Optional[str] = None


class ComplianceProvider(ABC):
    @abstractmethod
    def verify_identity(
        self, full_name: str, country: str, document_type: str, document_reference: str
    ) -> KycCheckResult:
        raise NotImplementedError

    @abstractmethod
    def screen_sanctions(self, full_name: str, country: str) -> bool:
        """Returns True if the person is clear (NOT on a sanctions list)."""
        raise NotImplementedError

    @abstractmethod
    def assess_risk(self, amount_usd: Decimal, country: str) -> RiskAssessment:
        raise NotImplementedError


class MockComplianceProvider(ComplianceProvider):
    """
    TESTNET/SIMULATED ONLY. Approves any structurally-complete
    submission and flags only clearly-synthetic "test sanctioned"
    inputs, so the workflow can be exercised deterministically without
    a real KYC/sanctions vendor.
    """

    # A reserved, obviously-fake name used only by the test suite to
    # exercise the sanctions-hit path deterministically.
    SIMULATED_SANCTIONED_NAME = "Sanctioned Test Person"

    def verify_identity(
        self, full_name: str, country: str, document_type: str, document_reference: str
    ) -> KycCheckResult:
        if not full_name or not country or not document_type or not document_reference:
            return KycCheckResult(approved=False, reason="Incomplete submission")
        return KycCheckResult(approved=True)

    def screen_sanctions(self, full_name: str, country: str) -> bool:
        return full_name.strip() != self.SIMULATED_SANCTIONED_NAME

    def assess_risk(self, amount_usd: Decimal, country: str) -> RiskAssessment:
        # Deliberately simple, deterministic mock scoring: larger amounts
        # score higher. A real provider would factor in many more signals.
        score = min(int(amount_usd / Decimal("1000")), 100)
        return RiskAssessment(risk_score=score, is_high_risk=score >= 80)


compliance_provider = MockComplianceProvider()
