import hashlib
import requests
import time
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Meta tracking fields - stored when lead is created from Facebook
    meta_lead_id = fields.Char(
        string='Meta Lead ID',
        help='Facebook Lead ID from leadgen webhook',
        index=True,
    )
    meta_ad_id = fields.Char(
        string='Meta Ad ID',
        help='Facebook Ad ID (ad_id) that generated this lead',
        index=True,
    )
    meta_adset_id = fields.Char(
        string='Meta Adset ID',
        help='Facebook Adset ID (adset_id)',
    )
    meta_campaign_id = fields.Char(
        string='Meta Campaign ID',
        help='Facebook Campaign ID (campaign_id)',
    )
    meta_form_id = fields.Char(
        string='Meta Form ID',
        help='Facebook Lead Form ID (form_id)',
    )
    meta_fbclid = fields.Char(
        string='Facebook Click ID (fbclid)',
        help='Facebook Click ID for tracking',
        index=True,
    )
    meta_fbc = fields.Char(
        string='Meta fbc Cookie',
        help='Facebook browser cookie parameter (_fbc)',
    )
    meta_fbp = fields.Char(
        string='Meta fbp Cookie',
        help='Facebook browser ID cookie parameter (_fbp)',
    )
    meta_page_id = fields.Char(
        string='Meta Page ID',
        help='Facebook Page ID that received the lead',
    )
    meta_created_time = fields.Datetime(
        string='Meta Created Time',
        help='Timestamp when lead was created on Facebook',
    )
    meta_event_sent = fields.Boolean(
        string='QualifiedLead Event Sent',
        default=False,
        help='Indicates if QualifiedLead event was sent to Meta CAPI',
    )

    def action_set_won_rainbowman(self):
        """
        Override the won action to send QualifiedLead event to Meta CAPI
        when opportunity is marked as won.
        """
        res = super(CrmLead, self).action_set_won_rainbowman()
        for lead in self:
            if lead.meta_lead_id or lead.meta_ad_id or lead.meta_fbclid:
                lead._send_qualified_lead_to_meta_capi()
        return res

    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        """
        Override convert_opportunity to send QualifiedLead event to Meta CAPI.
        This is called when a lead is converted to an opportunity.
        """
        res = super(CrmLead, self).convert_opportunity(partner_id, user_ids=user_ids, team_id=team_id)
        
        for lead in self:
            # Only send if lead has Meta tracking data and event hasn't been sent
            if not lead.meta_event_sent and (lead.meta_lead_id or lead.meta_ad_id or lead.meta_fbclid):
                lead._send_qualified_lead_to_meta_capi()
        
        return res

    def _send_qualified_lead_to_meta_capi(self):
        """
        Send QualifiedLead event to Meta Conversions API.
        This event indicates that a lead has been qualified (converted to opportunity).
        """
        _logger.info("=== META CAPI: Sending QualifiedLead for lead %s ===" % self.name)
        
        # Configuration (Should be stored in System Parameters in production)
        ICP = self.env['ir.config_parameter'].sudo()
        ACCESS_TOKEN = ICP.get_param('meta.access_token', 'EAAKWCZAoKZBZB0BQWVauSCt2bZCAkZCeoM6ZAsBPLZA5kWVmWkkPdeHIgRZCchXfXd7W2Md2xCo67Rz3rd3aJ0kkPpGGAXaFdYGaKcXucZBr7JXiHFqBkQdisvJoKvj33o5g28GylyZC9q9cXcrtA6Oh9kO1hY8OdOckaACIAJnvT3c3cF5iUYeIs5ZBGrmhfoxj9ilL1KJAva7nHZBZBkeqqEzZCnEjVpuRUBgU38egZA0')
        PIXEL_ID = ICP.get_param('meta.pixel_id', '1572264680686179')
        TEST_CODE = ICP.get_param('meta.test_event_code', 'TEST42631')

        # Hash customer data
        email = self.email_from or ""
        phone = self.phone or self.mobile or ""
        name = self.contact_name or self.partner_name or ""
        
        # Normalize and hash data according to Meta requirements
        hashed_email = hashlib.sha256(email.lower().strip().encode()).hexdigest() if email else None
        hashed_phone = hashlib.sha256(self._normalize_phone(phone).encode()).hexdigest() if phone else None
        
        # Split name into first and last name
        name_parts = name.strip().split(' ', 1) if name else ['', '']
        first_name = name_parts[0].lower() if name_parts else ''
        last_name = name_parts[1].lower() if len(name_parts) > 1 else ''
        hashed_fn = hashlib.sha256(first_name.encode()).hexdigest() if first_name else None
        hashed_ln = hashlib.sha256(last_name.encode()).hexdigest() if last_name else None

        # Build user_data with available hashed information
        user_data = {}
        if hashed_email:
            user_data['em'] = [hashed_email]
        if hashed_phone:
            user_data['ph'] = [hashed_phone]
        if hashed_fn:
            user_data['fn'] = hashed_fn
        if hashed_ln:
            user_data['ln'] = hashed_ln
        
        # Add click IDs for attribution
        if self.meta_fbc:
            user_data['fbc'] = self.meta_fbc
        if self.meta_fbp:
            user_data['fbp'] = self.meta_fbp
        if self.meta_fbclid:
            # If we have fbclid but not fbc, construct fbc format
            if not self.meta_fbc:
                # fbc format: fb.1.{timestamp}.{fbclid}
                user_data['fbc'] = f"fb.1.{int(time.time())}.{self.meta_fbclid}"

        # Add lead_id for better attribution
        if self.meta_lead_id:
            user_data['lead_id'] = self.meta_lead_id

        # Build custom_data with campaign info
        custom_data = {
            'lead_event_source': 'odoo_crm',
            'content_category': 'CRM Lead',
            'status': 'qualified',
        }
        
        # Add Meta campaign tracking data
        if self.meta_ad_id:
            custom_data['ad_id'] = self.meta_ad_id
        if self.meta_adset_id:
            custom_data['adset_id'] = self.meta_adset_id
        if self.meta_campaign_id:
            custom_data['campaign_id'] = self.meta_campaign_id
        if self.meta_form_id:
            custom_data['form_id'] = self.meta_form_id
        
        # Add lead value if expected revenue is set
        if self.expected_revenue:
            custom_data['value'] = self.expected_revenue
            custom_data['currency'] = self.company_currency.name if self.company_currency else 'USD'

        # Construct the event payload
        event_data = {
            "event_name": "Lead",  # Standard Meta event - use QualifiedLead in custom_data
            "event_time": int(time.time()),
            "action_source": "system_generated",
            "event_source_url": self.website or "",
            "user_data": user_data,
            "custom_data": {
                **custom_data,
                "event_type": "QualifiedLead",  # Custom qualifier
                "lead_type": "opportunity",
            },
        }

        # Add event_id for deduplication
        event_data["event_id"] = f"qualified_lead_{self.id}_{int(time.time())}"

        payload = {
            "data": [event_data],
        }
        
        # Add test event code if configured
        if TEST_CODE:
            payload["test_event_code"] = TEST_CODE

        url = f"https://graph.facebook.com/v24.0/{PIXEL_ID}/events?access_token={ACCESS_TOKEN}"

        _logger.info("=== META CAPI: Sending QualifiedLead payload to %s ===" % url[:50])
        _logger.info("=== META CAPI: Payload = %s ===" % payload)

        # Create outgoing event record
        outgoing_event = self.env['meta.outgoing.event'].sudo().create_from_lead(
            lead=self,
            event_name='QualifiedLead',
            payload=payload,
            pixel_id=PIXEL_ID
        )

        try:
            response = requests.post(url, json=payload, timeout=30)
            _logger.info("=== META CAPI: Response status=%s, body=%s ===" % (response.status_code, response.text))

            if response.status_code == 200:
                outgoing_event.mark_success(response.status_code, response.text)
                self.meta_event_sent = True
            else:
                outgoing_event.mark_failed(
                    error_message=f"HTTP {response.status_code}",
                    response_status=response.status_code,
                    response_body=response.text
                )
        except Exception as e:
            _logger.error("=== META CAPI: Error sending QualifiedLead = %s ===" % str(e))
            outgoing_event.mark_failed(error_message=str(e))

    def _normalize_phone(self, phone):
        """
        Normalize phone number by removing non-digit characters.
        Meta requires phone to be hashed in E.164 format.
        """
        if not phone:
            return ''
        # Remove all non-digit characters except leading +
        import re
        normalized = re.sub(r'[^\d+]', '', phone)
        # Remove the + if present (Meta expects just digits)
        normalized = normalized.lstrip('+')
        return normalized
