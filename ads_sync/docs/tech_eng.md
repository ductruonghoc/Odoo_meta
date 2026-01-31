# Ads Sync - Technical Documentation

## Overview

**Ads Sync** is an Odoo module designed to seamlessly integrate Odoo ERP with Meta (Facebook) Conversion API (CAPI) for enhanced advertising optimization. This module facilitates bidirectional data synchronization between Odoo and Meta's advertising platform, enabling businesses to:

1. **Receive and process webhook events** from Meta, routing them to appropriate Odoo models for automated processing.
2. **Push conversion events** to Meta CAPI in real-time when predefined actions occur within Odoo.
3. **Configure event triggers** through an intuitive user interface with toggle switches for granular control.

The module supports a wide range of Meta events, including lead generation, sales conversions, user engagements, and custom events, ensuring comprehensive tracking and optimization of marketing campaigns.

---

## Architecture

The Ads Sync module follows a modular architecture that integrates deeply with Odoo's ORM and controller framework:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              ODOO                                        │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐  │
│  │  Model Triggers │───▶│ meta.event.config │───▶│  External Server   │  │
│  │  (crm.lead,     │    │  (Check if active)│    │  /meta/events/push │  │
│  │   sale.order,   │    └──────────────────┘    └────────────────────┘  │
│  │   res.partner)  │                                      │             │
│  └─────────────────┘                                      ▼             │
│                                                    ┌─────────────┐      │
│  ┌─────────────────┐    ┌──────────────────┐      │  Meta CAPI  │      │
│  │ /webhooks/meta  │◀───│ ads.meta.webhook │      │  (Facebook) │      │
│  │  (Controller)   │    │     .event       │      └─────────────┘      │
│  └─────────────────┘    └──────────────────┘                           │
│          │                                                              │
│          ▼                                                              │
│  ┌─────────────────────────────────────────┐                           │
│  │  Route to Models (crm.lead, sale.order) │                           │
│  │  Based on event field type              │                           │
│  └─────────────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

- **Model Triggers**: Extensions to core Odoo models that detect state changes and trigger events.
- **Event Configuration**: Central configuration model managing event definitions and activation states.
- **Webhook Controller**: Handles incoming Meta webhooks with signature verification and payload processing.
- **External Server Integration**: Secure API communication with an external service for Meta CAPI interactions.
- **Event Storage**: Persistent logging of all webhook events and push operations for auditing.

---

## Module Dependencies

The module requires the following Odoo modules:

```python
'depends': ['base', 'web', 'mail', 'crm', 'sale', 'account', 'calendar', 'mass_mailing']
```

### Additional Requirements

- Python 3.8+
- Odoo 16.0+
- External server with Meta CAPI proxy (recommended for security)
- Valid Meta Business API credentials

---

## Models

### 1. `meta.event.config` - Event Configuration

**Purpose**: Manages Meta CAPI event definitions, configurations, and activation states with comprehensive tracking.

**Key Fields**:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `name` | Char | Human-readable event name (e.g., "Purchase", "Lead") | ✓ |
| `technical_name` | Char | Internal identifier used by triggers | ✓ |
| `category` | Selection | Event category (lead, sales, engagement, registration, ecommerce) | ✓ |
| `is_active` | Boolean | Toggle to enable/disable automatic event pushing | ✓ |
| `trigger_model` | Char | Odoo model that triggers this event | ✓ |
| `trigger_action` | Char | Method name that triggers this event | ✓ |
| `include_user_data` | Boolean | Include SHA256-hashed PII in payload | ✗ |
| `include_custom_data` | Boolean | Include custom business data in payload | ✗ |
| `test_mode` | Boolean | Use test_event_code for Meta debugging | ✗ |
| `push_count` | Integer | Statistics: total successful pushes | ✗ |
| `last_push_date` | Datetime | Statistics: timestamp of last successful push | ✗ |
| `error_count` | Integer | Statistics: total failed pushes | ✗ |
| `last_error_date` | Datetime | Statistics: timestamp of last error | ✗ |
| `last_error_message` | Text | Statistics: last error details | ✗ |

**Key Methods**:

```python
@api.model
def trigger_event(self, technical_name, record, extra_data=None):
    """
    Main entry point for triggering Meta events.
    Performs validation, builds payload, and initiates push.

    :param technical_name: str - Event identifier (e.g., 'purchase', 'lead')
    :param record: recordset - The Odoo record that triggered the event
    :param extra_data: dict - Additional data to merge into payload
    :return: dict - Result with 'success', 'response', 'error' keys
    :raises: ValidationError for invalid configurations
    """
    config = self.search([('technical_name', '=', technical_name), ('is_active', '=', True)])
    if not config:
        return {'success': False, 'error': 'Event not configured or inactive'}

    payload = config._build_payload_from_record(record, extra_data)
    return config._push_event_to_meta(payload)

def _push_event_to_meta(self, payload, pixel_id=None, access_token=None):
    """
    Securely push event payload to Meta CAPI via external server proxy.

    :param payload: dict - Meta CAPI compliant payload
    :param pixel_id: str - Override default pixel ID
    :param access_token: str - Override default access token
    :return: dict - API response from external server
    """
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': self.env['ir.config_parameter'].sudo().get_param('ads_sync.api_key'),
        'Authorization': f'Bearer {access_token or self._get_access_token()}'
    }

    url = f"{self._get_server_url()}/meta/events/push"
    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code == 200:
        self._update_push_stats(success=True)
        return {'success': True, 'response': response.json()}
    else:
        self._update_push_stats(success=False, error=response.text)
        return {'success': False, 'error': response.text}

def _build_payload_from_record(self, record, extra_data=None):
    """
    Construct Meta CAPI compliant payload from Odoo record data.

    :param record: recordset - Source Odoo record
    :param extra_data: dict - Additional custom data
    :return: dict - Complete Meta event payload
    """
    payload = {
        'event_name': self.name,
        'event_time': int(time.time()),
        'event_id': f"{self.technical_name}_{record._name}_{record.id}_{int(time.time())}",
        'action_source': 'system_generated'
    }

    if self.include_user_data:
        payload['user_data'] = self._extract_user_data(record)

    if self.include_custom_data:
        payload['custom_data'] = self._extract_custom_data(record, extra_data)

    return {'data': [payload]}

def _extract_user_data(self, record):
    """
    Extract and hash PII according to Meta CAPI requirements.

    :param record: recordset - Source record
    :return: dict - Hashed user data
    """
    user_data = {}

    # Email hashing
    if hasattr(record, 'email') and record.email:
        user_data['em'] = [hashlib.sha256(record.email.lower().strip().encode()).hexdigest()]

    # Phone hashing (digits only)
    if hasattr(record, 'phone') and record.phone:
        phone_digits = re.sub(r'\D', '', record.phone)
        user_data['ph'] = [hashlib.sha256(phone_digits.encode()).hexdigest()]

    # Name hashing
    if hasattr(record, 'name') and record.name:
        names = record.name.split()
        if names:
            user_data['fn'] = [hashlib.sha256(names[0].lower().encode()).hexdigest()]
        if len(names) > 1:
            user_data['ln'] = [hashlib.sha256(names[-1].lower().encode()).hexdigest()]

    return user_data
```

### 2. `ads.meta.webhook.event` - Webhook Event Storage

**Purpose**: Provides persistent storage and processing state tracking for incoming Meta webhook events.

**Key Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | Char | Meta webhook event type |
| `object_type` | Char | Meta object type (page, user, etc.) |
| `entry_id` | Char | Meta entry identifier |
| `payload_json` | Text | Complete raw JSON payload |
| `source_ip` | Char | Originating IP address for security logging |
| `state` | Selection | Processing state (received, processing, processed, error, ignored) |
| `processed_at` | Datetime | Timestamp when event was processed |
| `error_message` | Text | Error details if processing failed |
| `retry_count` | Integer | Number of processing retries attempted |

**Key Methods**:

```python
@api.model
def create_from_webhook(self, payload, source_ip=None, subscription=None):
    """
    Factory method for creating webhook event records from Meta payloads.

    :param payload: dict - Parsed JSON webhook payload
    :param source_ip: str - Source IP for security tracking
    :param subscription: recordset - Associated subscription record
    :return: recordset - Created webhook event record
    """
    return self.create({
        'event_type': payload.get('object'),
        'object_type': payload.get('entry', [{}])[0].get('changes', [{}])[0].get('field'),
        'entry_id': payload.get('entry', [{}])[0].get('id'),
        'payload_json': json.dumps(payload),
        'source_ip': source_ip,
        'state': 'received'
    })

def process_webhook_event(self):
    """
    Process a received webhook event and route to appropriate models.

    :return: bool - True if processing successful
    """
    try:
        payload = json.loads(self.payload_json)
        routing_result = self._route_to_models(payload)
        self.write({
            'state': 'processed' if routing_result else 'ignored',
            'processed_at': fields.Datetime.now()
        })
        return True
    except Exception as e:
        self.write({
            'state': 'error',
            'error_message': str(e),
            'retry_count': self.retry_count + 1
        })
        return False
```

### 3. `ads.meta.event.push` - Manual Event Push Interface

**Purpose**: Provides a user interface for manually creating and pushing custom events to Meta CAPI.

**Features**:
- Pre-built templates for standard Meta events
- JSON payload editor with schema validation
- Real-time response tracking and error logging
- Batch event pushing capabilities

### 4. `ads.subscription` - Subscription Management

**Purpose**: Securely stores Meta API credentials and manages subscription configurations.

**Key Fields**:
- `name`: Char - Subscription identifier
- `meta_pixel_id`: Char - Facebook Pixel ID (encrypted)
- `meta_access_token`: Char - CAPI Access Token (encrypted)
- `meta_app_secret`: Char - App Secret for webhook verification (encrypted)
- `api_key`: Char - External server API key (encrypted)
- `webhook_verify_token`: Char - Token for webhook URL verification
- `is_active`: Boolean - Subscription activation status

---

## Model Extensions (Event Triggers)

Located in `models/meta_event_triggers.py`, these extensions hook into core Odoo model methods to automatically trigger Meta events.

### Trigger Mapping

| Model | Method | Event Technical Name | Meta Event | Description |
|-------|--------|---------------------|------------|-------------|
| `crm.lead` | `create` | `lead` | Lead | New lead creation |
| `crm.lead` | `convert_opportunity` | `qualified_lead` | QualifiedLead | Lead qualification |
| `crm.lead` | `action_set_won_rainbowman` | `converted_lead` | ConvertedLead | Lead conversion to won |
| `sale.order` | `action_confirm` | `purchase` | Purchase | Order confirmation |
| `sale.order` | `action_quotation_sent` | `initiate_checkout` | InitiateCheckout | Quotation sent |
| `account.move` | `action_post` | `add_payment_info` | AddPaymentInfo | Invoice posting |
| `res.partner` | `create` | `contact` | Contact | New contact creation |
| `res.users` | `create` | `complete_registration` | CompleteRegistration | User registration |
| `calendar.event` | `create` | `schedule` | Schedule | Calendar event creation |
| `mailing.contact` | `create` | `subscribe` | Subscribe | Mailing list subscription |

### Trigger Implementation Pattern

```python
class CrmLeadMetaEvents(models.Model):
    _inherit = 'crm.lead'

    def action_set_won_rainbowman(self):
        """Override to trigger Meta event on lead conversion."""
        res = super().action_set_won_rainbowman()

        for record in self:
            try:
                self.env['meta.event.config'].sudo().trigger_event(
                    'converted_lead',
                    record,
                    extra_data={'conversion_value': record.expected_revenue}
                )
            except Exception as e:
                _logger.exception(f"Meta event trigger failed for lead {record.id}: {e}")
                # Continue execution - don't fail the business logic

        return res
```

---

## Controllers

### Webhook Endpoints (`controllers/main.py`)

#### `GET /webhooks/meta` - Webhook Verification

Meta's webhook setup process requires URL verification.

**Request Parameters**:
- `hub.mode`: Must be 'subscribe'
- `hub.verify_token`: Must match configured `webhook_verify_token`
- `hub.challenge`: Random string to echo back

**Response**: HTTP 200 with challenge string as plain text

**Implementation**:
```python
@http.route('/webhooks/meta', type='http', auth='public', methods=['GET'], csrf=False)
def verify_webhook(self, **kwargs):
    mode = kwargs.get('hub.mode')
    token = kwargs.get('hub.verify_token')
    challenge = kwargs.get('hub.challenge')

    configured_token = self.env['ir.config_parameter'].sudo().get_param('ads_sync.meta_webhook_verify_token')

    if mode == 'subscribe' and token == configured_token:
        return challenge
    else:
        raise werkzeug.exceptions.BadRequest('Verification failed')
```

#### `POST /webhooks/meta` - Receive Webhook Events

Processes incoming Meta webhook payloads with signature verification.

**Security Features**:
- SHA256 signature verification using app secret
- IP whitelist validation
- Payload size limits
- Rate limiting protection

**Process Flow**:
1. Verify request signature
2. Parse and validate JSON payload
3. Create `ads.meta.webhook.event` record
4. Queue event for asynchronous processing
5. Return HTTP 200 (always, per Meta requirements)

**Event Routing Logic**:
```python
def _route_webhook_event(self, payload):
    """Route webhook events to appropriate Odoo models based on field type."""
    routing_map = {
        'affiliation': 'crm.lead',      # Business partnerships
        'attire': 'sale.order',         # Product preferences
        'awards': 'crm.lead',           # Customer achievements
        'bio': 'res.partner',           # User biographies
        'birthday': 'res.partner',      # Birth dates
        'education': 'res.partner',     # Education history
        'email': 'res.partner',         # Email updates
        'favorite_athletes': 'crm.lead', # Interests
        'favorite_teams': 'crm.lead',   # Interests
        'first_name': 'res.partner',    # Name changes
        'gender': 'res.partner',        # Gender updates
        'hometown': 'res.partner',      # Location data
        'interested_in': 'crm.lead',    # Interests
        'languages': 'res.partner',     # Language preferences
        'last_name': 'res.partner',     # Name changes
        'link': 'res.partner',          # Profile links
        'location': 'res.partner',      # Current location
        'meeting_for': 'crm.lead',      # Meeting purposes
        'middle_name': 'res.partner',   # Name changes
        'name': 'res.partner',          # Name updates
        'political': 'crm.lead',        # Political views
        'quotes': 'crm.lead',           # User quotes
        'relationship_status': 'res.partner', # Relationship status
        'religion': 'crm.lead',         # Religious views
        'sports': 'crm.lead',           # Sports interests
        'website': 'res.partner',       # Website updates
        'work': 'res.partner'           # Employment updates
    }

    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            field = change.get('field')
            if field in routing_map:
                model = routing_map[field]
                self._create_or_update_record(model, change.get('value'))
```

---

## API Specifications

### External Server API

The module communicates with an external server for Meta CAPI interactions to maintain security separation.

#### POST /meta/events/push

**Purpose**: Push events to Meta CAPI

**Headers**:
```
Content-Type: application/json
X-API-Key: <api_key>
Authorization: Bearer <access_token>
```

**Request Body**:
```json
{
  "data": [{
    "event_name": "Purchase",
    "event_time": 1737561600,
    "event_id": "purchase_sale_order_123_1737561600",
    "action_source": "system_generated",
    "user_data": {
      "em": ["sha256_hash_of_email"],
      "ph": ["sha256_hash_of_phone"],
      "fn": ["sha256_hash_of_firstname"],
      "ln": ["sha256_hash_of_lastname"],
      "client_ip_address": "192.168.1.1",
      "client_user_agent": "Mozilla/5.0..."
    },
    "custom_data": {
      "currency": "USD",
      "value": 150.00,
      "content_name": "Sale Order SO001",
      "content_ids": ["SO001"],
      "order_id": "SO001",
      "num_items": 3,
      "contents": [
        {
          "id": "PROD001",
          "quantity": 2,
          "item_price": 50.00
        }
      ]
    }
  }],
  "pixel_id": "123456789",
  "test_event_code": "TEST123"  // Only in test mode
}
```

**Response**:
```json
{
  "success": true,
  "events_received": 1,
  "messages": [],
  "fbtrace_id": "AbCdEfGhIjKlMnOpQrStUvWxYz"
}
```

### Meta Webhook Payload Format

**Standard Webhook Payload**:
```json
{
  "object": "page",
  "entry": [{
    "id": "123456789",
    "time": 1737561600,
    "changes": [{
      "field": "email",
      "value": {
        "email": "user@example.com",
        "id": "987654321"
      }
    }]
  }]
}
```

---

## Security Considerations

### Data Protection

1. **PII Hashing**: All personally identifiable information is SHA256 hashed before transmission to Meta, complying with privacy regulations.

2. **Encryption at Rest**: Sensitive credentials (access tokens, app secrets) are encrypted using Odoo's built-in encryption mechanisms.

3. **Access Control**: Granular permissions ensure only authorized users can configure events and view sensitive data.

### Network Security

1. **Webhook Verification**: SHA256 signature verification prevents unauthorized webhook submissions.

2. **IP Whitelisting**: Optional IP address validation for incoming webhooks.

3. **Rate Limiting**: Built-in protection against webhook spam and abuse.

4. **HTTPS Only**: All external communications use HTTPS with certificate validation.

### Access Control Matrix

| Model | Group | Read | Write | Create | Delete |
|-------|-------|------|-------|--------|--------|
| `meta.event.config` | ads_sync.user | ✓ | ✓ | ✓ | ✗ |
| `meta.event.config` | ads_sync.admin | ✓ | ✓ | ✓ | ✓ |
| `ads.meta.webhook.event` | ads_sync.user | ✓ | ✗ | ✗ | ✗ |
| `ads.meta.webhook.event` | ads_sync.admin | ✓ | ✓ | ✓ | ✓ |
| `ads.subscription` | ads_sync.admin | ✓ | ✓ | ✓ | ✓ |

### Security Best Practices

- Regularly rotate Meta API credentials
- Monitor webhook event logs for anomalies
- Use test mode for development and staging
- Implement proper firewall rules for webhook endpoints
- Enable audit logging for all configuration changes

---

## Configuration

### System Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `ads_sync.server_url` | External server base URL | - | ✓ |
| `ads_sync.meta_webhook_verify_token` | Webhook verification token | - | ✓ |
| `ads_sync.api_key` | External server API key | - | ✓ |
| `meta.pixel_id` | Default Facebook Pixel ID | - | ✓ |
| `meta.test_event_code` | Test event code for debugging | - | ✗ |
| `ads_sync.webhook_ip_whitelist` | Comma-separated allowed IPs | - | ✗ |
| `ads_sync.rate_limit_per_minute` | Webhook rate limit | 60 | ✗ |

### Event Configuration Data

Pre-configured events loaded from `data/meta_event_config_data.xml`:

```xml
<record id="meta_event_purchase" model="meta.event.config">
    <field name="name">Purchase</field>
    <field name="technical_name">purchase</field>
    <field name="category">sales</field>
    <field name="trigger_model">sale.order</field>
    <field name="trigger_action">action_confirm</field>
    <field name="is_active">False</field>
    <field name="include_user_data">True</field>
    <field name="include_custom_data">True</field>
</record>
```

---

## Deployment

### Prerequisites

1. **Odoo Installation**: Version 16.0 or higher with required modules
2. **External Server**: Deploy the companion API server for Meta CAPI communication
3. **Meta Business Account**: Valid Facebook Business API credentials
4. **SSL Certificate**: HTTPS configuration for webhook endpoints

### Installation Steps

```bash
# 1. Install module dependencies
./odoo-bin -d your_database -i crm,sale,account,calendar,mass_mailing

# 2. Install ads_sync module
./odoo-bin -d your_database -i ads_sync

# 3. Configure system parameters
# Set ads_sync.server_url, ads_sync.meta_webhook_verify_token, etc.

# 4. Deploy external server
# Follow external server documentation for deployment

# 5. Configure Meta webhook
# Use https://your-odoo-domain/webhooks/meta as webhook URL
```

### Production Considerations

- **Load Balancing**: Ensure webhook endpoints are accessible through load balancers
- **Database Optimization**: Monitor database performance with high event volumes
- **Backup Strategy**: Regular backups of configuration and event logs
- **Monitoring**: Implement comprehensive monitoring (see Monitoring section)

### Upgrade Procedure

```bash
# 1. Backup database
pg_dump your_database > backup.sql

# 2. Stop Odoo service
sudo systemctl stop odoo

# 3. Update module code
git pull origin main

# 4. Upgrade module
./odoo-bin -d your_database -u ads_sync

# 5. Restart service
sudo systemctl start odoo

# 6. Verify functionality
# Check event logs and test event pushing
```

---

## Monitoring

### Key Metrics to Monitor

1. **Event Push Success Rate**: Percentage of successful Meta CAPI pushes
2. **Webhook Processing Time**: Average time to process incoming webhooks
3. **Error Rates**: Failed pushes and webhook processing errors
4. **Queue Depth**: Number of unprocessed webhook events

### Logging Configuration

Enable detailed logging in `odoo.conf`:

```ini
log_level = INFO
loggers = odoo.addons.ads_sync:DEBUG
```

### Monitoring Dashboard

Create custom dashboard views to track:

- Daily event push volumes by type
- Error trends and patterns
- Webhook event processing states
- Performance metrics (response times)

### Alert Configuration

Set up alerts for:
- Event push failure rate > 5%
- Webhook processing errors > 10
- Queue depth > 100 unprocessed events
- External server connectivity issues

### Health Checks

Implement health check endpoints:

```python
@http.route('/health/ads_sync', type='http', auth='public', methods=['GET'])
def health_check(self):
    """Health check endpoint for monitoring systems."""
    try:
        # Check database connectivity
        self.env['meta.event.config'].search_count([])

        # Check external server connectivity
        # ... implementation ...

        return {'status': 'healthy', 'timestamp': fields.Datetime.now()}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}
```

---

## Advanced Configurations

### Custom Event Types

To add new event types:

1. **Define Event Configuration**:
```xml
<record id="meta_event_custom" model="meta.event.config">
    <field name="name">Custom Event</field>
    <field name="technical_name">custom_event</field>
    <field name="category">custom</field>
    <field name="trigger_model">your.custom.model</field>
    <field name="trigger_action">custom_action</field>
    <field name="is_active">False</field>
</record>
```

2. **Implement Trigger Logic**:
```python
class CustomModelMetaEvents(models.Model):
    _inherit = 'your.custom.model'

    def custom_action(self):
        res = super().custom_action()
        for record in self:
            self.env['meta.event.config'].sudo().trigger_event(
                'custom_event',
                record,
                extra_data=self._prepare_custom_data(record)
            )
        return res

    def _prepare_custom_data(self, record):
        """Prepare custom data for Meta event."""
        return {
            'custom_field': record.custom_field,
            'calculated_value': self._calculate_value(record)
        }
```

### Conditional Event Triggering

Implement conditional logic for selective event pushing:

```python
def trigger_event(self, technical_name, record, extra_data=None):
    config = self.search([('technical_name', '=', technical_name), ('is_active', '=', True)])
    if not config:
        return {'success': False, 'error': 'Event not configured'}

    # Custom condition checking
    if not self._should_trigger_event(config, record):
        return {'success': False, 'error': 'Conditions not met'}

    payload = config._build_payload_from_record(record, extra_data)
    return config._push_event_to_meta(payload)

def _should_trigger_event(self, config, record):
    """Custom logic to determine if event should be triggered."""
    if config.technical_name == 'purchase':
        return record.amount_total > 100  # Only for orders over $100
    return True
```

### Batch Event Processing

For high-volume scenarios, implement batch processing:

```python
def batch_push_events(self, events):
    """Push multiple events in a single API call."""
    batch_payload = {'data': []}

    for event in events:
        payload = self._build_payload_from_record(event['record'], event.get('extra_data'))
        batch_payload['data'].extend(payload['data'])

    return self._push_event_to_meta(batch_payload)
```

### Integration with External Systems

Extend for integration with other marketing platforms:

```python
def push_to_multiple_platforms(self, event_name, record):
    """Push events to multiple advertising platforms."""
    results = {}

    # Meta CAPI
    results['meta'] = self.trigger_event(event_name, record)

    # Google Ads (if configured)
    if self._google_ads_enabled():
        results['google'] = self._push_to_google_ads(event_name, record)

    # Other platforms...
    return results
```

---

## Debugging and Troubleshooting

### Common Issues

1. **Webhook Verification Failed**
   - Check `ads_sync.meta_webhook_verify_token` parameter
   - Ensure webhook URL is HTTPS
   - Verify Meta app configuration

2. **Event Push Failures**
   - Validate Meta API credentials
   - Check external server connectivity
   - Review payload format compliance

3. **Performance Issues**
   - Monitor database query performance
   - Check for blocking operations in triggers
   - Implement asynchronous processing for high volumes

### Debug Logging

Enable comprehensive logging:

```python
_logger = logging.getLogger(__name__)

def trigger_event(self, technical_name, record, extra_data=None):
    _logger.debug(f"Triggering event {technical_name} for record {record._name}:{record.id}")
    # ... implementation with detailed logging ...
```

### Test Mode Configuration

For development and testing:

1. Enable test mode in event configurations
2. Set `meta.test_event_code` parameter
3. Use Meta Events Manager to validate test events
4. Monitor test event delivery in Meta dashboard

---

## Extending the Module

### Adding New Trigger Models

1. **Create Model Extension**:
```python
class YourModelMetaEvents(models.Model):
    _inherit = 'your.model'

    def your_trigger_method(self):
        res = super().your_trigger_method()
        self.env['meta.event.config'].sudo().trigger_event(
            'your_event', self, extra_data={'custom': 'data'}
        )
        return res
```

2. **Update Event Configuration**:
Add new records to `data/meta_event_config_data.xml`

3. **Update Routing Logic**:
Modify webhook routing in controllers if needed

### Custom Payload Builders

Override payload building for specific requirements:

```python
def _build_payload_from_record(self, record, extra_data=None):
    """Custom payload building logic."""
    payload = super()._build_payload_from_record(record, extra_data)

    # Add custom fields
    if hasattr(record, 'custom_field'):
        payload['data'][0]['custom_data']['custom_metric'] = record.custom_field

    return payload
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-22 | Initial release with 10 pre-configured events |
| 1.0.1 | 2026-01-28 | Enhanced documentation, added deployment and monitoring sections, improved security features, advanced configuration options |

---

*Last updated: January 28, 2026*
