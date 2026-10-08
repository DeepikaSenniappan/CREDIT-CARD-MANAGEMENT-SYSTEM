# Credit Card Payment System Backend

A Django REST Framework API for identity, saved-card metadata, transaction history, and staff operations, paired with a FastAPI payment endpoint. Both services share Django models and the configured database.

> The payment gateway in this repository is a deterministic simulator, not a real processor. Before handling real payments, replace it with a PCI DSS-compliant provider and use provider-hosted tokenization. Do not send or store a PAN or CVV in this application.

## Requirements

- Python 3.11+
- Docker Desktop (for MySQL), or use the default local SQLite database for development

## Setup on Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For a quick SQLite run, keep `DB_ENGINE=sqlite` in `.env`. For MySQL, start the database:

```powershell
docker compose up -d db
```

Set `DB_ENGINE=mysql` in `.env`; the remaining default DB values match `docker-compose.yml`. Apply migrations and create a staff account:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Run the services in separate terminals:

```powershell
python manage.py runserver 127.0.0.1:8000
```

```powershell
uvicorn fastapi_app.main:app --reload --host 127.0.0.1 --port 8001
```

The default development configuration uses SQLite. A deployment must use a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, restricted `DJANGO_ALLOWED_HOSTS`, TLS, managed secrets, backups, monitoring, and a production payment provider.

## API Documentation

- Django OpenAPI schema: `http://127.0.0.1:8000/api/schema/`
- Django Swagger UI: `http://127.0.0.1:8000/api/docs/`
- FastAPI Swagger UI: `http://127.0.0.1:8001/docs`
- FastAPI ReDoc: `http://127.0.0.1:8001/redoc`
- Health check: `GET http://127.0.0.1:8001/health`
- Import `postman/Credit-Card-Payment-System.postman_collection.json` into Postman. Set `django_url`, `payment_url`, and `access_token` collection variables.

### Django endpoints

All paths below are prefixed with `/api`.

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register/` | Public | Register with username, email, password |
| POST | `/auth/login/` | Public | Obtain access and refresh JWTs; login field is email |
| POST | `/auth/refresh/` | Public | Rotate a refresh token |
| POST | `/auth/logout/` | Bearer | Blacklist the supplied refresh token |
| GET, POST | `/cards/` | Bearer | List or save a provider-tokenized card |
| DELETE | `/cards/{uuid}/` | Bearer | Delete an owned saved card |
| GET | `/transactions/` | Bearer | List own transactions |
| GET | `/admin/users/` | Staff | List users |
| GET, PATCH | `/admin/users/{id}/` | Staff | Read/update account status and staff access |
| GET | `/admin/cards/` | Staff | View card metadata |
| GET | `/admin/transactions/` | Staff | View transactions |
| GET | `/admin/transactions/export/` | Staff | Export transactions as CSV and record an admin log |
| GET | `/admin/summary/daily/?date=YYYY-MM-DD` | Staff | Daily counts and totals grouped by status |

Transaction filters: `status`, `start_date`, `end_date` (ISO 8601 datetime), `min_amount`, and `max_amount`.

Send authenticated requests with `Authorization: Bearer <access_token>`. Logout revokes the refresh token; already-issued access tokens remain valid until their short expiry.

### FastAPI payment endpoint

`POST http://127.0.0.1:8001/payments` accepts a JSON object with `card_id` (saved card UUID), positive `amount` (up to two decimal places), and optional three-letter `currency`. It requires the same Django-issued Bearer access token. Amounts over `PAYMENT_SIMULATOR_FAIL_ABOVE_AMOUNT` deterministically finish as `FAILED`; other amounts finish as `SUCCESS`. Transactions are initially created as `PENDING` and updated with the simulator result.

## Database Schema

| Table / model | Important fields and constraints |
| --- | --- |
| `banking_user` | Django `AbstractUser`; unique email; Django password hash; staff/active flags |
| `banking_card` | Owner, provider payment-method reference, brand, last four, type, expiry; unique provider reference per user; no PAN/CVV fields |
| `banking_transaction` | Owner, saved card, decimal amount, currency, `PENDING`/`SUCCESS`/`FAILED`, timestamps and failure reason; indexed by owner/date and status/date |
| `banking_adminlog` | Actor, action, target, timestamp, JSON details |

Schema changes are captured in `banking/migrations/`. ORM queries and serializers are used throughout; input is validated before persistence.

## Testing and Coverage

```powershell
python -m coverage run manage.py test
python -m coverage report --fail-under=50
```

Tests cover password hashing/JWT auth, card ownership and raw PAN/CVV rejection, payment success/failure and authorization, and admin CSV auditing. Coverage configuration excludes generated migrations.

## Production Notes

This is a complete educational/reference workflow, not a certification that a deployment is production-ready for real card data. The simulator is deliberately non-integrated. Store only a provider-issued payment-method reference and display metadata after provider tokenization. Review provider webhook signature verification, idempotency, retry/outbox behavior, rate limits, audit retention, key rotation, logging redaction, and operational controls before production use.