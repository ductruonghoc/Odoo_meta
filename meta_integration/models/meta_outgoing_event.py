import json
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MetaOutgoingEvent(models.Model):
    _name = 'meta.outgoing.event'
    _description = 'Meta Outgoing Events (CAPI)'
    _order = 'event_time desc, id desc'

    # Event identifiers
    name = fields.Char(string='Event Name', required=True, index=True)
    event_time = fields.Datetime(string='Event Time', index=True)
    
    # Related records
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', index=True, ondelete='set null')
    lead_id = fields.Many2one('crm.lead', string='CRM Lead', index=True, ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Customer', index=True, ondelete='set null')
    
    # Event data
    pixel_id = fields.Char(string='Pixel ID')
    action_source = fields.Char(string='Action Source')
    currency = fields.Char(string='Currency')
    value = fields.Float(string='Value', digits=(16, 2))
    
    # Hashed user data
    hashed_email = fields.Char(string='Hashed Email')
    
    # Product contents (JSON)
    contents = fields.Text(string='Contents', help='JSON array of product items')
    
    # Meta tracking IDs
    meta_ad_id = fields.Char(string='Ad ID', help='Facebook Ad ID')
    meta_adset_id = fields.Char(string='Adset ID', help='Facebook Adset ID')
    meta_campaign_id = fields.Char(string='Campaign ID', help='Facebook Campaign ID')
    meta_form_id = fields.Char(string='Form ID', help='Facebook Lead Form ID')
    meta_lead_id = fields.Char(string='Lead ID', help='Facebook Lead ID')
    meta_fbclid = fields.Char(string='Facebook Click ID', help='Facebook Click ID (fbclid)')
    
    # Full payload for debugging
    payload = fields.Text(string='Payload', help='Full JSON payload sent to Meta')
    
    # Response data
    response_status = fields.Integer(string='Response Status')
    response_body = fields.Text(string='Response Body')
    
    # Processing status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='pending', index=True)
    
    error_message = fields.Text(string='Error Message')

    @api.model
    def create_from_sale_order(self, order, event_name, payload, pixel_id=None):
        """
        Create an outgoing event record from a sale order.
        
        :param order: sale.order record
        :param event_name: name of the event (e.g., 'Purchase')
        :param payload: dict payload sent to Meta
        :param pixel_id: Meta Pixel ID
        :return: created meta.outgoing.event record
        """
        from datetime import datetime
        
        try:
            event_data = payload.get('data', [{}])[0] if payload.get('data') else {}
            custom_data = event_data.get('custom_data', {})
            user_data = event_data.get('user_data', {})
            
            vals = {
                'name': event_name,
                'event_time': datetime.now(),
                'sale_order_id': order.id,
                'partner_id': order.partner_id.id if order.partner_id else False,
                'pixel_id': pixel_id or '',
                'action_source': event_data.get('action_source', ''),
                'currency': custom_data.get('currency', ''),
                'value': custom_data.get('value', 0.0),
                'contents': json.dumps(custom_data.get('contents', []), indent=2, ensure_ascii=False),
                'payload': json.dumps(payload, indent=4, ensure_ascii=False),
                'state': 'pending',
            }
            
            record = self.create(vals)
            _logger.info(f"Created meta.outgoing.event record ID={record.id}, event={event_name}")
            return record
            
        except Exception as e:
            _logger.error(f"Failed to create meta.outgoing.event: {str(e)}")
            raise

    @api.model
    def create_from_lead(self, lead, event_name, payload, pixel_id=None):
        """
        Create an outgoing event record from a CRM lead.
        
        :param lead: crm.lead record
        :param event_name: name of the event (e.g., 'QualifiedLead')
        :param payload: dict payload sent to Meta
        :param pixel_id: Meta Pixel ID
        :return: created meta.outgoing.event record
        """
        from datetime import datetime
        
        try:
            event_data = payload.get('data', [{}])[0] if payload.get('data') else {}
            custom_data = event_data.get('custom_data', {})
            user_data = event_data.get('user_data', {})
            
            vals = {
                'name': event_name,
                'event_time': datetime.now(),
                'lead_id': lead.id,
                'partner_id': lead.partner_id.id if lead.partner_id else False,
                'pixel_id': pixel_id or '',
                'action_source': event_data.get('action_source', ''),
                'currency': custom_data.get('currency', ''),
                'value': custom_data.get('value', 0.0),
                'hashed_email': user_data.get('em', [''])[0] if user_data.get('em') else '',
                'meta_ad_id': lead.meta_ad_id or custom_data.get('ad_id', ''),
                'meta_adset_id': lead.meta_adset_id or custom_data.get('adset_id', ''),
                'meta_campaign_id': lead.meta_campaign_id or custom_data.get('campaign_id', ''),
                'meta_form_id': lead.meta_form_id or custom_data.get('form_id', ''),
                'meta_lead_id': lead.meta_lead_id or '',
                'meta_fbclid': lead.meta_fbclid or '',
                'payload': json.dumps(payload, indent=4, ensure_ascii=False),
                'state': 'pending',
            }
            
            record = self.create(vals)
            _logger.info(f"Created meta.outgoing.event record ID={record.id}, event={event_name}, lead={lead.name}")
            return record
            
        except Exception as e:
            _logger.error(f"Failed to create meta.outgoing.event from lead: {str(e)}")
            raise

    def mark_success(self, response_status, response_body):
        """Mark the event as successfully sent."""
        self.write({
            'state': 'success',
            'response_status': response_status,
            'response_body': response_body,
        })

    def mark_failed(self, error_message, response_status=None, response_body=None):
        """Mark the event as failed."""
        vals = {
            'state': 'failed',
            'error_message': error_message,
        }
        if response_status:
            vals['response_status'] = response_status
        if response_body:
            vals['response_body'] = response_body
        self.write(vals)
