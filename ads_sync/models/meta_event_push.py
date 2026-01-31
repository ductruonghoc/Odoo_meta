# -*- coding: utf-8 -*-

import json
import time
import requests
import logging

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Event Templates for common Odoo events
EVENT_TEMPLATES = {
    'purchase': {
        'name': 'Purchase',
        'description': 'When a customer completes a purchase',
        'payload': {
            "data": [{
                "event_name": "Purchase",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""],
                    "fn": [""],
                    "ln": [""],
                    "ct": [""],
                    "st": [""],
                    "zp": [""],
                    "country": [""]
                },
                "custom_data": {
                    "currency": "USD",
                    "value": 0.00,
                    "content_type": "product",
                    "contents": [],
                    "num_items": 0
                }
            }]
        }
    },
    'add_to_cart': {
        'name': 'AddToCart',
        'description': 'When a product is added to cart',
        'payload': {
            "data": [{
                "event_name": "AddToCart",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""]
                },
                "custom_data": {
                    "currency": "USD",
                    "value": 0.00,
                    "content_type": "product",
                    "content_ids": [],
                    "contents": []
                }
            }]
        }
    },
    'initiate_checkout': {
        'name': 'InitiateCheckout',
        'description': 'When checkout process begins',
        'payload': {
            "data": [{
                "event_name": "InitiateCheckout",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""]
                },
                "custom_data": {
                    "currency": "USD",
                    "value": 0.00,
                    "num_items": 0
                }
            }]
        }
    },
    'lead': {
        'name': 'Lead',
        'description': 'When a new lead is created',
        'payload': {
            "data": [{
                "event_name": "Lead",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""],
                    "fn": [""],
                    "ln": [""]
                },
                "custom_data": {
                    "lead_id": "",
                    "content_name": ""
                }
            }]
        }
    },
    'complete_registration': {
        'name': 'CompleteRegistration',
        'description': 'When user completes registration',
        'payload': {
            "data": [{
                "event_name": "CompleteRegistration",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""],
                    "fn": [""],
                    "ln": [""]
                },
                "custom_data": {
                    "status": "registered"
                }
            }]
        }
    },
    'contact': {
        'name': 'Contact',
        'description': 'When user submits contact form',
        'payload': {
            "data": [{
                "event_name": "Contact",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""],
                    "fn": [""],
                    "ln": [""]
                },
                "custom_data": {}
            }]
        }
    },
    'view_content': {
        'name': 'ViewContent',
        'description': 'When user views a product/page',
        'payload': {
            "data": [{
                "event_name": "ViewContent",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""]
                },
                "custom_data": {
                    "content_type": "product",
                    "content_ids": [],
                    "content_name": "",
                    "currency": "USD",
                    "value": 0.00
                }
            }]
        }
    },
    'search': {
        'name': 'Search',
        'description': 'When user performs a search',
        'payload': {
            "data": [{
                "event_name": "Search",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""]
                },
                "custom_data": {
                    "search_string": ""
                }
            }]
        }
    },
    'add_payment_info': {
        'name': 'AddPaymentInfo',
        'description': 'When user adds payment info',
        'payload': {
            "data": [{
                "event_name": "AddPaymentInfo",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""]
                },
                "custom_data": {
                    "currency": "USD",
                    "value": 0.00
                }
            }]
        }
    },
    'subscribe': {
        'name': 'Subscribe',
        'description': 'When user subscribes to newsletter/service',
        'payload': {
            "data": [{
                "event_name": "Subscribe",
                "event_time": 0,
                "event_id": "",
                "action_source": "website",
                "user_data": {
                    "em": [""],
                    "ph": [""]
                },
                "custom_data": {
                    "predicted_ltv": 0.00
                }
            }]
        }
    },
}


class MetaEventPush(models.Model):
    _name = 'ads.meta.event.push'
    _description = 'Meta Event Push'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: f"Event Push {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    template = fields.Selection([
        ('purchase', 'Purchase'),
        ('add_to_cart', 'Add to Cart'),
        ('initiate_checkout', 'Initiate Checkout'),
        ('lead', 'Lead'),
        ('complete_registration', 'Complete Registration'),
        ('contact', 'Contact'),
        ('view_content', 'View Content'),
        ('search', 'Search'),
        ('add_payment_info', 'Add Payment Info'),
        ('subscribe', 'Subscribe'),
        ('custom', 'Custom Event'),
    ], string='Event Template', default='custom')
    
    payload_json = fields.Text(
        string='Event Payload (JSON)',
        required=True,
        help='The event payload in JSON format to send to Meta CAPI'
    )
    
    payload_formatted = fields.Text(
        string='Formatted Payload',
        compute='_compute_payload_formatted',
        help='Pretty-printed JSON for display'
    )
    
    pixel_id_override = fields.Char(
        string='Pixel ID Override',
        help='Optional: Override the default pixel ID from subscription'
    )
    
    access_token_override = fields.Char(
        string='Access Token Override',
        help='Optional: Override the default access token from subscription'
    )
    
    subscription_id = fields.Many2one(
        'ads.subscription',
        string='Subscription',
        domain="[('state', '=', 'subscribed'), ('platform', '=', 'meta')]",
        help='Select a subscription to use its credentials (if not overriding)'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('success', 'Success'),
        ('error', 'Error'),
    ], string='Status', default='draft', readonly=True, tracking=True)
    
    response_json = fields.Text(
        string='Response',
        readonly=True,
        help='Response from the external server'
    )
    
    sent_at = fields.Datetime(
        string='Sent At',
        readonly=True,
    )
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
    )

    @api.depends('payload_json')
    def _compute_payload_formatted(self):
        for record in self:
            if record.payload_json:
                try:
                    data = json.loads(record.payload_json)
                    record.payload_formatted = json.dumps(data, indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    record.payload_formatted = record.payload_json
            else:
                record.payload_formatted = ''

    @api.onchange('template')
    def _onchange_template(self):
        """Load template payload when template is selected."""
        if self.template and self.template != 'custom':
            template_data = EVENT_TEMPLATES.get(self.template, {})
            payload = template_data.get('payload', {})
            
            # Set current timestamp
            if payload.get('data') and len(payload['data']) > 0:
                payload['data'][0]['event_time'] = int(time.time())
                payload['data'][0]['event_id'] = f"odoo_{self.template}_{int(time.time())}"
            
            self.payload_json = json.dumps(payload, indent=2)
            
            # Update name with template name
            if template_data.get('name'):
                self.name = f"{template_data['name']} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}"

    def action_validate_json(self):
        """Validate the JSON payload."""
        self.ensure_one()
        try:
            data = json.loads(self.payload_json)
            
            # Basic validation
            if 'data' not in data:
                raise UserError("Payload must contain 'data' array")
            
            if not isinstance(data['data'], list) or len(data['data']) == 0:
                raise UserError("'data' must be a non-empty array")
            
            for event in data['data']:
                if 'event_name' not in event:
                    raise UserError("Each event must have 'event_name'")
                if 'event_time' not in event:
                    raise UserError("Each event must have 'event_time'")
                if 'action_source' not in event:
                    raise UserError("Each event must have 'action_source'")
            
            # Re-format the JSON
            self.payload_json = json.dumps(data, indent=2)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Validation Success',
                    'message': 'JSON payload is valid!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except json.JSONDecodeError as e:
            raise UserError(f"Invalid JSON: {str(e)}")

    def action_set_current_timestamp(self):
        """Set current timestamp in the payload."""
        self.ensure_one()
        try:
            data = json.loads(self.payload_json)
            current_time = int(time.time())
            
            if 'data' in data and isinstance(data['data'], list):
                for event in data['data']:
                    event['event_time'] = current_time
                    if not event.get('event_id'):
                        event['event_id'] = f"odoo_{current_time}_{id(event)}"
            
            self.payload_json = json.dumps(data, indent=2)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Timestamp Updated',
                    'message': f'Event time set to {current_time}',
                    'type': 'info',
                    'sticky': False,
                }
            }
        except json.JSONDecodeError as e:
            raise UserError(f"Invalid JSON: {str(e)}")

    def action_push_event(self):
        """Push the event to Meta CAPI via external server."""
        self.ensure_one()
        
        # Validate JSON first
        try:
            payload_data = json.loads(self.payload_json)
        except json.JSONDecodeError as e:
            self.write({
                'state': 'error',
                'error_message': f"Invalid JSON: {str(e)}"
            })
            raise UserError(f"Invalid JSON: {str(e)}")
        
        # Build request body
        request_body = {
            'payload': payload_data
        }
        
        # Add optional overrides
        if self.pixel_id_override:
            request_body['pixel_id'] = self.pixel_id_override
        elif self.subscription_id and self.subscription_id.meta_pixel_id:
            request_body['pixel_id'] = self.subscription_id.meta_pixel_id
            
        if self.access_token_override:
            request_body['access_token'] = self.access_token_override
        elif self.subscription_id and self.subscription_id.meta_access_token:
            request_body['access_token'] = self.subscription_id.meta_access_token
        
        # Get server URL
        server_url = self.env['ir.config_parameter'].sudo().get_param(
            'ads_sync.server_url', default='https://easter-unprofiteering-tristin.ngrok-free.dev/api/v1'
        )
        
        self.write({'state': 'sent', 'sent_at': fields.Datetime.now()})
        
        # Build headers with API key authentication
        headers = {'Content-Type': 'application/json'}
        if self.subscription_id and self.subscription_id.api_key:
            headers['X-API-Key'] = self.subscription_id.api_key
            headers['Authorization'] = f'Bearer {self.subscription_id.api_key}'
        
        try:
            _logger.info(f"Pushing event to {server_url}/meta/events/push")
            
            response = requests.post(
                f"{server_url}/meta/events/push",
                json=request_body,
                headers=headers,
                timeout=30
            )
            
            response_data = response.json() if response.content else {}
            
            if response.status_code == 200:
                self.write({
                    'state': 'success',
                    'response_json': json.dumps(response_data, indent=2),
                    'error_message': False,
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Event pushed successfully!',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = response_data.get('error', response.text)
                self.write({
                    'state': 'error',
                    'response_json': json.dumps(response_data, indent=2) if response_data else response.text,
                    'error_message': f"HTTP {response.status_code}: {error_msg}",
                })
                raise UserError(f"Failed to push event: {error_msg}")
                
        except requests.RequestException as e:
            _logger.exception(f"Error pushing event: {str(e)}")
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise UserError(f"Connection error: {str(e)}")

    def action_reset_to_draft(self):
        """Reset to draft state."""
        self.write({
            'state': 'draft',
            'response_json': False,
            'error_message': False,
            'sent_at': False,
        })

    def action_duplicate_and_edit(self):
        """Duplicate this record for quick re-push with modifications."""
        self.ensure_one()
        new_record = self.copy({
            'name': f"{self.name} (Copy)",
            'state': 'draft',
            'response_json': False,
            'error_message': False,
            'sent_at': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ads.meta.event.push',
            'res_id': new_record.id,
            'view_mode': 'form',
            'target': 'current',
        }