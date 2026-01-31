# -*- coding: utf-8 -*-

import json
import time
import hashlib
import requests
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MetaEventConfig(models.Model):
    _name = 'meta.event.config'
    _description = 'Meta Event Push Configuration'
    _order = 'category, sequence, name'

    name = fields.Char(
        string='Event Name',
        required=True,
        help='Meta Conversion API event name (e.g., Purchase, Lead, etc.)'
    )
    
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help='Technical identifier for the event',
        index=True,
    )
    
    description = fields.Text(
        string='Description',
        help='Description of when this event should be triggered'
    )
    
    category = fields.Selection([
        ('lead', 'Lead Generation'),
        ('sales', 'Sales & Purchase'),
        ('engagement', 'User Engagement'),
        ('registration', 'Registration & Subscription'),
        ('ecommerce', 'E-commerce'),
    ], string='Category', required=True, default='lead', index=True)
    
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Enable this event to be pushed to Meta when the trigger action occurs'
    )
    
    trigger_model = fields.Char(
        string='Trigger Model',
        help='Odoo model that triggers this event (e.g., crm.lead, sale.order)'
    )
    
    trigger_action = fields.Char(
        string='Trigger Action',
        help='The action/method that triggers this event (e.g., action_set_won, action_confirm)'
    )
    
    trigger_description = fields.Char(
        string='Trigger Description',
        compute='_compute_trigger_description',
        store=True,
        help='Human-readable description of the trigger'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display'
    )
    
    # Event parameters configuration
    include_user_data = fields.Boolean(
        string='Include User Data',
        default=True,
        help='Include hashed user data (email, phone) in the event'
    )
    
    include_custom_data = fields.Boolean(
        string='Include Custom Data',
        default=True,
        help='Include custom data (value, currency, content) in the event'
    )
    
    test_mode = fields.Boolean(
        string='Test Mode',
        default=False,
        help='Send events with test_event_code for debugging in Meta Events Manager'
    )
    
    # Statistics
    push_count = fields.Integer(
        string='Push Count',
        default=0,
        readonly=True,
        help='Number of times this event has been pushed to Meta'
    )
    
    last_push_date = fields.Datetime(
        string='Last Push Date',
        readonly=True,
        help='Last time this event was pushed to Meta'
    )
    
    @api.depends('trigger_model', 'trigger_action')
    def _compute_trigger_description(self):
        trigger_map = {
            # Lead Generation Events
            ('crm.lead', 'create'): 'When a new lead is created',
            ('crm.lead', 'convert_opportunity'): 'When lead is converted to opportunity',
            ('crm.lead', 'action_set_won_rainbowman'): 'When opportunity is marked as Won',
            ('crm.lead', 'action_set_lost'): 'When opportunity is marked as Lost',
            ('crm.lead', 'search'): 'When leads are searched',
            
            # Sales & Purchase Events
            ('sale.order', 'create'): 'When a sale order is created',
            ('sale.order', 'action_confirm'): 'When sale order is confirmed',
            ('sale.order', 'action_quotation_sent'): 'When quotation is sent to customer',
            ('sale.order', 'action_cancel'): 'When sale order is cancelled',
            ('sale.order.line', 'create'): 'When order line is added to cart',
            
            # User Engagement Events
            ('res.partner', 'create'): 'When a new contact is created',
            ('res.partner', 'write'): 'When contact profile is updated',
            ('calendar.event', 'create'): 'When a meeting is scheduled',
            
            # Registration & Subscription Events
            ('res.users', 'create'): 'When a new user registers',
            # E-commerce Events
            ('product.product', 'create'): 'When a new product is created',
            ('product.category', 'create'): 'When a product category is created',
            
            # Payment Events
            ('account.move', 'action_post'): 'When invoice is posted/validated',
            ('account.payment', 'create'): 'When a payment is created',
        }
        for record in self:
            key = (record.trigger_model, record.trigger_action)
            record.trigger_description = trigger_map.get(key, f'{record.trigger_model} → {record.trigger_action}')

    def action_toggle_active(self):
        """Toggle the active state of the event configuration."""
        for record in self:
            record.is_active = not record.is_active
            status = 'activated' if record.is_active else 'deactivated'
            _logger.info(f"Meta Event '{record.name}' has been {status}")
        return True

    def action_test_push(self):
        """Send a test event to Meta for debugging."""
        self.ensure_one()
        _logger.info(f"Sending test event '{self.name}' to Meta...")
        
        # Create a test payload
        test_payload = self._build_test_payload()
        
        # Push to Meta
        result = self._push_event_to_meta(test_payload)
        
        if result.get('success'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Event Sent',
                    'message': f'Test event "{self.name}" has been sent to Meta successfully.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Test Event Failed',
                    'message': f'Failed to send test event: {result.get("error", "Unknown error")}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _build_test_payload(self):
        """Build a test payload for the event."""
        return {
            "data": [{
                "event_name": self.name,
                "event_time": int(time.time()),
                "event_id": f"test_{self.technical_name}_{int(time.time())}",
                "action_source": "system_generated",
                "user_data": {
                    "em": [hashlib.sha256("test@example.com".encode()).hexdigest()],
                },
                "custom_data": {
                    "test_mode": True,
                    "source": "odoo_meta_event_config",
                }
            }]
        }

    @api.model
    def is_event_active(self, technical_name):
        """Check if an event is active by its technical name."""
        config = self.search([('technical_name', '=', technical_name), ('is_active', '=', True)], limit=1)
        return bool(config)

    @api.model
    def get_active_event(self, technical_name):
        """Get active event configuration by technical name."""
        return self.search([('technical_name', '=', technical_name), ('is_active', '=', True)], limit=1)

    def increment_push_count(self):
        """Increment the push count and update last push date."""
        self.write({
            'push_count': self.push_count + 1,
            'last_push_date': fields.Datetime.now(),
        })

    def _get_server_url(self):
        """Get the external server URL from system parameters."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'ads_sync.server_url', 
            default='https://easter-unprofiteering-tristin.ngrok-free.dev/api/v1'
        )

    def _get_subscription(self):
        """Get an active Meta subscription for pushing events."""
        return self.env['ads.subscription'].sudo().search([
            ('state', '=', 'subscribed'),
            ('platform', '=', 'meta')
        ], limit=1)

    def _push_event_to_meta(self, payload, pixel_id=None, access_token=None):
        """
        Push an event to Meta CAPI via the external server.
        
        :param payload: dict - The event payload
        :param pixel_id: str - Optional pixel ID override
        :param access_token: str - Optional access token override
        :return: dict - Result with success status and response/error
        """
        server_url = self._get_server_url()
        subscription = self._get_subscription()
        
        # Build request body
        request_body = {'payload': payload}
        
        # Add pixel_id
        if pixel_id:
            request_body['pixel_id'] = pixel_id
        elif subscription and subscription.meta_pixel_id:
            request_body['pixel_id'] = subscription.meta_pixel_id
        else:
            # Try system parameter
            request_body['pixel_id'] = self.env['ir.config_parameter'].sudo().get_param('meta.pixel_id', '')
        
        # Add access_token
        if access_token:
            request_body['access_token'] = access_token
        elif subscription and subscription.meta_access_token:
            request_body['access_token'] = subscription.meta_access_token
        
        # Add test_event_code if in test mode
        if self.test_mode:
            test_code = self.env['ir.config_parameter'].sudo().get_param('meta.test_event_code', '')
            if test_code:
                request_body['test_event_code'] = test_code
        
        # Build headers
        headers = {'Content-Type': 'application/json'}
        if subscription and subscription.api_key:
            headers['X-API-Key'] = subscription.api_key
            headers['Authorization'] = f'Bearer {subscription.api_key}'
        
        # Prepare data for creating the monitor record
        event_name = payload.get('data', [{}])[0].get('event_name', self.name)
        monitor_vals = {
            'name': f"{event_name} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'template': self.technical_name if self.technical_name in ['purchase', 'add_to_cart', 'initiate_checkout', 'lead', 'complete_registration', 'contact', 'view_content', 'search', 'add_payment_info', 'subscribe'] else 'custom',
            'payload_json': json.dumps(payload),
            'pixel_id_override': pixel_id,
            'access_token_override': access_token,
            'subscription_id': subscription.id if subscription else False,
            'state': 'sent',  # Initially set to sent, will update based on result
            'sent_at': fields.Datetime.now(),
        }
        
        try:
            _logger.info(f"[MetaEventConfig] Pushing event '{self.name}' to {server_url}/meta/events/push")
            _logger.debug(f"[MetaEventConfig] Payload: {json.dumps(request_body, indent=2)}")
            
            response = requests.post(
                f"{server_url}/meta/events/push",
                json=request_body,
                headers=headers,
                timeout=30
            )
            
            response_data = response.json() if response.content else {}
            
            if response.status_code == 200:
                _logger.info(f"[MetaEventConfig] Event '{self.name}' pushed successfully")
                self.increment_push_count()
                monitor_vals.update({
                    'state': 'success',
                    'response_json': json.dumps(response_data),
                })
                result = {
                    'success': True,
                    'response': response_data,
                    'status_code': response.status_code,
                }
            else:
                error_msg = response_data.get('error', response.text)
                _logger.error(f"[MetaEventConfig] Failed to push event '{self.name}': {error_msg}")
                monitor_vals.update({
                    'state': 'error',
                    'response_json': json.dumps(response_data),
                    'error_message': error_msg,
                })
                result = {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {error_msg}",
                    'response': response_data,
                    'status_code': response.status_code,
                }
                
        except requests.RequestException as e:
            _logger.exception(f"[MetaEventConfig] Connection error pushing event '{self.name}': {str(e)}")
            monitor_vals.update({
                'state': 'error',
                'error_message': f"Connection error: {str(e)}",
            })
            result = {
                'success': False,
                'error': f"Connection error: {str(e)}",
            }
        
        # Create the monitor record
        self.env['ads.meta.event.push'].sudo().create(monitor_vals)
        
        return result

    @api.model
    def trigger_event(self, technical_name, record, extra_data=None, check_view_preference=True):
        """
        Trigger a Meta event if it's active.
        
        This is the main method to be called from other models when an action occurs.
        
        :param technical_name: str - The technical name of the event (e.g., 'purchase', 'qualified_lead')
        :param record: recordset - The record that triggered the event
        :param extra_data: dict - Additional data to include in the event
        :param check_view_preference: bool - Whether to check per-record event preferences
        :return: dict - Result of the push or None if event is not active
        """
        config = self.get_active_event(technical_name)
        if not config:
            _logger.debug(f"[MetaEventConfig] Event '{technical_name}' is not active, skipping push")
            return None
        
        # Check if the record has per-view preference and if it's disabled
        if check_view_preference and hasattr(record, 'meta_event_enabled'):
            if not record.meta_event_enabled:
                _logger.debug(f"[MetaEventConfig] Event '{technical_name}' is disabled for {record._name} ID {record.id}")
                return None
        
        _logger.info(f"[MetaEventConfig] Triggering event '{technical_name}' for {record._name} ID {record.id}")
        
        # Build the payload based on the record and event configuration
        payload = config._build_payload_from_record(record, extra_data)
        
        # Push to Meta
        return config._push_event_to_meta(payload)

    def _build_payload_from_record(self, record, extra_data=None):
        """
        Build a Meta CAPI payload from an Odoo record.
        
        :param record: recordset - The record to build payload from
        :param extra_data: dict - Additional data to include
        :return: dict - The event payload
        """
        event_time = int(time.time())
        event_id = f"{self.technical_name}_{record._name.replace('.', '_')}_{record.id}_{event_time}"
        
        payload = {
            "data": [{
                "event_name": self.name,
                "event_time": event_time,
                "event_id": event_id,
                "action_source": "system_generated",
            }]
        }
        
        event_data = payload["data"][0]
        
        # Add user data if configured
        if self.include_user_data:
            user_data = self._extract_user_data(record)
            if user_data:
                event_data["user_data"] = user_data
        
        # Add custom data if configured
        if self.include_custom_data:
            custom_data = self._extract_custom_data(record, extra_data)
            if custom_data:
                event_data["custom_data"] = custom_data
        
        return payload

    def _extract_user_data(self, record):
        """
        Extract and hash user data from a record.
        
        :param record: recordset - The record to extract user data from
        :return: dict - Hashed user data for Meta CAPI
        """
        user_data = {}
        
        # Try to get email
        email = None
        if hasattr(record, 'email_from'):
            email = record.email_from
        elif hasattr(record, 'email'):
            email = record.email
        elif hasattr(record, 'partner_id') and record.partner_id:
            email = record.partner_id.email
        
        if email:
            user_data['em'] = [hashlib.sha256(email.lower().strip().encode()).hexdigest()]
        
        # Try to get phone
        phone = None
        if hasattr(record, 'phone'):
            phone = record.phone
        elif hasattr(record, 'mobile'):
            phone = record.mobile
        elif hasattr(record, 'partner_id') and record.partner_id:
            phone = record.partner_id.phone or record.partner_id.mobile
        
        if phone:
            # Normalize phone number (remove spaces, dashes, etc.)
            normalized_phone = ''.join(filter(str.isdigit, phone))
            if normalized_phone:
                user_data['ph'] = [hashlib.sha256(normalized_phone.encode()).hexdigest()]
        
        # Try to get name
        name = None
        if hasattr(record, 'contact_name'):
            name = record.contact_name
        elif hasattr(record, 'partner_name'):
            name = record.partner_name
        elif hasattr(record, 'name') and record._name != 'sale.order':
            name = record.name
        elif hasattr(record, 'partner_id') and record.partner_id:
            name = record.partner_id.name
        
        if name:
            parts = name.split(' ', 1)
            fn = parts[0].lower().strip() if parts else ''
            ln = parts[1].lower().strip() if len(parts) > 1 else ''
            if fn:
                user_data['fn'] = [hashlib.sha256(fn.encode()).hexdigest()]
            if ln:
                user_data['ln'] = [hashlib.sha256(ln.encode()).hexdigest()]
        
        return user_data

    def _extract_custom_data(self, record, extra_data=None):
        """
        Extract custom data from a record.
        
        :param record: recordset - The record to extract custom data from
        :param extra_data: dict - Additional data provided by the caller
        :return: dict - Custom data for Meta CAPI
        """
        custom_data = {}
        
        # Add record reference
        custom_data['content_name'] = record.display_name if hasattr(record, 'display_name') else str(record.id)
        custom_data['content_ids'] = [str(record.id)]
        
        # Try to get value/amount
        if hasattr(record, 'amount_total'):
            custom_data['value'] = float(record.amount_total)
        elif hasattr(record, 'expected_revenue'):
            custom_data['value'] = float(record.expected_revenue or 0)
        elif hasattr(record, 'planned_revenue'):
            custom_data['value'] = float(record.planned_revenue or 0)
        
        # Try to get currency
        if hasattr(record, 'currency_id') and record.currency_id:
            custom_data['currency'] = record.currency_id.name
        elif hasattr(record, 'company_id') and record.company_id and record.company_id.currency_id:
            custom_data['currency'] = record.company_id.currency_id.name
        
        # Add model-specific data
        if record._name == 'crm.lead':
            custom_data['lead_id'] = str(record.id)
            if record.stage_id:
                custom_data['status'] = record.stage_id.name
        elif record._name == 'sale.order':
            custom_data['order_id'] = record.name
            custom_data['num_items'] = len(record.order_line)
        
        # Merge with extra data
        if extra_data:
            custom_data.update(extra_data)
        
        return custom_data