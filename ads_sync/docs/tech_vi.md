# Ads Sync - Tài Liệu Kỹ Thuật

**Ngày cập nhật:** 28 tháng 1, 2026  
**Phiên bản module:** 1.0.0  
**Tác giả:** Đội ngũ phát triển Odoo Meta Integration  

## Tổng Quan

**Ads Sync** là một module Odoo chuyên nghiệp được thiết kế để tích hợp liền mạch hệ thống ERP Odoo với Meta (Facebook) Conversion API (CAPI). Module này cho phép luồng dữ liệu hai chiều giữa Odoo và nền tảng quảng cáo Meta, giúp doanh nghiệp tối ưu hóa chiến lược quảng cáo kỹ thuật số thông qua việc:

1. **Nhận và xử lý webhook events** từ Meta để cập nhật dữ liệu Odoo theo thời gian thực
2. **Đẩy conversion events** tự động đến Meta CAPI khi có hành động kinh doanh quan trọng xảy ra trong Odoo
3. **Cấu hình linh hoạt event triggers** thông qua giao diện quản trị với các công tắc bật/tắt
4. **Đảm bảo tuân thủ bảo mật** với việc hash dữ liệu PII và xác thực webhook

Module được xây dựng theo kiến trúc microservices, sử dụng external server để xử lý các request đến Meta API, đảm bảo hiệu suất và độ tin cậy cao.

---

## Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                ODOO INSTANCE                                   │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐     │
│  │  Model Triggers │───▶│ meta.event.config │───▶│    External Server      │     │
│  │  (crm.lead,     │    │  (Validation &    │    │  /meta/events/push      │     │
│  │   sale.order,   │    │   Processing)     │    │  (REST API Gateway)    │     │
│  │   res.partner)  │    └──────────────────┘    └─────────────────────────┘     │
│  └─────────────────┘                                      │                      │
│                                                    ┌─────────────┐               │
│  ┌─────────────────┐    ┌──────────────────┐      │  Meta CAPI  │               │
│  │ /webhooks/meta  │◀───│ ads.meta.webhook │      │  (Facebook) │               │
│  │  (Webhook       │    │     .event       │      └─────────────┘               │
│  │   Controller)   │    │  (Event Storage  │                                      │
│  └─────────────────┘    └──────────────────┘                                      │
│          │                                                                       │
│          ▼                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐     │
│  │            Event Routing Engine                                        │     │
│  │  - Định tuyến dựa trên field type                                     │     │
│  │  - Mapping đến Models: crm.lead, sale.order, res.partner             │     │
│  │  - Validation và error handling                                       │     │
│  └─────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVER ARCHITECTURE                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Nginx     │───▶│   Flask     │───▶│  Rate      │───▶│   Meta     │     │
│  │  (Reverse   │    │   API       │    │  Limiter   │    │   API      │     │
│  │   Proxy)    │    │   Server    │    │            │    │   Client   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│          │                    │                    │                    │      │
│          ▼                    ▼                    ▼                    ▼      │
│     Load Balancing      Request Queue      Circuit Breaker      HTTP Client │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Thành Phần Chính

- **Odoo Module**: Xử lý logic nghiệp vụ, triggers, và giao diện quản trị
- **External Server**: API gateway để giao tiếp với Meta APIs, xử lý rate limiting và retry logic
- **Meta CAPI**: Endpoint của Facebook để nhận conversion events
- **Webhook System**: Nhận events từ Meta và cập nhật Odoo

### Luồng Dữ Liệu

1. **Outbound Flow (Odoo → Meta)**:
   - Trigger từ model changes
   - Validation qua meta.event.config
   - Payload construction và gửi đến external server
   - External server forward đến Meta CAPI

2. **Inbound Flow (Meta → Odoo)**:
   - Webhook nhận từ Meta
   - Validation và parsing payload
   - Routing đến appropriate models
   - Update/create records trong Odoo

---

## Phụ Thuộc Module

```python
'depends': [
    'base',        # Core Odoo functionality
    'web',         # Web interface components
    'mail',        # Email functionality
    'crm',         # Customer Relationship Management
    'sale',        # Sales orders and quotations
    'account',     # Accounting and invoicing
    'calendar',    # Calendar events
    'mass_mailing' # Email marketing campaigns
]
```

**Lý do phụ thuộc:**
- `crm`: Để trigger events từ leads và opportunities
- `sale`: Để track purchase events từ sales orders
- `account`: Để monitor payment events
- `calendar`: Để track scheduling events
- `mass_mailing`: Để handle subscription events

---

## Các Models

### 1. `meta.event.config` - Cấu Hình Event

**Mục đích**: Quản lý cấu hình cho các Meta CAPI events với khả năng bật/tắt động và theo dõi hiệu suất.

**Các Trường Chính**:

| Trường | Kiểu | Mô Tả | Bắt Buộc |
|--------|------|-------|----------|
| `name` | Char | Tên hiển thị của event (vd: "Purchase", "Lead") | ✓ |
| `technical_name` | Char | Định danh nội bộ cho triggers | ✓ |
| `category` | Selection | Danh mục event (lead, sales, engagement, registration, ecommerce) | ✓ |
| `is_active` | Boolean | Công tắc kích hoạt event | ✗ |
| `trigger_model` | Char | Model Odoo kích hoạt event | ✓ |
| `trigger_action` | Char | Method name kích hoạt event | ✓ |
| `include_user_data` | Boolean | Bao gồm PII đã hash trong payload | ✗ |
| `include_custom_data` | Boolean | Bao gồm custom data trong payload | ✗ |
| `test_mode` | Boolean | Sử dụng test_event_code cho debug | ✗ |
| `pixel_id` | Char | Facebook Pixel ID cụ thể (override global) | ✗ |
| `access_token` | Char | CAPI Access Token cụ thể (override global) | ✗ |
| `push_count` | Integer | Số lần đẩy thành công | ✗ |
| `last_push_date` | Datetime | Thời gian đẩy cuối cùng | ✗ |
| `error_count` | Integer | Số lần đẩy thất bại | ✗ |
| `last_error_message` | Text | Thông báo lỗi cuối cùng | ✗ |

**Các Methods Chính**:

```python
@api.model
def trigger_event(self, technical_name, record, extra_data=None):
    """
    Điểm vào chính để kích hoạt Meta events.
    
    Args:
        technical_name (str): Định danh event
        record (recordset): Record Odoo đã kích hoạt
        extra_data (dict): Dữ liệu bổ sung
    
    Returns:
        dict: {'success': bool, 'response': dict, 'error': str}
    
    Raises:
        ValidationError: Nếu event không active hoặc config không hợp lệ
    """
    config = self.search([('technical_name', '=', technical_name), ('is_active', '=', True)], limit=1)
    if not config:
        return {'success': False, 'error': f'Event {technical_name} không active'}
    
    try:
        payload = config._build_payload_from_record(record, extra_data)
        response = config._push_event_to_meta(payload)
        config._update_statistics(success=True)
        return {'success': True, 'response': response}
    except Exception as e:
        config._update_statistics(success=False, error=str(e))
        _logger.exception(f"Failed to push event {technical_name}: {e}")
        return {'success': False, 'error': str(e)}

def _push_event_to_meta(self, payload, pixel_id=None, access_token=None):
    """
    Đẩy event đến Meta CAPI qua external server.
    
    API Endpoint: POST {server_url}/meta/events/push
    Headers:
        Content-Type: application/json
        X-API-Key: {api_key}
        Authorization: Bearer {access_token}
    
    Args:
        payload (dict): Event payload theo định dạng Meta CAPI
        pixel_id (str): Facebook Pixel ID
        access_token (str): CAPI Access Token
    
    Returns:
        dict: Response từ Meta API
    """
    import requests
    
    server_url = self.env['ir.config_parameter'].sudo().get_param('ads_sync.server_url')
    api_key = self.env['ir.config_parameter'].sudo().get_param('ads_sync.api_key')
    
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key,
        'Authorization': f'Bearer {access_token or self.access_token}'
    }
    
    response = requests.post(
        f"{server_url}/meta/events/push",
        json=payload,
        headers=headers,
        timeout=30
    )
    
    response.raise_for_status()
    return response.json()

def _build_payload_from_record(self, record, extra_data=None):
    """
    Xây dựng payload Meta CAPI từ Odoo record.
    
    Args:
        record: Odoo record
        extra_data (dict): Dữ liệu bổ sung
    
    Returns:
        dict: Payload theo định dạng Meta CAPI v16.0
    """
    payload = {
        'data': [{
            'event_name': self.name,
            'event_time': int(record.create_date.timestamp()),
            'event_id': f"{self.technical_name}_{record._name}_{record.id}_{int(record.create_date.timestamp())}",
            'action_source': 'system_generated'
        }]
    }
    
    if self.include_user_data:
        payload['data'][0]['user_data'] = self._extract_user_data(record)
    
    if self.include_custom_data:
        payload['data'][0]['custom_data'] = self._extract_custom_data(record, extra_data)
    
    if self.test_mode:
        test_code = self.env['ir.config_parameter'].sudo().get_param('meta.test_event_code')
        if test_code:
            payload['data'][0]['test_event_code'] = test_code
    
    return payload

def _extract_user_data(self, record):
    """
    Trích xuất và hash PII theo tiêu chuẩn Meta.
    
    Supported fields:
    - em: email (SHA256 hash)
    - ph: phone (SHA256 hash)
    - fn: first name (SHA256 hash)
    - ln: last name (SHA256 hash)
    - ct: city
    - st: state
    - zp: zip code
    - country: country code
    """
    import hashlib
    
    user_data = {}
    
    # Email hashing
    if hasattr(record, 'email') and record.email:
        email = record.email.lower().strip()
        user_data['em'] = [hashlib.sha256(email.encode()).hexdigest()]
    
    # Phone hashing
    if hasattr(record, 'phone') and record.phone:
        phone = ''.join(filter(str.isdigit, record.phone))
        user_data['ph'] = [hashlib.sha256(phone.encode()).hexdigest()]
    
    # Name hashing
    if hasattr(record, 'name') and record.name:
        names = record.name.split()
        if names:
            user_data['fn'] = [hashlib.sha256(names[0].lower().encode()).hexdigest()]
        if len(names) > 1:
            user_data['ln'] = [hashlib.sha256(' '.join(names[1:]).lower().encode()).hexdigest()]
    
    return user_data
```

### 2. `ads.meta.webhook.event` - Lưu Trữ Webhook Event

**Mục đích**: Lưu trữ và theo dõi tất cả webhook events từ Meta để kiểm toán, debug và xử lý lại.

**Các Trường Chính**:

| Trường | Kiểu | Mô Tả |
|--------|------|-------|
| `event_type` | Char | Loại webhook event từ Meta |
| `object_type` | Char | Loại object Meta (page, user, pixel) |
| `entry_id` | Char | Meta entry ID |
| `payload_json` | Text | Raw JSON payload |
| `source_ip` | Char | IP nguồn của request |
| `user_agent` | Char | User agent của request |
| `state` | Selection | Trạng thái xử lý |
| `processing_time` | Float | Thời gian xử lý (giây) |
| `error_message` | Text | Thông báo lỗi nếu có |
| `retry_count` | Integer | Số lần retry |
| `subscription_id` | Many2one | Liên kết đến ads.subscription |

**Methods Chính**:

```python
@api.model
def create_from_webhook(self, payload, source_ip=None, subscription=None):
    """
    Factory method tạo webhook event từ payload Meta.
    
    Args:
        payload (dict): Webhook payload từ Meta
        source_ip (str): IP nguồn
        subscription: Subscription record
    
    Returns:
        ads.meta.webhook.event: Record mới tạo
    """
    import json
    
    # Parse payload structure
    object_type = payload.get('object')
    entries = payload.get('entry', [])
    
    events = []
    for entry in entries:
        entry_id = entry.get('id')
        time_received = entry.get('time')
        
        for change in entry.get('changes', []):
            event = self.create({
                'event_type': change.get('field'),
                'object_type': object_type,
                'entry_id': entry_id,
                'payload_json': json.dumps(change.get('value', {})),
                'source_ip': source_ip,
                'user_agent': request.httprequest.headers.get('User-Agent'),
                'state': 'received',
                'subscription_id': subscription.id if subscription else False
            })
            events.append(event)
    
    return events

def process_event(self):
    """
    Xử lý event và định tuyến đến models phù hợp.
    
    Returns:
        bool: True nếu xử lý thành công
    """
    try:
        import json
        payload = json.loads(self.payload_json)
        
        # Route based on event_type
        routing_map = {
            'affiliation': 'crm.lead',
            'attire': 'sale.order',
            'awards': 'crm.lead',
            # ... more mappings
        }
        
        target_model = routing_map.get(self.event_type)
        if target_model:
            self._route_to_model(target_model, payload)
        
        self.write({
            'state': 'processed',
            'processing_time': time.time() - self.create_date.timestamp()
        })
        return True
        
    except Exception as e:
        self.write({
            'state': 'error',
            'error_message': str(e)
        })
        return False
```

### 3. `ads.meta.event.push` - Đẩy Event Thủ Công

**Mục đích**: Giao diện UI để developers và admins có thể đẩy events thủ công cho testing và debugging.

**Tính năng nâng cao**:
- Template events với validation JSON schema
- Batch push cho multiple events
- Response viewer với syntax highlighting
- Error logging và retry mechanism

### 4. `ads.subscription` - Quản Lý Subscription

**Mục đích**: Lưu trữ thông tin xác thực và cấu hình cho Meta API integrations.

**Các Trường Chính**:
- `name`: Tên subscription
- `meta_pixel_id`: Facebook Pixel ID
- `meta_access_token`: CAPI Access Token (encrypted)
- `meta_app_secret`: App Secret cho webhook verification
- `api_key`: API key cho external server
- `webhook_verify_token`: Token xác thực webhook
- `is_active`: Trạng thái active
- `last_sync_date`: Thời gian sync cuối
- `error_count`: Số lỗi tích lũy

---

## Model Extensions (Triggers)

Nằm trong `models/meta_event_triggers.py`, các extensions sử dụng inheritance để thêm logic trigger vào models core.

### Bảng Ánh Xạ Trigger Chi Tiết

| Model | Method | Technical Name | Meta Event | Điều Kiện Trigger |
|-------|--------|----------------|------------|-------------------|
| `crm.lead` | `create` | `lead` | Lead | Luôn luôn |
| `crm.lead` | `convert_opportunity` | `qualified_lead` | QualifiedLead | Khi chuyển thành opportunity |
| `crm.lead` | `action_set_won_rainbowman` | `converted_lead` | ConvertedLead | Khi won deal |
| `sale.order` | `action_confirm` | `purchase` | Purchase | Khi confirm order |
| `sale.order` | `action_quotation_sent` | `initiate_checkout` | InitiateCheckout | Khi gửi quotation |
| `account.move` | `action_post` | `add_payment_info` | AddPaymentInfo | Khi post invoice |
| `res.partner` | `create` | `contact` | Contact | Luôn luôn |
| `res.users` | `create` | `complete_registration` | CompleteRegistration | Luôn luôn |
| `calendar.event` | `create` | `schedule` | Schedule | Luôn luôn |
| `mailing.contact` | `create` | `subscribe` | Subscribe | Luôn luôn |

### Mẫu Triển Khai Trigger với Error Handling

```python
class CrmLeadMetaEvents(models.Model):
    _inherit = 'crm.lead'

    def action_set_won_rainbowman(self):
        res = super().action_set_won_rainbowman()
        
        for record in self:
            try:
                # Check if event is configured and active
                config = self.env['meta.event.config'].sudo().search([
                    ('technical_name', '=', 'converted_lead'),
                    ('is_active', '=', True)
                ], limit=1)
                
                if config:
                    result = config.trigger_event(
                        'converted_lead',
                        record,
                        extra_data={
                            'outcome': 'won',
                            'deal_value': record.expected_revenue,
                            'probability': record.probability
                        }
                    )
                    
                    if not result['success']:
                        _logger.warning(f"Failed to push converted_lead event: {result['error']}")
                
            except Exception as e:
                _logger.exception(f"Error triggering converted_lead event for lead {record.id}: {e}")
                # Continue execution even if event push fails
        
        return res
```

---

## Controllers

### Webhook Endpoints (`controllers/main.py`)

#### `GET /webhooks/meta` - Xác Thực Webhook

**API Specification:**
- **Method:** GET
- **Purpose:** Webhook URL verification by Meta
- **Parameters:**
  - `hub.mode` (string, required): Must be 'subscribe'
  - `hub.verify_token` (string, required): Must match configured token
  - `hub.challenge` (string, required): Challenge string to return
- **Response:** Plain text challenge string
- **Status Codes:** 200 OK, 403 Forbidden

**Implementation:**
```python
@http.route('/webhooks/meta', type='http', auth='public', methods=['GET'], csrf=False)
def verify_webhook(self, **kwargs):
    mode = kwargs.get('hub.mode')
    token = kwargs.get('hub.verify_token')
    challenge = kwargs.get('hub.challenge')
    
    configured_token = request.env['ir.config_parameter'].sudo().get_param('ads_sync.meta_webhook_verify_token')
    
    if mode == 'subscribe' and token == configured_token:
        return challenge
    else:
        return werkzeug.exceptions.Forbidden()
```

#### `POST /webhooks/meta` - Nhận Webhook Events

**API Specification:**
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** X-Hub-Signature-256 header for payload verification
- **Rate Limiting:** 1000 requests/minute
- **Timeout:** 30 seconds

**Request Body Schema:**
```json
{
  "type": "object",
  "properties": {
    "object": {"type": "string", "enum": ["page", "user", "pixel"]},
    "entry": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "time": {"type": "integer"},
          "changes": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "field": {"type": "string"},
                "value": {"type": "object"}
              }
            }
          }
        }
      }
    }
  }
}
```

**Response Codes:**
- `200 OK`: Always returned to prevent Meta from disabling webhook
- `400 Bad Request`: Invalid payload format
- `401 Unauthorized`: Invalid signature
- `429 Too Many Requests`: Rate limit exceeded

**Processing Flow:**
```python
@http.route('/webhooks/meta', type='http', auth='public', methods=['POST'], csrf=False)
def receive_webhook(self, **kwargs):
    try:
        # Verify signature
        signature = request.httprequest.headers.get('X-Hub-Signature-256')
        if not self._verify_signature(request.httprequest.data, signature):
            return werkzeug.exceptions.Unauthorized()
        
        # Parse payload
        payload = json.loads(request.httprequest.data)
        
        # Create webhook event record
        events = request.env['ads.meta.webhook.event'].sudo().create_from_webhook(
            payload,
            source_ip=request.httprequest.remote_addr
        )
        
        # Process events asynchronously
        for event in events:
            request.env.cr.commit()  # Ensure record is saved
            event.with_delay().process_event()
        
        return werkzeug.Response('OK', status=200)
        
    except json.JSONDecodeError:
        return werkzeug.exceptions.BadRequest()
    except Exception as e:
        _logger.exception(f"Webhook processing error: {e}")
        return werkzeug.Response('Internal Error', status=500)
```

---

## Cấu Hình

### Tham Số Hệ Thống

| Tham Số | Mô Tả | Mặc Định | Bắt Buộc |
|---------|-------|----------|----------|
| `ads_sync.server_url` | URL của external server | - | ✓ |
| `ads_sync.api_key` | API key cho external server | - | ✓ |
| `ads_sync.meta_webhook_verify_token` | Token xác thực webhook | - | ✓ |
| `meta.pixel_id` | Facebook Pixel ID mặc định | - | ✓ |
| `meta.access_token` | CAPI Access Token mặc định | - | ✓ |
| `meta.test_event_code` | Mã test event cho debug | - | ✗ |
| `ads_sync.rate_limit` | Giới hạn rate (requests/minute) | 1000 | ✗ |
| `ads_sync.retry_attempts` | Số lần retry thất bại | 3 | ✗ |
| `ads_sync.webhook_timeout` | Timeout cho webhook processing | 30 | ✗ |

### Dữ Liệu Cấu Hình Event

**File:** `data/meta_event_config_data.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
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
        
        <!-- Additional events -->
        <record id="meta_event_lead" model="meta.event.config">
            <field name="name">Lead</field>
            <field name="technical_name">lead</field>
            <field name="category">lead</field>
            <field name="trigger_model">crm.lead</field>
            <field name="trigger_action">create</field>
            <field name="is_active">False</field>
        </record>
    </data>
</odoo>
```

---

## Định Dạng API Payload

### Payload Event Đi (Odoo → Meta CAPI)

**Meta CAPI v16.0 Specification:**

```json
{
  "data": [
    {
      "event_name": "Purchase",
      "event_time": 1737561600,
      "event_id": "purchase_sale_order_123_1737561600",
      "action_source": "system_generated",
      "event_source_url": "https://your-odoo-instance.com",
      "user_data": {
        "em": ["sha256_hash_of_email"],
        "ph": ["sha256_hash_of_phone"],
        "fn": ["sha256_hash_of_first_name"],
        "ln": ["sha256_hash_of_last_name"],
        "ct": ["city"],
        "st": ["state"],
        "zp": ["12345"],
        "country": ["us"]
      },
      "custom_data": {
        "currency": "USD",
        "value": 150.00,
        "content_name": "SO001",
        "content_ids": ["PROD001", "PROD002"],
        "order_id": "SO001",
        "num_items": 3,
        "contents": [
          {
            "id": "PROD001",
            "quantity": 2,
            "item_price": 50.00
          },
          {
            "id": "PROD002",
            "quantity": 1,
            "item_price": 50.00
          }
        ]
      },
      "test_event_code": "TEST12345"
    }
  ],
  "access_token": "your_access_token"
}
```

### Payload Webhook Đến (Meta → Odoo)

**Meta Webhooks v16.0 Specification:**

```json
{
  "object": "page",
  "entry": [
    {
      "id": "123456789",
      "time": 1737561600,
      "changes": [
        {
          "field": "affiliation",
          "value": {
            "name": "Partner Company",
            "email": "partner@example.com",
            "phone": "+1234567890",
            "website": "https://partner.com"
          }
        }
      ]
    }
  ]
}
```

---

## Bảo Mật

### Xác Thực và Ủy Quyền

1. **Webhook Signature Verification:**
   ```python
   def _verify_signature(self, payload, signature):
       import hmac
       import hashlib
       
       app_secret = self.env['ir.config_parameter'].sudo().get_param('meta.app_secret')
       expected_signature = hmac.new(
           app_secret.encode(),
           payload,
           hashlib.sha256
       ).hexdigest()
       
       return hmac.compare_digest(f"sha256={expected_signature}", signature)
   ```

2. **API Key Authentication:**
   - Sử dụng X-API-Key header cho external server communication
   - Keys được rotate định kỳ và lưu trữ encrypted

3. **Access Token Management:**
   - Tokens được mã hóa trong database
   - Automatic refresh mechanism cho long-lived tokens

### Bảo Vệ Dữ Liệu

1. **PII Hashing:** Tất cả PII được hash SHA256 trước khi gửi
2. **Data Minimization:** Chỉ gửi dữ liệu cần thiết
3. **Encryption:** Sensitive data encrypted at rest và in transit
4. **Audit Logging:** Tất cả access và modifications được log

### Rate Limiting và DDoS Protection

- **Application Level:** 1000 requests/minute per IP
- **Infrastructure Level:** Nginx rate limiting
- **Circuit Breaker:** Automatic failover khi Meta API down

---

## Triển Khai (Deployment)

### Môi Trường Production

#### 1. External Server Setup

```bash
# Clone repository
git clone https://github.com/your-org/ads-sync-external.git
cd ads-sync-external

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
export ADS_SYNC_API_KEY="your-secure-api-key"
export META_APP_SECRET="your-meta-app-secret"
export FLASK_ENV="production"

# Run with Gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
```

#### 2. Nginx Configuration

```nginx
upstream ads_sync_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://ads_sync_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=100 nodelay;
    }
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy strict-origin-when-cross-origin;
}
```

#### 3. Odoo Configuration

```python
# odoo.conf
[options]
addons_path = /path/to/addons
db_host = your-db-host
db_port = 5432
db_user = odoo
db_password = secure-password

# Ads Sync specific
ads_sync.server_url = https://api.your-domain.com
ads_sync.api_key = your-secure-api-key
ads_sync.meta_webhook_verify_token = your-webhook-token
```

### Container Deployment (Docker)

```dockerfile
# Dockerfile for External Server
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:app"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  ads-sync-api:
    build: .
    environment:
      - ADS_SYNC_API_KEY=${API_KEY}
      - META_APP_SECRET=${APP_SECRET}
    ports:
      - "8000:8000"
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - ads-sync-api
```

### Monitoring và Alerting

#### Health Checks

```python
@app.route('/health')
def health_check():
    # Check database connectivity
    try:
        db.session.execute(text('SELECT 1'))
    except:
        return jsonify({'status': 'unhealthy'}), 500
    
    # Check Meta API connectivity
    try:
        response = requests.get('https://graph.facebook.com/v16.0/me', 
                              params={'access_token': access_token},
                              timeout=5)
        response.raise_for_status()
    except:
        return jsonify({'status': 'degraded'}), 200
    
    return jsonify({'status': 'healthy'})
```

---

## Giám Sát (Monitoring)

### Metrics Thu Thập

1. **Application Metrics:**
   - Request count và latency
   - Error rates theo endpoint
   - Event push success/failure rates
   - Webhook processing times

2. **Business Metrics:**
   - Events pushed per day/week
   - Conversion attribution
   - ROI tracking

3. **System Metrics:**
   - CPU/Memory usage
   - Database connection pools
   - External API response times

### Logging Strategy

```python
import logging
import json_log_formatter

# Structured logging configuration
formatter = json_log_formatter.JSONFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger('ads_sync')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Usage
logger.info('Event pushed successfully', extra={
    'event_name': 'Purchase',
    'record_id': record.id,
    'response_time': 0.5,
    'meta_response': response
})
```

### Alert Configuration

```yaml
# Prometheus alerting rules
groups:
  - name: ads_sync_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: WebhookProcessingDelay
        expr: histogram_quantile(0.95, rate(webhook_processing_duration_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Webhook processing delay > 30s"
```

### Dashboard Grafana

**Key Panels:**
- Event Push Success Rate
- Webhook Processing Latency
- Error Rate by Event Type
- Daily Event Volume
- Meta API Response Times

---

## Cấu Hình Nâng Cao

### Custom Event Fields

```python
class MetaEventConfig(models.Model):
    _inherit = 'meta.event.config'
    
    custom_fields = fields.One2many('meta.event.custom.field', 'event_config_id')
    
    def _extract_custom_data(self, record, extra_data=None):
        custom_data = super()._extract_custom_data(record, extra_data)
        
        # Add custom fields
        for field in self.custom_fields:
            value = self._get_field_value(record, field.field_name)
            if value is not None:
                custom_data[field.meta_field_name] = value
        
        return custom_data
    
    def _get_field_value(self, record, field_path):
        """Extract nested field values using dot notation"""
        try:
            obj = record
            for part in field_path.split('.'):
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            return None
```

### Rate Limiting Configuration

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per minute"]
)

@app.route('/meta/events/push')
@limiter.limit("50 per minute")
def push_event():
    # Implementation
    pass
```

### Circuit Breaker Pattern

```python
import circuitbreaker

@circuitbreaker.circuit(failure_threshold=5, recovery_timeout=60)
def call_meta_api(payload):
    response = requests.post(META_API_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()
```

### Batch Processing

```python
def batch_push_events(self, events):
    """
    Push multiple events in single API call for efficiency
    """
    if not events:
        return
    
    batch_payload = {'data': []}
    
    for event in events:
        payload = self._build_payload_from_record(event['record'], event['extra_data'])
        batch_payload['data'].extend(payload['data'])
    
    # Limit batch size to Meta's constraints
    if len(batch_payload['data']) > 1000:
        # Split into chunks
        chunks = [batch_payload['data'][i:i+1000] for i in range(0, len(batch_payload['data']), 1000)]
        for chunk in chunks:
            self._push_batch({'data': chunk})
    else:
        self._push_batch(batch_payload)
```

---

## Debug và Troubleshooting

### Logging Levels

```python
# Enable debug logging
import logging
logging.getLogger('odoo.addons.ads_sync').setLevel(logging.DEBUG)
logging.getLogger('requests.packages.urllib3').setLevel(logging.DEBUG)
```

### Common Issues và Solutions

1. **Webhook Not Receiving Events:**
   - Check webhook URL accessibility
   - Verify SSL certificate validity
   - Confirm verify token matches

2. **Event Push Failures:**
   - Validate access token permissions
   - Check pixel ID configuration
   - Review payload format against Meta specs

3. **Rate Limiting Issues:**
   - Implement exponential backoff
   - Monitor API usage in Meta dashboard
   - Consider upgrading to higher tier

### Debug Tools

```python
# Test event push manually
def test_event_push(self):
    """Debug method to test event pushing"""
    test_record = self.env['sale.order'].search([], limit=1)
    if not test_record:
        return "No test record found"
    
    config = self.env['meta.event.config'].search([('technical_name', '=', 'purchase')], limit=1)
    if not config:
        return "Purchase event not configured"
    
    result = config.trigger_event('purchase', test_record)
    return f"Result: {result}"
```

---

## Cài Đặt & Nâng Cấp

### Cài Đặt Ban Đầu

```bash
# 1. Install dependencies
./odoo-bin -d your_database -i base,web,mail,crm,sale,account,calendar,mass_mailing

# 2. Install Ads Sync module
./odoo-bin -d your_database -i ads_sync

# 3. Configure system parameters
# Access Settings > Technical > Parameters > System Parameters

# 4. Load event configurations
./odoo-bin -d your_database --load-data=ads_sync/data/meta_event_config_data.xml
```

### Nâng Cấp Module

```bash
# 1. Backup database
pg_dump your_database > backup.sql

# 2. Update module code
git pull origin main

# 3. Upgrade module
./odoo-bin -d your_database -u ads_sync

# 4. Restart Odoo service
sudo systemctl restart odoo
```

### Migration Scripts

```python
# migration script for version upgrades
def migrate(cr, version):
    if not version:
        return
    
    # Add new fields if needed
    cr.execute("""
        ALTER TABLE meta_event_config 
        ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0
    """)
    
    # Update existing records
    cr.execute("""
        UPDATE meta_event_config 
        SET error_count = 0 
        WHERE error_count IS NULL
    """)
```

---

## Mở Rộng Module

### Thêm Event Trigger Mới

1. **Tạo Event Config:**
```xml
<record id="meta_event_custom" model="meta.event.config">
    <field name="name">Custom Event</field>
    <field name="technical_name">custom_event</field>
    <field name="category">custom</field>
    <field name="trigger_model">your.model</field>
    <field name="trigger_action">your_method</field>
    <field name="is_active">False</field>
</record>
```

2. **Implement Trigger:**
```python
class YourModelMetaEvents(models.Model):
    _inherit = 'your.model'

    def your_method(self):
        res = super().your_method()
        
        for record in self:
            self.env['meta.event.config'].sudo().trigger_event(
                'custom_event', 
                record,
                extra_data={'custom_field': record.custom_value}
            )
        
        return res
```

3. **Update Routing (nếu cần):**
```python
# In controllers/main.py
routing_map.update({
    'your_custom_field': 'your.model'
})
```

### Custom Payload Builders

```python
class CustomEventConfig(models.Model):
    _inherit = 'meta.event.config'
    
    def _build_custom_payload(self, record, event_data):
        """Override for custom payload logic"""
        payload = super()._build_custom_payload(record, event_data)
        
        # Add custom logic here
        if self.technical_name == 'custom_event':
            payload['data'][0]['custom_data']['special_field'] = record.special_value
        
        return payload
```

---

## Lịch Sử Phiên Bản

| Phiên Bản | Ngày | Thay Đổi Chính |
|-----------|------|----------------|
| 1.0.0 | 28-01-2026 | Phát hành đầu tiên với đầy đủ tính năng CAPI integration, webhook processing, và monitoring |
| 0.9.0 | 15-12-2025 | Beta release với core functionality |
| 0.8.0 | 01-11-2025 | Alpha release với basic event pushing |

---

*Tài liệu này được cập nhật lần cuối vào ngày 28 tháng 1, 2026. Để báo cáo lỗi hoặc đề xuất cải tiến, vui lòng tạo issue trên repository dự án.*

**Các Methods Chính**:

```python
@api.model
def trigger_event(self, technical_name, record, extra_data=None):
    """
    Điểm vào chính để kích hoạt Meta events.
    Được gọi từ các model extensions khi có hành động xảy ra.
    
    :param technical_name: str - Định danh event (vd: 'purchase', 'lead')
    :param record: recordset - Record Odoo đã kích hoạt event
    :param extra_data: dict - Dữ liệu bổ sung để thêm vào payload
    :return: dict - Kết quả với trạng thái thành công và response
    """

def _push_event_to_meta(self, payload, pixel_id=None, access_token=None):
    """
    Đẩy event payload đến Meta CAPI thông qua external server.
    
    Endpoint: {server_url}/meta/events/push
    Method: POST
    Headers: Content-Type: application/json, X-API-Key, Authorization
    """

def _build_payload_from_record(self, record, extra_data=None):
    """
    Xây dựng payload tương thích Meta CAPI từ Odoo record.
    Tự động trích xuất user_data và custom_data.
    """

def _extract_user_data(self, record):
    """
    Trích xuất và hash SHA256 PII từ record.
    Hỗ trợ: email (em), phone (ph), first name (fn), last name (ln)
    """
```

### 2. `ads.meta.webhook.event` - Lưu Trữ Webhook Event

**Mục đích**: Lưu trữ các webhook events đến từ Meta để kiểm toán và xử lý.

**Các Trường Chính**:
| Trường | Kiểu | Mô Tả |
|--------|------|-------|
| `event_type` | Char | Loại webhook event |
| `object_type` | Char | Loại object Meta (page, user, etc.) |
| `entry_id` | Char | Meta entry ID |
| `payload_json` | Text | Raw JSON payload |
| `source_ip` | Char | Địa chỉ IP gửi đến |
| `state` | Selection | Trạng thái xử lý (received, processing, processed, error, ignored) |

**Methods Chính**:

```python
@api.model
def create_from_webhook(self, payload, source_ip=None, subscription=None):
    """
    Factory method để tạo webhook event từ payload đến.
    Trích xuất event_type, object_type, entry_id từ định dạng webhook Meta.
    """
```

### 3. `ads.meta.event.push` - Đẩy Event Thủ Công

**Mục đích**: Giao diện UI để tạo và đẩy events đến Meta CAPI thủ công.

**Tính năng**:
- Các template event có sẵn (Purchase, Lead, AddToCart, etc.)
- Trình soạn thảo JSON payload với xác thực
- Theo dõi response và ghi log lỗi

### 4. `ads.subscription` - Quản Lý Subscription

**Mục đích**: Lưu trữ thông tin xác thực Meta API và cấu hình subscription.

**Các Trường Chính**:
- `meta_pixel_id`: Facebook Pixel ID
- `meta_access_token`: CAPI Access Token
- `meta_app_secret`: App Secret để xác thực chữ ký
- `api_key`: API key của external server

---

## Model Extensions (Triggers)

Nằm trong `models/meta_event_triggers.py`, các extensions này mở rộng các model core Odoo để kích hoạt Meta events.

### Bảng Ánh Xạ Trigger

| Model | Method | Technical Name | Meta Event |
|-------|--------|----------------|------------|
| `crm.lead` | `create` | `lead` | Lead |
| `crm.lead` | `convert_opportunity` | `qualified_lead` | QualifiedLead |
| `crm.lead` | `action_set_won_rainbowman` | `converted_lead` | ConvertedLead |
| `sale.order` | `action_confirm` | `purchase` | Purchase |
| `sale.order` | `action_quotation_sent` | `initiate_checkout` | InitiateCheckout |
| `account.move` | `action_post` | `add_payment_info` | AddPaymentInfo |
| `res.partner` | `create` | `contact` | Contact |
| `res.users` | `create` | `complete_registration` | CompleteRegistration |
| `calendar.event` | `create` | `schedule` | Schedule |
| `mailing.contact` | `create` | `subscribe` | Subscribe |

### Mẫu Triển Khai Trigger

```python
class CrmLeadMetaEvents(models.Model):
    _inherit = 'crm.lead'

    def action_set_won_rainbowman(self):
        res = super().action_set_won_rainbowman()
        
        for record in self:
            try:
                self.env['meta.event.config'].sudo().trigger_event(
                    'converted_lead',  # technical_name
                    record,            # record
                    extra_data={'outcome': 'won'}
                )
            except Exception as e:
                _logger.exception(f"Không thể kích hoạt event: {e}")
        
        return res
```

---

## Controllers

### Webhook Endpoints (`controllers/main.py`)

#### `GET /webhooks/meta` - Xác Thực Webhook

Meta gửi request này để xác thực webhook URL trong quá trình thiết lập.

**Tham số**:
- `hub.mode`: Phải là 'subscribe'
- `hub.verify_token`: Phải khớp với token đã cấu hình
- `hub.challenge`: Trả về giá trị này để xác thực

**Response**: Chuỗi challenge dạng plain text

#### `POST /webhooks/meta` - Nhận Webhook Events

**Quy trình xử lý**:
1. Parse JSON payload từ request body
2. Tạo record `ads.meta.webhook.event`
3. Định tuyến đến các model Odoo phù hợp dựa trên loại `field`
4. Trả về 200 OK (luôn luôn, để tránh Meta vô hiệu hóa webhook)

**Định Tuyến Event**:
| Field | Model Đích | Mô Tả |
|-------|------------|-------|
| `affiliation` | `crm.lead` | Quan hệ đối tác |
| `attire` | `sale.order` | Sở thích sản phẩm |
| `awards` | `crm.lead` | Thành tựu khách hàng |

---

## Cấu Hình

### Tham Số Hệ Thống

| Tham Số | Mô Tả | Mặc Định |
|---------|-------|----------|
| `ads_sync.server_url` | URL base của external server | `https://...ngrok.../api/v1` |
| `ads_sync.meta_webhook_verify_token` | Token xác thực webhook | - |
| `meta.pixel_id` | Facebook Pixel ID mặc định | - |
| `meta.test_event_code` | Mã test event để debug | - |

### Dữ Liệu Cấu Hình Event

Các events được cấu hình sẵn được load từ `data/meta_event_config_data.xml`:

```xml
<record id="meta_event_purchase" model="meta.event.config">
    <field name="name">Purchase</field>
    <field name="technical_name">purchase</field>
    <field name="category">sales</field>
    <field name="trigger_model">sale.order</field>
    <field name="trigger_action">action_confirm</field>
    <field name="is_active">False</field>
</record>
```

---

## Định Dạng API Payload

### Payload Event Đi (đến Meta CAPI)

```json
{
  "data": [{
    "event_name": "Purchase",
    "event_time": 1737561600,
    "event_id": "purchase_sale_order_123_1737561600",
    "action_source": "system_generated",
    "user_data": {
      "em": ["sha256_hashed_email"],
      "ph": ["sha256_hashed_phone"],
      "fn": ["sha256_hashed_firstname"],
      "ln": ["sha256_hashed_lastname"]
    },
    "custom_data": {
      "currency": "USD",
      "value": 150.00,
      "content_name": "SO001",
      "content_ids": ["123"],
      "order_id": "SO001",
      "num_items": 3,
      "contents": [
        {"id": "PROD001", "quantity": 2, "item_price": 50.00}
      ]
    }
  }]
}
```

### Payload Webhook Đến (từ Meta)

```json
{
  "object": "page",
  "entry": [{
    "id": "123456789",
    "time": 1737561600,
    "changes": [{
      "field": "affiliation",
      "value": {
        "name": "Tên Đối Tác",
        "email": "partner@example.com"
      }
    }]
  }]
}
```

---

## Bảo Mật

### Kiểm Soát Truy Cập (ir.model.access.csv)

| Model | Nhóm | Đọc | Ghi | Tạo | Xóa |
|-------|------|-----|-----|-----|-----|
| `meta.event.config` | User | ✓ | ✓ | ✓ | ✗ |
| `meta.event.config` | System | ✓ | ✓ | ✓ | ✓ |
| `ads.meta.webhook.event` | User | ✓ | ✓ | ✓ | ✗ |
| `ads.meta.webhook.event` | System | ✓ | ✓ | ✓ | ✓ |

### Hash Dữ Liệu

Tất cả PII gửi đến Meta đều được hash SHA256 theo yêu cầu Meta CAPI:
- Email: chuyển thường, cắt khoảng trắng, sau đó hash
- Điện thoại: chỉ giữ số, sau đó hash
- Tên: chuyển thường, cắt khoảng trắng, sau đó hash

---

## Debug

### Logging

Bật debug logging cho các logger sau:
- `odoo.addons.ads_sync.models.meta_event_config`
- `odoo.addons.ads_sync.models.meta_event_triggers`
- `odoo.addons.ads_sync.controllers.main`

Tìm các prefix log:
- `[MetaEventConfig]` - Cấu hình event và đẩy dữ liệu
- `[MetaEventTrigger]` - Các event trigger từ model

### Chế Độ Test

1. Bật "Test Mode" trên cấu hình event
2. Đặt tham số hệ thống `meta.test_event_code`
3. Events sẽ được gửi với test_event_code để debug trong Meta Events Manager

---

## Cài Đặt & Nâng Cấp

```bash
# Cài đặt
./odoo-bin -d your_database -i ads_sync

# Nâng cấp (sau khi thay đổi code)
./odoo-bin -d your_database -u ads_sync

# Với các dependencies
./odoo-bin -d your_database -i crm,sale,account,calendar,mass_mailing,ads_sync
```

---

## Mở Rộng Module

### Thêm Event Trigger Mới

1. Thêm cấu hình event trong `data/meta_event_config_data.xml`:
```xml
<record id="meta_event_custom" model="meta.event.config">
    <field name="name">CustomEvent</field>
    <field name="technical_name">custom_event</field>
    <field name="trigger_model">your.model</field>
    <field name="trigger_action">your_method</field>
    ...
</record>
```

2. Thêm trigger trong `models/meta_event_triggers.py`:
```python
class YourModelMetaEvents(models.Model):
    _inherit = 'your.model'

    def your_method(self):
        res = super().your_method()
        for record in self:
            self.env['meta.event.config'].sudo().trigger_event(
                'custom_event', record
            )
        return res
```

3. Cập nhật `_compute_trigger_description` trong `meta_event_config.py` để có mô tả dễ đọc.

---

## Lịch Sử Phiên Bản

| Phiên Bản | Ngày | Thay Đổi |
|-----------|------|----------|
| 1.0.0 | 22-01-2026 | Phát hành đầu tiên với 10 events cấu hình sẵn |
