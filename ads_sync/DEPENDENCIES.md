# Project Dependencies

This document lists the main dependencies required by the codebase in this module. It includes both Python packages and Odoo-specific modules.

## Python Package Dependencies

- odoo (Odoo ERP framework)
- requests
- json (standard library)
- logging (standard library)
- time (standard library)
- hashlib (standard library)
- secrets (standard library)
- string (standard library)

## Odoo Modules
- base (required by all Odoo modules)
- Any other Odoo modules required by your business logic (check __manifest__.py for details)

## Additional Notes
- All standard library modules are available by default in Python 3.x.
- The `requests` package must be installed in the Python environment used by Odoo.
- Odoo dependencies are managed via the Odoo server and the manifest file.

For a full list of dependencies, see the `__manifest__.py` file and review any external service requirements in the codebase.

---

## API Endpoints

Below is a summary of the main API endpoints provided by the Meta Odoo Middleware project. Each endpoint is implemented in the `app/api/` directory.

### `/subscribe` (Subscription Management)
- **POST `/subscribe`**  
  Create a new webhook subscription.  
  Requires platform credentials and returns an API key and webhook verification token.

- **GET `/subscribe`**  
  List all registered subscriptions (API key authentication required).

- **DELETE `/subscribe/{subscription_id}`**  
  Deactivate a subscription by its ID (API key authentication required).

### `/webhooks` (Webhook Receiver)
- **POST `/webhooks/meta`**  
  Receives and processes Meta (Facebook/Instagram) webhook events.

- **POST `/webhooks/google_ads`**  
  Receives and processes Google Ads webhook events (future support).

- **POST `/webhooks/tiktok_ads`**  
  Receives and processes TikTok Ads webhook events (future support).

### `/meta` (Meta/Facebook API Proxy)
- **POST `/meta/forward`**  
  Forwards events or data to the Meta Conversions API on behalf of a subscription.

### `/events` (Event Management)
- **GET `/events`**  
  List or query processed events (API key authentication required).

### `/health` (Health Check)
- **GET `/health`**  
  Returns the health status of the API service.