from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import Asset
from app.models.ledger_balance import LedgerBalance


def get_or_create_ledger_balance(db: Session, user_id: str, asset: Asset) -> LedgerBalance:
    balance = (
        db.query(LedgerBalance)
        .filter(LedgerBalance.user_id == user_id, LedgerBalance.asset == asset)
        .first()
    )
    if balance is None:
        balance = LedgerBalance(user_id=user_id, asset=asset, amount=Decimal("0"))
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def credit_ledger_balance(db: Session, user_id: str, asset: Asset, amount: Decimal) -> LedgerBalance:
    balance = get_or_create_ledger_balance(db, user_id, asset)
    balance.amount = Decimal(balance.amount) + amount
    db.commit()
    db.refresh(balance)
    return balance


def debit_ledger_balance(db: Session, user_id: str, asset: Asset, amount: Decimal) -> LedgerBalance:
    balance = get_or_create_ledger_balance(db, user_id, asset)
    if Decimal(balance.amount) < amount:
        raise ValueError("Insufficient ledger balance")
    balance.amount = Decimal(balance.amount) - amount
    db.commit()
    db.refresh(balance)
    return balance
