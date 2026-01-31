# -*- coding: utf-8 -*-

import secrets
import string
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AdsSubscription(models.Model):
    _name = 'ads.subscription'
    _description = 'Ads Platform Subscription'
    _order = 'create_date desc'
    # Add mail.thread here
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Subscription Name',
        tracking=True,
        required=True,
        help='A friendly name for this subscription (e.g., "My Odoo Instance")'
    )
    
    platform = fields.Selection([
        ('meta', 'Meta (Facebook/Instagram)'),
        ('google', 'Google Ads'),
        ('tiktok', 'TikTok Ads'),
    ], string='Platform', required=True, default='meta')
    
    # Subscription Response Fields
    subscription_id = fields.Char(
        string='Subscription ID',
        readonly=True,
        copy=False,
        help='Unique subscription identifier returned from the API'
    )
    
    api_key = fields.Char(
        string='API Key',
        readonly=True,
        copy=False,
        help='API key for authenticating webhook requests'
    )
    
    webhook_verify_token = fields.Char(
        string='Webhook Verify Token',
        readonly=True,
        copy=False,
        help='Token used to verify webhook requests'
    )
    
    callback_url = fields.Char(
        string='Odoo Callback URL',
        help='URL where the middleman server will send webhook events to Odoo'
    )
    
    api_callback_url = fields.Char(
        string='API Callback URL',
        compute='_compute_api_callback_url',
        store=False,
        help='URL on middleman server - register this in Meta Events Manager'
    )
    
    # Meta Credentials
    meta_access_token = fields.Char(
        string='Access Token',
        help='Meta API Access Token (starts with EAA...)'
    )
    
    meta_pixel_id = fields.Char(
        string='Pixel ID',
        help='Meta Pixel ID for tracking conversions'
    )
    
    meta_test_event_code = fields.Char(
        string='Test Event Code',
        help='Test Event Code for debugging (e.g., TEST12345)'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('subscribed', 'Subscribed'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', readonly=True, copy=False)
    
    is_active = fields.Boolean(
        string='Active',
        default=False,
        help='Mark this subscription as the active one to use for services'
    )
    
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        copy=False
    )
    
    subscribed_at = fields.Datetime(
        string='Subscribed At',
        readonly=True,
        copy=False
    )
    
    # API Endpoint Configuration
    api_endpoint = fields.Char(
        string='API Endpoint',
        default='http://localhost:8000/api/v1',
        help='Base URL of the subscription API'
    )

    @api.depends('platform', 'api_endpoint', 'api_key')
    def _compute_api_callback_url(self):
        """Compute the API callback URL based on API endpoint, platform and api_key."""
        for record in self:
            if record.platform and record.api_endpoint and record.api_key:
                record.api_callback_url = f"{record.api_endpoint.rstrip('/')}/{record.platform}/{record.api_key}"
            else:
                record.api_callback_url = False

    @api.constrains('platform', 'meta_access_token', 'meta_pixel_id')
    def _check_meta_credentials(self):
        for record in self:
            if record.platform == 'meta':
                if not record.meta_access_token:
                    raise ValidationError('Access Token is required for Meta platform')
                if not record.meta_pixel_id:
                    raise ValidationError('Pixel ID is required for Meta platform')

    def _generate_token(self, prefix, length=24):
        """Generate a random token with a prefix."""
        chars = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(chars) for _ in range(length))
        return f"{prefix}_{random_part}"

    def action_subscribe(self):
        """Create a webhook subscription by calling the external API."""
        self.ensure_one()
        
        if self.state == 'subscribed':
            raise UserError('This subscription is already active.')
        
        # Build the request payload
        payload = {
            'name': self.name,
            'platform': self.platform,
            'callback_url': self.callback_url,
        }
        
        if self.platform == 'meta':
            payload['meta_credentials'] = {
                'access_token': self.meta_access_token,
                'pixel_id': self.meta_pixel_id,
            }
            # if self.meta_app_secret:
            #     payload['meta_credentials']['app_secret'] = self.meta_app_secret
            if self.meta_test_event_code:
                payload['meta_credentials']['test_event_code'] = self.meta_test_event_code
        
        try:
            # Make the API call
            response = requests.post(
                f"{self.api_endpoint.rstrip('/')}/subscribe",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                self.write({
                    'subscription_id': data.get('subscription_id'),
                    'api_key': data.get('api_key'),
                    'webhook_verify_token': data.get('webhook_verify_token'),
                    'state': 'subscribed',
                    'subscribed_at': fields.Datetime.now(),
                    'error_message': False,
                })
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                self.write({
                    'state': 'error',
                    'error_message': error_msg,
                })
                raise UserError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Connection Error: {str(e)}"
            self.write({
                'state': 'error',
                'error_message': error_msg,
            })
            raise UserError(error_msg)

    def action_subscribe_local(self):
        """Create a local subscription (for testing without external API)."""
        self.ensure_one()
        
        if self.state == 'subscribed':
            raise UserError('This subscription is already active.')
        
        # Generate tokens locally
        subscription_id = self._generate_token('sub', 12)
        api_key = self._generate_token('mk_live', 24)
        webhook_verify_token = self._generate_token('wvt', 16)
        
        self.write({
            'subscription_id': subscription_id,
            'api_key': api_key,
            'webhook_verify_token': webhook_verify_token,
            'state': 'subscribed',
            'subscribed_at': fields.Datetime.now(),
            'error_message': False,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Subscription created successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Cancel the subscription."""
        self.ensure_one()
        self.write({
            'state': 'cancelled',
        })

    def action_reset_to_draft(self):
        """Reset subscription to draft state."""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'subscription_id': False,
            'api_key': False,
            'webhook_verify_token': False,
            'subscribed_at': False,
            'error_message': False,
        })

    def action_view_credentials(self):
        """Open a wizard to display the subscription credentials."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subscription Credentials',
            'res_model': 'ads.subscription',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('ads_sync.view_ads_subscription_credentials_form').id,
            'target': 'new',
        }

    def action_use_subscription(self):
        """Set this subscription as the active one."""
        self.ensure_one()
        # Deactivate all other subscriptions of the same platform
        self.search([
            ('platform', '=', self.platform),
            ('id', '!=', self.id),
            ('is_active', '=', True)
        ]).write({'is_active': False})
        # Activate this one
        self.write({'is_active': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Subscription Activated',
                'message': f'"{self.name}" is now the active subscription for {self.platform}.',
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._update_menu_active()
        return records

    @api.model
    def write(self, vals):
        result = super().write(vals)
        self._update_menu_active()
        return result

    @api.model
    def unlink(self):
        result = super().unlink()
        self._update_menu_active()
        return result

    def _update_menu_active(self):
        """Update the active status of menu items based on subscription existence."""
        has_subscriptions = self.search_count([]) > 0
        menu_refs = [
            'ads_sync.menu_ads_sync_events',
            'ads_sync.menu_meta_event_push',
            'ads_sync.menu_ads_sync_monitoring',
            'ads_sync.menu_meta_webhook_events',
            'ads_sync.menu_meta_event_push_monitor',
        ]
        for ref in menu_refs:
            try:
                menu = self.env.ref(ref)
                menu.active = has_subscriptions
            except ValueError:
                # Menu not found, skip
                pass
