import os
from decimal import Decimal
from uuid import UUID

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creditcard_system.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from banking.models import Card, Transaction
from banking.services import simulate_payment

app = FastAPI(title="Credit Card Payment Processor", version="1.0.0")
bearer_scheme = HTTPBearer(auto_error=False)


class PaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")


class PaymentResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    status: str
    failure_reason: str


def authenticated_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer access token required.")
    try:
        token = AccessToken(credentials.credentials)
        user = get_user_model().objects.get(pk=token["user_id"], is_active=True)
    except (TokenError, KeyError, get_user_model().DoesNotExist):
        raise HTTPException(status_code=401, detail="Invalid or expired access token.") from None
    return user


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/payments", response_model=PaymentResponse, status_code=201)
def make_payment(payload: PaymentRequest, user=Depends(authenticated_user)):
    card = Card.objects.filter(id=payload.card_id, user=user).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Saved card not found.")
    with db_transaction.atomic():
        payment = Transaction.objects.create(
            user=user, card=card, amount=payload.amount, currency=payload.currency.upper(),
            status=Transaction.Status.PENDING,
        )
        succeeded, failure_reason = simulate_payment(payment.amount)
        payment.status = Transaction.Status.SUCCESS if succeeded else Transaction.Status.FAILED
        payment.failure_reason = failure_reason
        payment.save(update_fields=("status", "failure_reason", "updated_at"))
    return PaymentResponse(
        id=payment.id, amount=payment.amount, currency=payment.currency,
        status=payment.status, failure_reason=payment.failure_reason,
    )