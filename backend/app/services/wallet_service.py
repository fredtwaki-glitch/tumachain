from decimal import Decimal

from sqlalchemy.orm import Session

from app.blockchain.adapter import get_adapter
from app.models.enums import Network
from app.models.user import User
from app.models.wallet import Wallet

SUPPORTED_NETWORKS = [
    Network.BITCOIN_TESTNET,
    Network.ETHEREUM_SEPOLIA,
    Network.SOLANA_DEVNET,
    Network.EVM_TESTNET,
    Network.ARC_TESTNET,
]


def create_wallets_for_user(db: Session, user: User) -> list[Wallet]:
    wallets = []
    for network in SUPPORTED_NETWORKS:
        adapter = get_adapter(network)
        address, mock_private_key = adapter.generate_address(user.id)
        wallet = Wallet(
            user_id=user.id,
            network=network,
            address=address,
            _mock_private_key=mock_private_key,
            balance=0,
        )
        db.add(wallet)
        wallets.append(wallet)
    db.commit()
    for w in wallets:
        db.refresh(w)
    return wallets


def faucet_credit(db: Session, user: User, network: Network, amount: Decimal) -> Wallet:
    """
    TESTNET-ONLY helper: credits a user's mock wallet balance so payment
    and withdrawal flows can be exercised without ever touching real
    cryptocurrency. There is no equivalent of this in a production
    build — real funds would arrive via an actual on-chain deposit.
    """
    wallet = (
        db.query(Wallet).filter(Wallet.user_id == user.id, Wallet.network == network).first()
    )
    if wallet is None:
        raise ValueError("No wallet found for that network")
    wallet.balance = Decimal(wallet.balance) + amount
    db.commit()
    db.refresh(wallet)
    return wallet


def ensure_missing_wallets_for_user(db: Session, user: User) -> list[Wallet]:
    """Backfill wallets introduced by later testnet networks without rotating existing wallets."""
    existing = {w.network for w in db.query(Wallet).filter(Wallet.user_id == user.id).all()}
    created = []
    for network in SUPPORTED_NETWORKS:
        if network in existing:
            continue
        adapter = get_adapter(network)
        address, mock_private_key = adapter.generate_address(user.id)
        wallet = Wallet(user_id=user.id, network=network, address=address,
                        _mock_private_key=mock_private_key, balance=0)
        db.add(wallet); created.append(wallet)
    if created:
        db.commit()
        for w in created: db.refresh(w)
    return created
