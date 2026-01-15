import requests
import logging
import json
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class FacebookLeadWebhook(http.Controller):
    # Dùng Permanent Token bạn đã lấy ở Milestone 1
    ACCESS_TOKEN = '5&9k8BiS7*\('

    @http.route('/webhook/facebook', type='http', auth='public', methods=['POST'], csrf=False)
    def facebook_receive_lead(self):
        try:
            data = request.httprequest.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        
        if data.get('object') == 'page':
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    field = change.get('field')
                    
                    if field == 'leadgen':
                        leadgen_value = change.get('value', {})
                        lead_id = leadgen_value.get('leadgen_id')
                        # Extract Meta tracking info from leadgen webhook
                        meta_tracking = {
                            'ad_id': leadgen_value.get('ad_id'),
                            'adset_id': leadgen_value.get('adset_id'),
                            'campaign_id': leadgen_value.get('campaign_id'),
                            'form_id': leadgen_value.get('form_id'),
                            'page_id': leadgen_value.get('page_id'),
                            'created_time': leadgen_value.get('created_time'),
                        }
                        self._process_lead(lead_id, meta_tracking)
                    
                    elif field == 'messages':
                        # Handle incoming messages from Meta
                        self._process_message(change.get('value', {}))
        
        return "success"

    def _process_lead(self, lead_id, meta_tracking=None):
        """
        Process a Facebook lead and create a CRM lead in Odoo.
        
        :param lead_id: Facebook lead ID
        :param meta_tracking: dict with Meta tracking info (ad_id, campaign_id, etc.)
        """
        meta_tracking = meta_tracking or {}
        
        # Gọi Meta Graph API để lấy chi tiết thông tin Lead
        url = f"https://graph.facebook.com/v24.0/{lead_id}?access_token={self.ACCESS_TOKEN}"
        response = requests.get(url).json()
        
        # Bóc tách dữ liệu từ mảng field_data của Meta
        lead_data = {item['name']: item['values'][0] for item in response.get('field_data', [])}
        
        # Parse created_time if present
        meta_created_time = False
        if meta_tracking.get('created_time'):
            try:
                meta_created_time = datetime.fromtimestamp(int(meta_tracking['created_time']))
            except (ValueError, TypeError):
                _logger.warning(f"Could not parse created_time: {meta_tracking.get('created_time')}")

        # Prepare lead values with Meta tracking data
        lead_vals = {
            'name': f"Lead từ FB: {lead_data.get('full_name', 'Khách hàng mới')}",
            'contact_name': lead_data.get('full_name'),
            'email_from': lead_data.get('email'),
            'phone': lead_data.get('phone_number'),
            'description': f"Facebook Lead ID: {lead_id}",
            'medium_id': request.env.ref('utm.utm_medium_facebook', raise_if_not_found=False).id if request.env.ref('utm.utm_medium_facebook', raise_if_not_found=False) else False,
            # Meta tracking fields
            'meta_lead_id': str(lead_id),
            'meta_ad_id': meta_tracking.get('ad_id') or '',
            'meta_adset_id': meta_tracking.get('adset_id') or '',
            'meta_campaign_id': meta_tracking.get('campaign_id') or '',
            'meta_form_id': meta_tracking.get('form_id') or '',
            'meta_page_id': meta_tracking.get('page_id') or '',
            'meta_created_time': meta_created_time,
        }
        
        # Also try to extract fbclid from additional data if available
        fbclid = response.get('retailer_item_id') or lead_data.get('fbclid')
        if fbclid:
            lead_vals['meta_fbclid'] = fbclid

        # Tạo Lead trong Odoo CRM
        crm_lead = request.env['crm.lead'].sudo().create(lead_vals)
        _logger.info(f"Đã tạo Lead thành công cho ID: {lead_id}, CRM Lead ID: {crm_lead.id}")
        
        return crm_lead

    def _process_message(self, message_data):
        """
        Process incoming message from Meta webhook.
        
        Expected message_data structure:
        {
            "sender": {"id": "12334"},
            "recipient": {"id": "23245"},
            "timestamp": "1527459824",
            "message": {
                "mid": "test_message_id",
                "text": "test_message",
                "commands": [{"name": "command123"}, {"name": "command456"}]
            }
        }
        """
        try:
            # Store the message in Odoo using meta.message model
            meta_message = request.env['meta.message'].sudo().create_from_webhook(message_data)
            _logger.info(f"Successfully processed Meta message, record ID: {meta_message.id}")
        except Exception as e:
            _logger.error(f"Failed to process Meta message: {str(e)}")