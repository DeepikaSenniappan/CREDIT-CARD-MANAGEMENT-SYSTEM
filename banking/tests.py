from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from fastapi.testclient import TestClient

from banking.models import AdminLog, Card, Transaction
from fastapi_app.main import app

User = get_user_model()


class AuthenticationTests(TestCase):
    def test_registration_hashes_password_and_login_returns_tokens(self):
        client = APIClient()
        response = client.post("/api/auth/register/", {
            "username": "sam", "email": "sam@example.com", "password": "Correct-Horse-98!",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="sam@example.com")
        self.assertNotEqual(user.password, "Correct-Horse-98!")
        self.assertTrue(user.check_password("Correct-Horse-98!"))
        login = client.post("/api/auth/login/", {
            "email": "sam@example.com", "password": "Correct-Horse-98!",
        }, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)
        self.assertIn("refresh", login.data)

    def test_protected_cards_endpoint_requires_authentication(self):
        self.assertEqual(APIClient().get("/api/cards/").status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        user = User.objects.create_user(username="pat", email="pat@example.com", password="Strong-Pass-987!")
        refresh = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = client.post("/api/auth/logout/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(response.status_code, 205)


class CardManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lee", email="lee@example.com", password="Strong-Pass-987!")
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}")

    def card_payload(self, **overrides):
        payload = {
            "provider_payment_method_id": "pm_test_123", "brand": "Visa", "last4": "4242",
            "card_type": "CREDIT", "expiry_month": 12, "expiry_year": 2030,
        }
        payload.update(overrides)
        return payload

    def test_card_creation_returns_mask_and_never_raw_number(self):
        response = self.client.post("/api/cards/", self.card_payload(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["masked_number"], "**** **** **** 4242")
        self.assertNotIn("provider_payment_method_id", response.data)
        self.assertFalse(hasattr(Card, "number"))

    def test_card_payload_rejects_pan_and_cvv(self):
        response = self.client.post("/api/cards/", self.card_payload(number="4111111111111111", cvv="123"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Card.objects.count(), 0)

    def test_card_list_is_owner_scoped_and_delete_works(self):
        card = Card.objects.create(user=self.user, **self.card_payload())
        other = User.objects.create_user(username="kim", email="kim@example.com", password="Strong-Pass-987!")
        Card.objects.create(user=other, **self.card_payload(provider_payment_method_id="pm_other"))
        listing = self.client.get("/api/cards/")
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(self.client.delete(f"/api/cards/{card.id}/").status_code, 204)


class PaymentTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ria", email="ria@example.com", password="Strong-Pass-987!")
        self.card = Card.objects.create(
            user=self.user, provider_payment_method_id="pm_payment_test", brand="Mastercard",
            last4="4444", card_type="DEBIT", expiry_month=5, expiry_year=2031,
        )
        self.client = TestClient(app)
        self.headers = {"Authorization": f"Bearer {AccessToken.for_user(self.user)}"}

    def test_payment_succeeds_and_is_saved_to_history(self):
        response = self.client.post("/payments", headers=self.headers, json={
            "card_id": str(self.card.id), "amount": "25.50", "currency": "usd",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], Transaction.Status.SUCCESS)
        self.assertEqual(Transaction.objects.get().amount, Decimal("25.50"))

    def test_simulator_failure_is_recorded(self):
        response = self.client.post("/payments", headers=self.headers, json={
            "card_id": str(self.card.id), "amount": "10001.00",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], Transaction.Status.FAILED)

    def test_payment_rejects_unknown_card_and_missing_token(self):
        missing_card = self.client.post("/payments", headers=self.headers, json={
            "card_id": "00000000-0000-0000-0000-000000000001", "amount": "10.00",
        })
        unauthorized = self.client.post("/payments", json={"card_id": str(self.card.id), "amount": "10.00"})
        self.assertEqual(missing_card.status_code, 404)
        self.assertEqual(unauthorized.status_code, 401)


class AdminApiTests(TestCase):
    def test_admin_export_records_audit_event(self):
        staff = User.objects.create_user(
            username="admin", email="admin@example.com", password="Strong-Pass-987!", is_staff=True,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(staff)}")
        response = client.get("/api/admin/transactions/export/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertEqual(AdminLog.objects.get().action, "TRANSACTIONS_EXPORTED")