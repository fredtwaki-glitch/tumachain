import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class VerificationState(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    KYC_PENDING = "KYC_PENDING"
    KYC_VERIFIED = "KYC_VERIFIED"
    KYC_REJECTED = "KYC_REJECTED"
    SUSPENDED = "SUSPENDED"


class Network(str, enum.Enum):
    BITCOIN_TESTNET = "BITCOIN_TESTNET"
    ETHEREUM_SEPOLIA = "ETHEREUM_SEPOLIA"
    SOLANA_DEVNET = "SOLANA_DEVNET"
    EVM_TESTNET = "EVM_TESTNET"  # generic EVM-compatible test network
    ARC_TESTNET = "ARC_TESTNET"


class Asset(str, enum.Enum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    EVMT = "EVMT"  # native token of the generic EVM testnet
    USDC = "USDC"
    USDT = "USDT"


class IdentityStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class SettlementStatus(str, enum.Enum):
    CREATED = "CREATED"
    QUOTED = "QUOTED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    CONFIRMING = "CONFIRMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class WithdrawalStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class KycStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ComplianceDecision(str, enum.Enum):
    APPROVED = "APPROVED"
    HELD = "HELD"
    REJECTED = "REJECTED"
