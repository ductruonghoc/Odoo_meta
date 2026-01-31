# -*- coding: utf-8 -*-

import json
import logging
import requests

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# External server base URL - should be configurable via system parameters
EXTERNAL_SERVER_URL = "https://easter-unprofiteering-tristin.ngrok-free.dev/api/v1"


class AdsSubscriptionController(http.Controller):

    def _get_server_url(self):
        """Get the external server URL from system parameters."""
        return request.env['ir.config_parameter'].sudo().get_param(
            'ads_sync.server_url', default=EXTERNAL_SERVER_URL
        )

    def _get_client_ip(self):
        """Get the client IP address from the request."""
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.httprequest.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in the list
            return forwarded_for.split(',')[0].strip()
        return request.httprequest.remote_addr

    # ==========================================
    # Meta Webhook Endpoints (/webhook/meta)
    # ==========================================

    @http.route('/webhooks/meta', type='http', auth='public', methods=['GET'], csrf=False)
    def meta_webhook_verify(self, **kwargs):
        """
        Handle Meta webhook verification requests (GET).
        Meta sends a GET request to verify the webhook URL during setup.
        
        Expected parameters:
        - hub.mode: Should be 'subscribe'
        - hub.verify_token: The verification token you set in Meta
        - hub.challenge: The challenge string to return
        """
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')
        
        _logger.info(f"Meta webhook verification: mode={mode}, token={token}")
        
        # Get the verify token from system parameters
        verify_token = request.env['ir.config_parameter'].sudo().get_param(
            'ads_sync.meta_webhook_verify_token', default=''
        )
        
        if mode == 'subscribe' and token and token == verify_token:
            _logger.info("Meta webhook verified successfully")
            return Response(challenge, status=200, content_type='text/plain')
        
        _logger.warning("Meta webhook verification failed")
        return Response('Verification failed', status=403)

    @http.route('/webhooks/meta', type='http', auth='public', methods=['POST'], csrf=False)
    def meta_webhook_receive(self, **kwargs):
        try:
            # Use httprequest.get_data() instead of jsonrequest
            raw_data = request.httprequest.get_data(as_text=True)
            
            if not raw_data:
                return Response(json.dumps({'status': 'error'}), status=400, content_type='application/json')
            
            data = json.loads(raw_data)
            
            # Use request.httprequest.remote_addr if _get_client_ip() isn't defined
            source_ip = getattr(self, '_get_client_ip', lambda: request.httprequest.remote_addr)()
            
            _logger.info(f"Meta Webhook received from {source_ip}")

            # Process and Store in ads.meta.webhook.event
            event = request.env['ads.meta.webhook.event'].sudo().create_from_webhook(
                payload=data,
                source_ip=source_ip
            )
            
            # Route to corresponding Odoo models based on event type
            routed_records = self._route_webhook_to_models(data, event)
            
            return Response(
                json.dumps({
                    'status': 'ok', 
                    'event_id': event.id,
                    'routed_records': routed_records
                }),
                status=200, 
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.exception(f"Error processing Meta webhook: {str(e)}")
            # We return 200 even on error to prevent Meta from retrying/disabling the webhook
            return Response(json.dumps({'status': 'error'}), status=200, content_type='application/json')

    def _route_webhook_to_models(self, data, webhook_event):
        """
        Route webhook data to corresponding Odoo models based on event field type.
        
        Supported events:
        1. affiliation - Creates/updates CRM Lead with affiliation info
        2. attire - Creates/updates Sale Order note with attire info  
        3. awards - Creates/updates CRM Lead with awards info
        4. birthday - Updates CRM Lead with birthday info
        5. business_integrity - Creates CRM Lead with business integrity issues
        6. category - Updates CRM Lead with category info
        7. current_location - Updates Partner with location info
        8. company_overview - Updates Partner with company description
        9. culinary_team - Creates CRM Lead with team info
        10. email - Updates Partner with email address
        11. description - Creates CRM Lead with general description
        12. founded - Updates Partner with founding date
        13. feed - Creates CRM Lead with social media post info
        14. general_manager - Creates CRM Lead with management info
        15. hometown - Updates Partner with hometown/location info
        16. group_feed - Creates CRM Lead with group post/comment info
        17. hours - Updates Partner with business hours
        18. leadgen - Creates CRM Lead from ad lead generation
        19. invoice_access_invoice_draft_change - Creates Sale Order from invoice changes
        20. inbox_labels - Creates CRM Lead from inbox label actions
        21. marketing_message_clicks - Creates CRM Lead from marketing message interactions
        22. location - Updates Partner with location information
        23. live_videos - Creates CRM Lead from live video events
        24. marketing_message_deliveries - Creates CRM Lead from marketing message deliveries
        25. marketing_message_delivery_failed - Creates CRM Lead from failed message deliveries
        26. marketing_messages_subscriber_upload_status - Creates CRM Lead from subscriber upload status
        27. marketing_message_reads - Creates CRM Lead from marketing message read events
        28. marketing_message_echoes - Creates CRM Lead from marketing message echo events
        29. message_context - Creates CRM Lead from message context and purchase detections
        30. mention - Creates CRM Lead from social media mentions
        31. members - Updates Partner with member information
        32. message_edits - Creates CRM Lead from message edit events
        33. message_echoes - Creates CRM Lead from message echo events  
        34. message_deliveries - Creates CRM Lead from message delivery confirmations
        35. website - Updates Partner with website information
        36. videos - Creates CRM Lead from video content events
        37. send_cart - Creates Sale Order from shopping cart events
        38. ratings - Creates CRM Lead from customer ratings and reviews
        39. public_transit - Updates Partner with public transit information
        40. products - Updates Partner with product information
        41. product_review - Creates CRM Lead from product review events
        42. price_range - Updates Partner with price range information
        43. picture - Updates Partner with picture information
        44. phone - Updates Partner with phone information
        45. personal_interests - Updates Partner with personal interests information
        46. personal_info - Updates Partner with personal information
        47. payment_options - Updates Partner with payment options information
        48. parking - Updates Partner with parking information
        49. page_upcoming_change - Creates CRM Lead from page upcoming change notifications
        50. page_change_proposal - Creates CRM Lead from page change proposal events
        51. name - Updates Partner with name information
        52. mission - Updates Partner with mission information
        53. messaging_referrals - Creates CRM Lead from messaging referral events
        54. messaging_postbacks - Creates CRM Lead from messaging postback events
        55. messaging_policy_enforcement - Creates CRM Lead from messaging policy enforcement events
        56. message_reactions - Creates CRM Lead from message reaction events
        57. message_reads - Creates CRM Lead from message read events
        58. message_template_status_update - Creates CRM Lead from message template status updates
        59. messages - Creates CRM Lead from general message events
        60. messaging_account_linking - Creates CRM Lead from account linking events
        61. messaging_customer_information - Creates CRM Lead from customer information collection
        62. messaging_handovers - Creates CRM Lead from conversation handover events
        63. messaging_in_thread_lead_form_submit - Creates CRM Lead from in-thread lead form submissions
        64. messaging_optins - Creates CRM Lead from messaging opt-in events
        
        Sample event format:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "attire"}]}], "object": "page"}
        
        :param data: dict - The webhook payload
        :param webhook_event: recordset - The created ads.meta.webhook.event record
        :return: dict - Summary of routed records
        """
        routed = {}
        
        try:
            entries = data.get('entry', [])
            object_type = data.get('object', '')
            
            for entry in entries:
                entry_id = entry.get('id', '')
                entry_time = entry.get('time', 0)
                changes = entry.get('changes', [])
                
                for change in changes:
                    field = change.get('field', '')
                    # Value may not exist in the payload - handle gracefully
                    value = change.get('value') if isinstance(change.get('value'), dict) else {}
                    
                    _logger.info(f"Processing webhook field '{field}' for entry {entry_id}")
                    
                    if field == 'affiliation':
                        # Route to CRM Lead - affiliation represents business/partner relationship
                        record = self._process_affiliation_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                    
                    elif field == 'attire':
                        # Route to Sale Order - attire represents product/item preferences
                        record = self._process_attire_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('sale.order', []).append(record.id)
                    
                    elif field == 'awards':
                        # Route to CRM Lead - awards as qualification/achievement info
                        record = self._process_awards_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'birthday':
                        # Route to CRM Lead - birthday represents customer birth date
                        record = self._process_birthday_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'business_integrity':
                        # Route to CRM Lead - business integrity issues and restrictions
                        record = self._process_business_integrity_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'category':
                        # Route to CRM Lead - category represents business/page category
                        record = self._process_category_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'current_location':
                        # Route to Partner - location represents contact/business location
                        record = self._process_current_location_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'company_overview':
                        # Route to Partner - company overview represents business description
                        record = self._process_company_overview_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'culinary_team':
                        # Route to CRM Lead - culinary team represents business team info
                        record = self._process_culinary_team_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'email':
                        # Route to Partner - email represents contact email updates
                        record = self._process_email_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'description':
                        # Route to CRM Lead - description represents general business description
                        record = self._process_description_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'founded':
                        # Route to Partner - founded represents business founding date
                        record = self._process_founded_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'feed':
                        # Route to CRM Lead - feed represents social media posts/activity
                        record = self._process_feed_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'general_manager':
                        # Route to CRM Lead - general_manager represents management info
                        record = self._process_general_manager_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'hometown':
                        # Route to Partner - hometown represents location/personal info
                        record = self._process_hometown_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'group_feed':
                        # Route to CRM Lead - group_feed represents group posts/comments
                        record = self._process_group_feed_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'hours':
                        # Route to Partner - hours represents business operating hours
                        record = self._process_hours_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'leadgen':
                        # Route to CRM Lead - leadgen represents ad lead generation
                        record = self._process_leadgen_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'invoice_access_invoice_draft_change':
                        # Route to Sale Order - invoice changes represent sales/order updates
                        record = self._process_invoice_access_invoice_draft_change_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('sale.order', []).append(record.id)
                            
                    elif field == 'inbox_labels':
                        # Route to CRM Lead - inbox_labels represents customer communication
                        record = self._process_inbox_labels_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'marketing_message_clicks':
                        # Route to CRM Lead - marketing_message_clicks represents customer engagement
                        record = self._process_marketing_message_clicks_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'location':
                        # Route to Partner - location represents business/contact location
                        record = self._process_location_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'live_videos':
                        # Route to CRM Lead - live_videos represents live streaming activity
                        record = self._process_live_videos_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'marketing_message_deliveries':
                        # Route to CRM Lead - marketing_message_deliveries represents message delivery tracking
                        record = self._process_marketing_message_deliveries_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'marketing_message_delivery_failed':
                        # Route to CRM Lead - marketing_message_delivery_failed represents delivery failures
                        record = self._process_marketing_message_delivery_failed_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'marketing_messages_subscriber_upload_status':
                        # Route to CRM Lead - marketing_messages_subscriber_upload_status represents audience upload status
                        record = self._process_marketing_messages_subscriber_upload_status_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'marketing_message_reads':
                        # Route to CRM Lead - marketing_message_reads represents message read tracking
                        record = self._process_marketing_message_reads_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'marketing_message_echoes':
                        # Route to CRM Lead - marketing_message_echoes represents automated message responses
                        record = self._process_marketing_message_echoes_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'message_context':
                        # Route to CRM Lead - message_context represents message context and purchase detections
                        record = self._process_message_context_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'mention':
                        # Route to CRM Lead - mention represents social media mentions
                        record = self._process_mention_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'members':
                        # Route to Partner - members represents group/page member information
                        record = self._process_members_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'message_edits':
                        # Route to CRM Lead - message_edits represents message editing activity
                        record = self._process_message_edits_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'message_echoes':
                        # Route to CRM Lead - message_echoes represents automated message responses
                        record = self._process_message_echoes_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'message_deliveries':
                        # Route to CRM Lead - message_deliveries represents message delivery confirmations
                        record = self._process_message_deliveries_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'website':
                        # Route to Partner - website represents business website information
                        record = self._process_website_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'videos':
                        # Route to CRM Lead - videos represents video content activity
                        record = self._process_videos_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'send_cart':
                        # Route to Sale Order - send_cart represents shopping cart/order events
                        record = self._process_send_cart_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('sale.order', []).append(record.id)
                            
                    elif field == 'ratings':
                        # Route to CRM Lead - ratings represents customer ratings and reviews
                        record = self._process_ratings_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'public_transit':
                        # Route to Partner - public_transit represents business transit information
                        record = self._process_public_transit_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'products':
                        # Route to Partner - products represents business product information
                        record = self._process_products_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'product_review':
                        # Route to CRM Lead - product_review represents product review events
                        record = self._process_product_review_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'price_range':
                        # Route to Partner - price_range represents business pricing information
                        record = self._process_price_range_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'picture':
                        # Route to Partner - picture represents business image information
                        record = self._process_picture_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'phone':
                        # Route to Partner - phone represents business phone information
                        record = self._process_phone_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'personal_interests':
                        # Route to Partner - personal_interests represents business/personal interests information
                        record = self._process_personal_interests_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'personal_info':
                        # Route to Partner - personal_info represents business personal information
                        record = self._process_personal_info_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'payment_options':
                        # Route to Partner - payment_options represents business payment methods
                        record = self._process_payment_options_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'parking':
                        # Route to Partner - parking represents business parking information
                        record = self._process_parking_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'page_upcoming_change':
                        # Route to CRM Lead - page_upcoming_change represents page change notifications
                        record = self._process_page_upcoming_change_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'page_change_proposal':
                        # Route to CRM Lead - page_change_proposal represents page change proposal events
                        record = self._process_page_change_proposal_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'name':
                        # Route to Partner - name represents business name information
                        record = self._process_name_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'mission':
                        # Route to Partner - mission represents business mission information
                        record = self._process_mission_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('res.partner', []).append(record.id)
                            
                    elif field == 'messaging_referrals':
                        # Route to CRM Lead - messaging_referrals represents customer referral interactions
                        record = self._process_messaging_referrals_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_postbacks':
                        # Route to CRM Lead - messaging_postbacks represents customer postback interactions
                        record = self._process_messaging_postbacks_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_policy_enforcement':
                        # Route to CRM Lead - messaging_policy_enforcement represents policy violation notifications
                        record = self._process_messaging_policy_enforcement_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'message_reactions':
                        # Route to CRM Lead - message_reactions represents customer reactions to messages
                        record = self._process_message_reactions_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'message_reads':
                        # Route to CRM Lead - message_reads represents message read confirmations
                        record = self._process_message_reads_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'message_template_status_update':
                        # Route to CRM Lead - message_template_status_update represents template status changes
                        record = self._process_message_template_status_update_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messages':
                        # Route to CRM Lead - messages represents general message events
                        record = self._process_messages_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_account_linking':
                        # Route to CRM Lead - messaging_account_linking represents account linking events
                        record = self._process_messaging_account_linking_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_customer_information':
                        # Route to CRM Lead - messaging_customer_information represents customer information collection
                        record = self._process_messaging_customer_information_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_handovers':
                        # Route to CRM Lead - messaging_handovers represents conversation handover events
                        record = self._process_messaging_handovers_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_in_thread_lead_form_submit':
                        # Route to CRM Lead - messaging_in_thread_lead_form_submit represents lead form submissions
                        record = self._process_messaging_in_thread_lead_form_submit_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
                            
                    elif field == 'messaging_optins':
                        # Route to CRM Lead - messaging_optins represents messaging opt-in events
                        record = self._process_messaging_optins_event(entry, value, webhook_event, object_type)
                        if record:
                            routed.setdefault('crm.lead', []).append(record.id)
            # Update webhook event state if records were routed
            if routed:
                webhook_event.sudo().write({
                    'processing_notes': f"Routed to: {json.dumps(routed)}",
                    'state': 'processed'
                })
                            
        except Exception as e:
            _logger.exception(f"Error routing webhook to models: {str(e)}")
            webhook_event.sudo().write({
                'processing_notes': f"Routing error: {str(e)}",
                'state': 'error'
            })
        
        return routed

    def _process_affiliation_event(self, entry, value, webhook_event, object_type=''):
        """
        Process affiliation event - Create/Update CRM Lead.
        Affiliation typically represents business partnerships or organizational relationships.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "affiliation"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "affiliation",
            "value": {
                "name": "Partner Name",
                "email": "partner@example.com",
                "phone": "+1234567890",
                "organization": "Organization Name",
                "affiliation_type": "partner|reseller|affiliate"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract data from value (may be empty dict)
            email = value.get('email', '') if value else ''
            phone = value.get('phone', '') if value else ''
            name = value.get('name') if value and value.get('name') else f"Meta Affiliation Lead - {entry_id}"
            organization = value.get('organization', '') if value else ''
            affiliation_type = value.get('affiliation_type', 'affiliate') if value else 'affiliate'
            
            # Check for existing lead by email or Meta entry ID
            existing_lead = False
            if email:
                existing_lead = CrmLead.search([('email_from', '=', email)], limit=1)
            
            lead_vals = {
                'name': f"[{affiliation_type.upper()}] {name}",
                'email_from': email or False,
                'phone': phone,
                'partner_name': organization or name,
                'description': f"Affiliation Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Type: {affiliation_type}\n"
                              f"Organization: {organization}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
            }
            
            if existing_lead:
                existing_lead.write(lead_vals)
                _logger.info(f"Updated CRM Lead {existing_lead.id} from affiliation event")
                return existing_lead
            else:
                lead = CrmLead.create(lead_vals)
                _logger.info(f"Created CRM Lead {lead.id} from affiliation event")
                return lead
                
        except Exception as e:
            _logger.exception(f"Error processing affiliation event: {str(e)}")
            return False

    def _process_attire_event(self, entry, value, webhook_event, object_type=''):
        """
        Process attire event - Create Sale Order (Quote).
        Attire typically represents product/fashion preferences and purchase intent.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "attire"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "attire",
            "value": {
                "customer_email": "customer@example.com",
                "customer_name": "Customer Name",
                "items": [
                    {"product_code": "SHIRT001", "quantity": 2, "size": "M"},
                    {"product_code": "PANTS001", "quantity": 1, "size": "L"}
                ],
                "style_preference": "casual|formal|sporty",
                "notes": "Additional notes"
            }
        }
        """
        try:
            SaleOrder = request.env['sale.order'].sudo()
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract customer data (may be empty dict)
            customer_email = value.get('customer_email', '') if value else ''
            customer_name = value.get('customer_name') if value and value.get('customer_name') else f"Meta Attire Customer - {entry_id}"
            items = value.get('items', []) if value else []
            style_preference = value.get('style_preference', '') if value else ''
            notes = value.get('notes', '') if value else ''
            
            # Find or create partner
            partner = False
            if customer_email:
                partner = Partner.search([('email', '=', customer_email)], limit=1)
            
            if not partner:
                # Use a default partner name if no customer info provided
                partner = Partner.create({
                    'name': customer_name,
                    'email': customer_email or False,
                    'comment': f"Created from Meta Attire webhook event (Entry ID: {entry_id})",
                })
            
            # Create Sale Order
            order_vals = {
                'partner_id': partner.id,
                'note': f"Attire Event from Meta\n"
                        f"Object Type: {object_type}\n"
                        f"Entry ID: {entry_id}\n"
                        f"Entry Time: {entry_time}\n"
                        f"Style Preference: {style_preference}\n"
                        f"Notes: {notes}\n"
                        f"Webhook Event ID: {webhook_event.id}\n"
                        f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'origin': f"Meta Webhook - {entry_id}",
            }
            
            order = SaleOrder.create(order_vals)
            _logger.info(f"Created Sale Order {order.name} from attire event (entry_id: {entry_id})")
            
            # Add order lines if items provided
            if items:
                Product = request.env['product.product'].sudo()
                for item in items:
                    product_code = item.get('product_code', '')
                    quantity = item.get('quantity', 1)
                    
                    # Find product by default_code
                    product = Product.search([('default_code', '=', product_code)], limit=1)
                    if not product:
                        # Try to find any product or skip
                        product = Product.search([], limit=1)
                    
                    if product:
                        request.env['sale.order.line'].sudo().create({
                            'order_id': order.id,
                            'product_id': product.id,
                            'product_uom_qty': quantity,
                            'name': f"{product.name} - Size: {item.get('size', 'N/A')}",
                        })
            
            return order
            
        except Exception as e:
            _logger.exception(f"Error processing attire event: {str(e)}")
            return False

    def _process_awards_event(self, entry, value, webhook_event, object_type=''):
        """
        Process awards event - Create/Update CRM Lead with award/achievement info.
        Awards typically represent customer achievements, qualifications, or recognition.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "awards"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "awards",
            "value": {
                "recipient_name": "Recipient Name",
                "recipient_email": "recipient@example.com",
                "award_name": "Award Title",
                "award_category": "excellence|innovation|loyalty",
                "award_date": "2026-01-22",
                "description": "Award description"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract data from value (may be empty dict)
            recipient_name = value.get('recipient_name') if value and value.get('recipient_name') else f"Meta Award Lead - {entry_id}"
            recipient_email = value.get('recipient_email', '') if value else ''
            award_name = value.get('award_name', 'Meta Award') if value else 'Meta Award'
            award_category = value.get('award_category', 'recognition') if value else 'recognition'
            award_date = value.get('award_date', '') if value else ''
            description = value.get('description', '') if value else ''
            
            # Check for existing lead by email
            existing_lead = False
            if recipient_email:
                existing_lead = CrmLead.search([('email_from', '=', recipient_email)], limit=1)
            
            lead_vals = {
                'name': f"[AWARD: {award_name}] {recipient_name}",
                'email_from': recipient_email or False,
                'contact_name': recipient_name,
                'description': f"Awards Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Award: {award_name}\n"
                              f"Category: {award_category}\n"
                              f"Date: {award_date}\n"
                              f"Description: {description}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '2',  # High priority for award recipients
            }
            
            if existing_lead:
                # Append award info to existing description
                existing_desc = existing_lead.description or ''
                lead_vals['description'] = f"{existing_desc}\n\n--- New Award ---\n{lead_vals['description']}"
                existing_lead.write(lead_vals)
                _logger.info(f"Updated CRM Lead {existing_lead.id} with awards event")
                return existing_lead
            else:
                lead = CrmLead.create(lead_vals)
                _logger.info(f"Created CRM Lead {lead.id} from awards event")
                return lead
                
        except Exception as e:
            _logger.exception(f"Error processing awards event: {str(e)}")
            return False 

    def _process_birthday_event(self, entry, value, webhook_event, object_type=''):
        """
        Process birthday event - Update CRM Lead with birthday info.
        Birthday represents customer birth date for personalized marketing.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "birthday"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "birthday",
            "value": {
                "date": "1990-01-15",
                "customer_email": "customer@example.com",
                "customer_name": "Customer Name"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract data from value (may be empty dict)
            birthday_date = value.get('date', '') if value else ''
            customer_email = value.get('customer_email', '') if value else ''
            customer_name = value.get('customer_name') if value and value.get('customer_name') else f"Meta Birthday Lead - {entry_id}"
            
            # Check for existing lead by email
            existing_lead = False
            if customer_email:
                existing_lead = CrmLead.search([('email_from', '=', customer_email)], limit=1)
            
            lead_vals = {
                'name': f"[BIRTHDAY] {customer_name}",
                'email_from': customer_email or False,
                'contact_name': customer_name,
                'description': f"Birthday Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Birthday: {birthday_date}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
            }
            
            if existing_lead:
                existing_lead.write(lead_vals)
                _logger.info(f"Updated CRM Lead {existing_lead.id} with birthday event")
                return existing_lead
            else:
                lead = CrmLead.create(lead_vals)
                _logger.info(f"Created CRM Lead {lead.id} from birthday event")
                return lead
                
        except Exception as e:
            _logger.exception(f"Error processing birthday event: {str(e)}")
            return False

    def _process_business_integrity_event(self, entry, value, webhook_event, object_type=''):
        """
        Process business integrity event - Create CRM Lead with integrity issues and restrictions.
        Business integrity represents policy violations, restrictions, and appeal status.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "business_integrity"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "business_integrity",
            "value": {
                "timestamp": 1234567890,
                "status": "warning",
                "violations": [
                    {
                        "type": "SPAM",
                        "url": "https://transparency.meta.com/policies/community-standards/spam/",
                        "description": "Có khả năng Trang này cố tạo lượt thích, theo dõi, chia sẻ hoặc lượt xem video theo cách gây hiểu nhầm."
                    }
                ],
                "restrictions": [
                    {
                        "feature": "page_messaging",
                        "description": "This page is restricted from sending messages via Messenger Platform for 1 day",
                        "applied_time": 1234567890,
                        "expiration_time": 1234567890
                    }
                ],
                "action_events": [
                    {
                        "type": "APPEAL",
                        "status": "OPEN",
                        "created_time": 1234567890,
                        "updated_time": 1234567890
                    }
                ]
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract data from value (may be empty dict)
            timestamp = value.get('timestamp', 0) if value else 0
            status = value.get('status', 'unknown') if value else 'unknown'
            violations = value.get('violations', []) if value else []
            restrictions = value.get('restrictions', []) if value else []
            action_events = value.get('action_events', []) if value else []
            
            # Create a summary of violations
            violations_summary = ""
            if violations:
                violations_summary = "\nViolations:\n" + "\n".join([
                    f"- {v.get('type', 'Unknown')}: {v.get('description', '')} (URL: {v.get('url', '')})"
                    for v in violations
                ])
            
            # Create a summary of restrictions
            restrictions_summary = ""
            if restrictions:
                restrictions_summary = "\nRestrictions:\n" + "\n".join([
                    f"- {r.get('feature', 'Unknown')}: {r.get('description', '')} (Applied: {r.get('applied_time', 0)}, Expires: {r.get('expiration_time', 0)})"
                    for r in restrictions
                ])
            
            # Create a summary of action events
            actions_summary = ""
            if action_events:
                actions_summary = "\nAction Events:\n" + "\n".join([
                    f"- {a.get('type', 'Unknown')}: {a.get('status', '')} (Created: {a.get('created_time', 0)}, Updated: {a.get('updated_time', 0)})"
                    for a in action_events
                ])
            
            lead_vals = {
                'name': f"[INTEGRITY: {status.upper()}] Meta Business Integrity - {entry_id}",
                'description': f"Business Integrity Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Status: {status}\n"
                              f"{violations_summary}\n"
                              f"{restrictions_summary}\n"
                              f"{actions_summary}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '3' if status == 'warning' else '2',  # High priority for integrity issues
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from business integrity event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing business integrity event: {str(e)}")
            return False

    def _process_category_event(self, entry, value, webhook_event, object_type=''):
        """
        Process category event - Update CRM Lead with category info.
        Category represents the business/page category classification.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "category"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "category",
            "value": "ACTOR"
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For category, value is typically a string like "ACTOR"
            category = value if isinstance(value, str) else str(value) if value else 'Unknown'
            
            lead_vals = {
                'name': f"[CATEGORY: {category}] Meta Category Update - {entry_id}",
                'description': f"Category Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Category: {category}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from category event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing category event: {str(e)}")
            return False

    def _process_current_location_event(self, entry, value, webhook_event, object_type=''):
        """
        Process current location event - Update Partner with location info.
        Current location represents business or contact location updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "current_location"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "current_location",
            "value": {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "address": "123 Main St, San Francisco, CA",
                "city": "San Francisco",
                "state": "CA",
                "country": "US",
                "zip_code": "94102"
            }
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract location data from value (may be empty dict)
            latitude = value.get('latitude', '') if value else ''
            longitude = value.get('longitude', '') if value else ''
            address = value.get('address', '') if value else ''
            city = value.get('city', '') if value else ''
            state = value.get('state', '') if value else ''
            country = value.get('country', '') if value else ''
            zip_code = value.get('zip_code', '') if value else ''
            
            # Try to find existing partner by entry_id or create new one
            partner_name = f"Meta Location Update - {entry_id}"
            partner_vals = {
                'name': partner_name,
                'street': address,
                'city': city,
                'state_id': False,  # Would need to resolve state
                'country_id': False,  # Would need to resolve country
                'zip': zip_code,
                'comment': f"Location Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Coordinates: {latitude}, {longitude}\n"
                          f"Address: {address}\n"
                          f"City: {city}\n"
                          f"State: {state}\n"
                          f"Country: {country}\n"
                          f"ZIP: {zip_code}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            # Try to find existing partner by name or create new
            existing_partner = Partner.search([('name', '=', partner_name)], limit=1)
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with location event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from current location event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing current location event: {str(e)}")
            return False

    def _process_company_overview_event(self, entry, value, webhook_event, object_type=''):
        """
        Process company overview event - Update Partner with company description.
        Company overview represents business description and information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "company_overview"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "company_overview",
            "value": "Awesome company"
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For company_overview, value is typically a string description
            overview = value if isinstance(value, str) else str(value) if value else 'No overview provided'
            
            partner_name = f"Meta Company Overview - {entry_id}"
            partner_vals = {
                'name': partner_name,
                'is_company': True,
                'comment': f"Company Overview Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Overview: {overview}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            # Try to find existing partner by name or create new
            existing_partner = Partner.search([('name', '=', partner_name)], limit=1)
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with company overview event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from company overview event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing company overview event: {str(e)}")
            return False

    def _process_culinary_team_event(self, entry, value, webhook_event, object_type=''):
        """
        Process culinary team event - Create CRM Lead with team information.
        Culinary team represents restaurant or food business team details.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "culinary_team"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "culinary_team",
            "value": {
                "chef_name": "Chef Mario",
                "specialties": ["Italian", "French"],
                "experience_years": 15,
                "certifications": ["Master Chef", "Culinary Arts Degree"],
                "team_size": 8
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract team data from value (may be empty dict)
            chef_name = value.get('chef_name', '') if value else ''
            specialties = value.get('specialties', []) if value else []
            experience_years = value.get('experience_years', '') if value else ''
            certifications = value.get('certifications', []) if value else []
            team_size = value.get('team_size', '') if value else ''
            
            # Format specialties and certifications
            specialties_str = ', '.join(specialties) if specialties else 'Not specified'
            certifications_str = ', '.join(certifications) if certifications else 'Not specified'
            
            lead_vals = {
                'name': f"[CULINARY TEAM] {chef_name or 'Restaurant Team'} - {entry_id}",
                'description': f"Culinary Team Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Chef: {chef_name}\n"
                              f"Specialties: {specialties_str}\n"
                              f"Experience: {experience_years} years\n"
                              f"Certifications: {certifications_str}\n"
                              f"Team Size: {team_size}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '1',  # Normal priority for team info
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from culinary team event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing culinary team event: {str(e)}")
            return False

    def _process_email_event(self, entry, value, webhook_event, object_type=''):
        """
        Process email event - Update Partner with email address.
        Email represents contact email updates for communication.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "email"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "email",
            "value": {
                "email": "contact@example.com",
                "contact_name": "John Doe",
                "verified": true
            }
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract email data from value (may be string or dict)
            if isinstance(value, str):
                email = value
                contact_name = f"Meta Email Contact - {entry_id}"
                verified = False
            else:
                email = value.get('email', '') if value else ''
                contact_name = value.get('contact_name', f"Meta Email Contact - {entry_id}") if value else f"Meta Email Contact - {entry_id}"
                verified = value.get('verified', False) if value else False
            
            # Try to find existing partner by email or create new one
            existing_partner = False
            if email:
                existing_partner = Partner.search([('email', '=', email)], limit=1)
            
            partner_vals = {
                'name': contact_name,
                'email': email,
                'comment': f"Email Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Email: {email}\n"
                          f"Verified: {verified}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with email event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from email event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing email event: {str(e)}")
            return False

    def _process_description_event(self, entry, value, webhook_event, object_type=''):
        """
        Process description event - Create CRM Lead with general description.
        Description represents general business or page description updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "description"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "description",
            "value": "This is a great business that provides excellent services."
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For description, value is typically a string
            description_text = value if isinstance(value, str) else str(value) if value else 'No description provided'
            
            lead_vals = {
                'name': f"[DESCRIPTION UPDATE] Meta Description - {entry_id}",
                'description': f"Description Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Description: {description_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '0',  # Low priority for description updates
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from description event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing description event: {str(e)}")
            return False

    def _process_founded_event(self, entry, value, webhook_event, object_type=''):
        """
        Process founded event - Update Partner with founding date.
        Founded represents when the business was established.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "founded"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "founded",
            "value": "2014 April"
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Founded value is typically a string like "2014 April"
            founded_text = value if isinstance(value, str) else str(value) if value else 'Not specified'
            
            # Try to find existing partner or create new one
            partner_name = f"Meta Founded Business - {entry_id}"
            existing_partner = Partner.search([('name', 'ilike', partner_name)], limit=1)
            
            partner_vals = {
                'name': partner_name,
                'comment': f"Founded Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Founded: {founded_text}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with founded event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from founded event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing founded event: {str(e)}")
            return False

    def _process_feed_event(self, entry, value, webhook_event, object_type=''):
        """
        Process feed event - Create CRM Lead with social media post info.
        Feed represents social media posts and activity updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "feed"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "feed",
            "value": {
                "item": "status",
                "post_id": "44444444_444444444",
                "verb": "add",
                "published": 1,
                "created_time": 1769242032,
                "message": "Example post content.",
                "from": {
                    "name": "Test Page",
                    "id": "1067280970047460"
                }
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract feed data from value object
            if isinstance(value, dict):
                item = value.get('item', 'unknown')
                post_id = value.get('post_id', '')
                verb = value.get('verb', 'unknown')
                published = value.get('published', 0)
                created_time = value.get('created_time', 0)
                message = value.get('message', '')
                from_info = value.get('from', {})
                from_name = from_info.get('name', 'Unknown') if from_info else 'Unknown'
                from_id = from_info.get('id', '') if from_info else ''
            else:
                # Fallback for non-object values
                item = str(value) if value else 'unknown'
                post_id = verb = message = from_name = from_id = ''
                published = created_time = 0
            
            lead_vals = {
                'name': f"[FEED POST] {from_name} - {item}",
                'description': f"Feed Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Post ID: {post_id}\n"
                              f"Item: {item}\n"
                              f"Verb: {verb}\n"
                              f"Published: {published}\n"
                              f"Created Time: {created_time}\n"
                              f"Message: {message}\n"
                              f"From: {from_name} ({from_id})\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '1',  # Medium priority for social media activity
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from feed event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing feed event: {str(e)}")
            return False

    def _process_general_manager_event(self, entry, value, webhook_event, object_type=''):
        """
        Process general_manager event - Create CRM Lead with management info.
        General_manager represents business management and leadership updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "general_manager"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "general_manager",
            "value": {
                "name": "John Smith",
                "title": "General Manager",
                "contact": "john@example.com"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract manager data from value (may be string or object)
            if isinstance(value, str):
                manager_name = value
                manager_title = "General Manager"
                manager_contact = ""
            elif isinstance(value, dict):
                manager_name = value.get('name', 'Unknown Manager')
                manager_title = value.get('title', 'General Manager')
                manager_contact = value.get('contact', '')
            else:
                manager_name = str(value) if value else 'Unknown Manager'
                manager_title = "General Manager"
                manager_contact = ""
            
            lead_vals = {
                'name': f"[MANAGEMENT] {manager_name} - {manager_title}",
                'description': f"General Manager Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Manager Name: {manager_name}\n"
                              f"Title: {manager_title}\n"
                              f"Contact: {manager_contact}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '2',  # High priority for management changes
                'contact_name': manager_name,
                'email_from': manager_contact if manager_contact else False,
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from general_manager event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing general_manager event: {str(e)}")
            return False

    def _process_hometown_event(self, entry, value, webhook_event, object_type=''):
        """
        Process hometown event - Update Partner with hometown/location info.
        Hometown represents personal or business origin location information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "hometown"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "hometown",
            "value": {
                "city": "New York",
                "state": "NY",
                "country": "USA"
            }
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract hometown data from value (may be string or object)
            if isinstance(value, str):
                hometown_text = value
                city = state = country = ""
            elif isinstance(value, dict):
                city = value.get('city', '')
                state = value.get('state', '')
                country = value.get('country', '')
                hometown_text = f"{city}, {state}, {country}".strip(', ')
            else:
                hometown_text = str(value) if value else 'Not specified'
                city = state = country = ""
            
            # Try to find existing partner or create new one
            partner_name = f"Meta Hometown Contact - {entry_id}"
            existing_partner = Partner.search([('name', 'ilike', partner_name)], limit=1)
            
            partner_vals = {
                'name': partner_name,
                'comment': f"Hometown Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Hometown: {hometown_text}\n"
                          f"City: {city}\n"
                          f"State: {state}\n"
                          f"Country: {country}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with hometown event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from hometown event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing hometown event: {str(e)}")
            return False

    def _process_group_feed_event(self, entry, value, webhook_event, object_type=''):
        """
        Process group_feed event - Create CRM Lead with group post/comment info.
        Group_feed represents Facebook group posts, comments, and interactions.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "group_feed"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "group_feed",
            "value": {
                "recipient": {
                    "id": "105884685145408"
                },
                "from": {
                    "id": "105884685145409",
                    "name": "John Doe"
                },
                "group_id": "1848645382201914",
                "comment_id": "1854779258255193",
                "post_id": "1848645605535225",
                "created_time": 1680550572,
                "item": "comment",
                "verb": "add",
                "message": "comment 40",
                "field": "group_feed",
                "parent_id": "1848645605535225"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract group feed data from value object
            if isinstance(value, dict):
                recipient = value.get('recipient', {})
                recipient_id = recipient.get('id', '') if recipient else ''
                
                from_info = value.get('from', {})
                from_id = from_info.get('id', '') if from_info else ''
                from_name = from_info.get('name', 'Unknown') if from_info else 'Unknown'
                
                group_id = value.get('group_id', '')
                comment_id = value.get('comment_id', '')
                post_id = value.get('post_id', '')
                created_time = value.get('created_time', 0)
                item = value.get('item', 'unknown')
                verb = value.get('verb', 'unknown')
                message = value.get('message', '')
                parent_id = value.get('parent_id', '')
            else:
                # Fallback for non-object values
                recipient_id = from_id = from_name = group_id = comment_id = post_id = ''
                item = verb = message = parent_id = str(value) if value else 'unknown'
                created_time = 0
            
            lead_vals = {
                'name': f"[GROUP {item.upper()}] {from_name} - Group {group_id}",
                'description': f"Group Feed Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Group ID: {group_id}\n"
                              f"Post ID: {post_id}\n"
                              f"Comment ID: {comment_id}\n"
                              f"Parent ID: {parent_id}\n"
                              f"Item: {item}\n"
                              f"Verb: {verb}\n"
                              f"Created Time: {created_time}\n"
                              f"Message: {message}\n"
                              f"From: {from_name} ({from_id})\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '1',  # Medium priority for group activity
                'contact_name': from_name,
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from group_feed event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing group_feed event: {str(e)}")
            return False

    def _process_hours_event(self, entry, value, webhook_event, object_type=''):
        """
        Process hours event - Update Partner with business operating hours.
        Hours represents business hours and availability information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "hours"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "hours",
            "value": {
                "mon": "09:00-17:00",
                "tue": "09:00-17:00",
                "wed": "09:00-17:00",
                "thu": "09:00-17:00",
                "fri": "09:00-17:00",
                "sat": "closed",
                "sun": "closed"
            }
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract hours data from value (may be string or object)
            if isinstance(value, str):
                hours_text = value
                hours_dict = {}
            elif isinstance(value, dict):
                hours_dict = value
                # Format hours into readable text
                hours_lines = []
                for day, hours in hours_dict.items():
                    hours_lines.append(f"{day.upper()}: {hours}")
                hours_text = "\n".join(hours_lines)
            else:
                hours_text = str(value) if value else 'Not specified'
                hours_dict = {}
            
            # Try to find existing partner or create new one
            partner_name = f"Meta Business Hours - {entry_id}"
            existing_partner = Partner.search([('name', 'ilike', partner_name)], limit=1)
            
            partner_vals = {
                'name': partner_name,
                'comment': f"Hours Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Business Hours:\n{hours_text}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with hours event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from hours event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing hours event: {str(e)}")
            return False

    def _process_leadgen_event(self, entry, value, webhook_event, object_type=''):
        """
        Process leadgen event - Create CRM Lead from ad lead generation.
        Leadgen represents leads generated from Facebook/Instagram ads.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "leadgen"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "leadgen",
            "value": {
                "ad_id": "444444444",
                "form_id": "444444444444",
                "leadgen_id": "444444444444",
                "created_time": 1769244778,
                "page_id": "444444444444",
                "adgroup_id": "44444444444"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract leadgen data from value object
            if isinstance(value, dict):
                ad_id = value.get('ad_id', '')
                form_id = value.get('form_id', '')
                leadgen_id = value.get('leadgen_id', '')
                created_time = value.get('created_time', 0)
                page_id = value.get('page_id', '')
                adgroup_id = value.get('adgroup_id', '')
            else:
                # Fallback for non-object values
                ad_id = form_id = leadgen_id = page_id = adgroup_id = str(value) if value else ''
                created_time = 0
            
            lead_vals = {
                'name': f"[LEADGEN] Ad Lead - {leadgen_id}",
                'description': f"Leadgen Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Leadgen ID: {leadgen_id}\n"
                              f"Ad ID: {ad_id}\n"
                              f"Form ID: {form_id}\n"
                              f"Ad Group ID: {adgroup_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Created Time: {created_time}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(leadgen_id),
                'priority': '3',  # Highest priority for generated leads
                'source_id': request.env.ref('utm.utm_source_facebook').id if hasattr(request.env, 'ref') else False,  # Facebook as source
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from leadgen event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing leadgen event: {str(e)}")
            return False

    def _process_invoice_access_invoice_draft_change_event(self, entry, value, webhook_event, object_type=''):
        """
        Process invoice_access_invoice_draft_change event - Create Sale Order from invoice changes.
        Invoice draft changes represent updates to invoices and payments.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "invoice_access_invoice_draft_change"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "invoice_access_invoice_draft_change",
            "value": {
                "page_id": 12345,
                "invoice_id": 12345,
                "external_invoice_id": "SKU00001",
                "updates": {
                    "shipping_address": {...},
                    "payments": {...}
                }
            }
        }
        """
        try:
            SaleOrder = request.env['sale.order'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract invoice data from value object
            if isinstance(value, dict):
                page_id = value.get('page_id', '')
                invoice_id = value.get('invoice_id', '')
                external_invoice_id = value.get('external_invoice_id', '')
                updates = value.get('updates', {})
                
                # Extract shipping address changes
                shipping_updates = updates.get('shipping_address', {})
                shipping_previous = shipping_updates.get('previous_value', {})
                shipping_new = shipping_updates.get('new_value', {})
                
                # Extract payment changes
                payment_updates = updates.get('payments', {})
                payments_previous = payment_updates.get('previous_value', [])
                payments_new = payment_updates.get('new_value', [])
            else:
                # Fallback for non-object values
                page_id = invoice_id = external_invoice_id = str(value) if value else ''
                shipping_previous = shipping_new = {}
                payments_previous = payments_new = []
            
            # Create sale order note with invoice change details
            order_note = f"Invoice Draft Change from Meta\n"
            order_note += f"Object Type: {object_type}\n"
            order_note += f"Entry ID: {entry_id}\n"
            order_note += f"Entry Time: {entry_time}\n"
            order_note += f"Page ID: {page_id}\n"
            order_note += f"Invoice ID: {invoice_id}\n"
            order_note += f"External Invoice ID: {external_invoice_id}\n"
            
            if shipping_previous or shipping_new:
                order_note += f"\nShipping Address Changes:\n"
                if shipping_previous:
                    order_note += f"Previous: {json.dumps(shipping_previous, indent=2)}\n"
                if shipping_new:
                    order_note += f"New: {json.dumps(shipping_new, indent=2)}\n"
            
            if payments_previous or payments_new:
                order_note += f"\nPayment Changes:\n"
                if payments_previous:
                    order_note += f"Previous: {json.dumps(payments_previous, indent=2)}\n"
                if payments_new:
                    order_note += f"New: {json.dumps(payments_new, indent=2)}\n"
            
            order_note += f"Webhook Event ID: {webhook_event.id}\n"
            order_note += f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}"
            
            # Try to find existing sale order by invoice ID or create new one
            existing_order = False
            if external_invoice_id:
                existing_order = SaleOrder.search([('name', 'ilike', f'%{external_invoice_id}%')], limit=1)
            
            if existing_order:
                existing_order.write({'note': order_note})
                _logger.info(f"Updated Sale Order {existing_order.id} with invoice change")
                return existing_order
            else:
                order_vals = {
                    'partner_id': request.env.ref('base.partner_admin').id,  # Default partner
                    'note': order_note,
                    'origin': f"Meta Invoice Change - {external_invoice_id}",
                }
                order = SaleOrder.create(order_vals)
                _logger.info(f"Created Sale Order {order.id} from invoice_access_invoice_draft_change event")
                return order
                
        except Exception as e:
            _logger.exception(f"Error processing invoice_access_invoice_draft_change event: {str(e)}")
            return False

    def _process_inbox_labels_event(self, entry, value, webhook_event, object_type=''):
        """
        Process inbox_labels event - Create CRM Lead from inbox label actions.
        Inbox labels represent customer communication categorization and tagging.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "inbox_labels"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "inbox_labels",
            "value": {
                "user": {
                    "id": "2382390648517094"
                },
                "action": "add",
                "label": {
                    "id": "588120122044608",
                    "name": "label name"
                }
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract inbox label data from value object
            if isinstance(value, dict):
                user = value.get('user', {})
                user_id = user.get('id', '') if user else ''
                
                action = value.get('action', 'unknown')
                label = value.get('label', {})
                label_id = label.get('id', '') if label else ''
                label_name = label.get('name', 'Unknown Label') if label else 'Unknown Label'
            else:
                # Fallback for non-object values
                user_id = action = label_id = label_name = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[INBOX LABEL] {action.upper()} - {label_name}",
                'description': f"Inbox Labels Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Action: {action}\n"
                              f"Label: {label_name} ({label_id})\n"
                              f"User ID: {user_id}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(entry_id),
                'priority': '1',  # Medium priority for inbox actions
                'tag_ids': [(0, 0, {'name': f"Meta Label: {label_name}"})],  # Add tag for the label
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from inbox_labels event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing inbox_labels event: {str(e)}")
            return False

    def _process_marketing_message_clicks_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_message_clicks event - Create CRM Lead from marketing message interactions.
        Marketing message clicks represent customer engagement with promotional content.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_message_clicks"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_message_clicks",
            "value": {
                "field": "marketing_message_clicks",
                "recipient_id": 12313123123123,
                "page_id": 140984918491243,
                "timestamp": 41412414141,
                "mid": "mid.12313123123123",
                "messenger_subscription_token": "12348141984909088",
                "message_id": 124141414124
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract marketing message click data from value object
            if isinstance(value, dict):
                recipient_id = value.get('recipient_id', '')
                page_id = value.get('page_id', '')
                timestamp = value.get('timestamp', 0)
                mid = value.get('mid', '')
                messenger_subscription_token = value.get('messenger_subscription_token', '')
                message_id = value.get('message_id', '')
            else:
                # Fallback for non-object values
                recipient_id = page_id = mid = messenger_subscription_token = message_id = str(value) if value else ''
                timestamp = 0
            
            lead_vals = {
                'name': f"[MARKETING CLICK] Message {message_id}",
                'description': f"Marketing Message Clicks Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Message ID: {message_id}\n"
                              f"MID: {mid}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Messenger Subscription Token: {messenger_subscription_token}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(recipient_id),
                'priority': '2',  # High priority for marketing engagement
                'contact_name': f"Recipient {recipient_id}",
                'tag_ids': [(0, 0, {'name': 'Marketing Engagement'})],  # Add marketing tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_message_clicks event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_message_clicks event: {str(e)}")
            return False

    def _process_location_event(self, entry, value, webhook_event, object_type=''):
        """
        Process location event - Update Partner with location information.
        Location represents business or contact address and geographical data.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "location"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "location",
            "value": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
                "country": "USA",
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract location data from value (may be string or object)
            if isinstance(value, str):
                location_text = value
                street = city = state = zip_code = country = ""
                latitude = longitude = 0.0
            elif isinstance(value, dict):
                street = value.get('street', '')
                city = value.get('city', '')
                state = value.get('state', '')
                zip_code = value.get('zip', '')
                country = value.get('country', '')
                latitude = value.get('latitude', 0.0)
                longitude = value.get('longitude', 0.0)
                location_text = f"{street}, {city}, {state} {zip_code}, {country}".strip(', ')
            else:
                location_text = str(value) if value else 'Not specified'
                street = city = state = zip_code = country = ""
                latitude = longitude = 0.0
            
            # Try to find existing partner or create new one
            partner_name = f"Meta Location Contact - {entry_id}"
            existing_partner = Partner.search([('name', 'ilike', partner_name)], limit=1)
            
            partner_vals = {
                'name': partner_name,
                'street': street,
                'city': city,
                'state_id': False,  # Would need state lookup
                'zip': zip_code,
                'country_id': False,  # Would need country lookup
                'comment': f"Location Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Location: {location_text}\n"
                          f"Street: {street}\n"
                          f"City: {city}\n"
                          f"State: {state}\n"
                          f"ZIP: {zip_code}\n"
                          f"Country: {country}\n"
                          f"Latitude: {latitude}\n"
                          f"Longitude: {longitude}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with location event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from location event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing location event: {str(e)}")
            return False

    def _process_live_videos_event(self, entry, value, webhook_event, object_type=''):
        """
        Process live_videos event - Create CRM Lead from live video events.
        Live videos represent live streaming activity and status changes.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "live_videos"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "live_videos",
            "value": {
                "id": "4444444444",
                "status": "live_stopped"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract live video data from value object
            if isinstance(value, dict):
                video_id = value.get('id', '')
                status = value.get('status', 'unknown')
            else:
                # Fallback for non-object values
                video_id = status = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[LIVE VIDEO] {status.upper()} - {video_id}",
                'description': f"Live Videos Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Video ID: {video_id}\n"
                              f"Status: {status}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(video_id),
                'priority': '1',  # Medium priority for live video activity
                'tag_ids': [(0, 0, {'name': f'Live Video: {status}'})],  # Add status tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from live_videos event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing live_videos event: {str(e)}")
            return False

    def _process_marketing_message_clicks_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_message_clicks event - Create CRM Lead from marketing message interactions.
        Marketing message clicks represent customer engagement with promotional content.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_message_clicks"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_message_clicks",
            "value": {
                "field": "marketing_message_clicks",
                "recipient_id": 12313123123123,
                "page_id": 140984918491243,
                "timestamp": 41412414141,
                "mid": "mid.12313123123123",
                "messenger_subscription_token": "12348141984909088",
                "message_id": 124141414124
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract marketing message click data from value object
            if isinstance(value, dict):
                recipient_id = value.get('recipient_id', '')
                page_id = value.get('page_id', '')
                timestamp = value.get('timestamp', 0)
                mid = value.get('mid', '')
                messenger_subscription_token = value.get('messenger_subscription_token', '')
                message_id = value.get('message_id', '')
            else:
                # Fallback for non-object values
                recipient_id = page_id = mid = messenger_subscription_token = message_id = str(value) if value else ''
                timestamp = 0
            
            lead_vals = {
                'name': f"[MARKETING CLICK] Message {message_id}",
                'description': f"Marketing Message Clicks Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Message ID: {message_id}\n"
                              f"MID: {mid}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Messenger Subscription Token: {messenger_subscription_token}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(recipient_id),
                'priority': '2',  # High priority for marketing engagement
                'contact_name': f"Recipient {recipient_id}",
                'tag_ids': [(0, 0, {'name': 'Marketing Engagement'})],  # Add marketing tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_message_clicks event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_message_clicks event: {str(e)}")
            return False

    def _process_marketing_message_deliveries_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_message_deliveries event - Create CRM Lead from marketing message deliveries.
        Marketing message deliveries represent successful message delivery tracking.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_message_deliveries"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_message_deliveries",
            "value": {
                "field": "marketing_message_deliveries",
                "recipient_id": 12313123123123,
                "page_id": 140984918491243,
                "app_id": 12313123123123,
                "timestamp": 41412414141,
                "mid": "mid.12313123123123",
                "marketing_message_tracking_id": "12313123123123",
                "messenger_subscription_token": "12348141984909088",
                "message_id": 124141414124
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract marketing message delivery data from value object
            if isinstance(value, dict):
                recipient_id = value.get('recipient_id', '')
                page_id = value.get('page_id', '')
                app_id = value.get('app_id', '')
                timestamp = value.get('timestamp', 0)
                mid = value.get('mid', '')
                marketing_message_tracking_id = value.get('marketing_message_tracking_id', '')
                messenger_subscription_token = value.get('messenger_subscription_token', '')
                message_id = value.get('message_id', '')
            else:
                # Fallback for non-object values
                recipient_id = page_id = app_id = mid = marketing_message_tracking_id = messenger_subscription_token = message_id = str(value) if value else ''
                timestamp = 0
            
            lead_vals = {
                'name': f"[MARKETING DELIVERY] Message {message_id}",
                'description': f"Marketing Message Deliveries Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Page ID: {page_id}\n"
                              f"App ID: {app_id}\n"
                              f"Message ID: {message_id}\n"
                              f"MID: {mid}\n"
                              f"Marketing Message Tracking ID: {marketing_message_tracking_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Messenger Subscription Token: {messenger_subscription_token}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(recipient_id),
                'priority': '1',  # Medium priority for delivery tracking
                'contact_name': f"Recipient {recipient_id}",
                'tag_ids': [(0, 0, {'name': 'Message Delivered'})],  # Add delivery tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_message_deliveries event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_message_deliveries event: {str(e)}")
            return False

    def _process_marketing_message_delivery_failed_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_message_delivery_failed event - Create CRM Lead from failed message deliveries.
        Marketing message delivery failures represent issues with message delivery that need attention.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_message_delivery_failed"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_message_delivery_failed",
            "value": {
                "field": "marketing_message_delivery_failed",
                "app_id": 12313123123123,
                "business_id": 134141414124123,
                "page_id": 140984918491243,
                "messenger_subscription_token": "12348141984909088",
                "timestamp": 41412414141,
                "error_message": "Unknown Error",
                "message_id": "124141414124"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract marketing message delivery failed data from value object
            if isinstance(value, dict):
                app_id = value.get('app_id', '')
                business_id = value.get('business_id', '')
                page_id = value.get('page_id', '')
                messenger_subscription_token = value.get('messenger_subscription_token', '')
                timestamp = value.get('timestamp', 0)
                error_message = value.get('error_message', 'Unknown error')
                message_id = value.get('message_id', '')
            else:
                # Fallback for non-object values
                app_id = business_id = page_id = messenger_subscription_token = message_id = str(value) if value else ''
                error_message = 'Unknown error'
                timestamp = 0
            
            lead_vals = {
                'name': f"[DELIVERY FAILED] Message {message_id}",
                'description': f"Marketing Message Delivery Failed Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"App ID: {app_id}\n"
                              f"Business ID: {business_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Message ID: {message_id}\n"
                              f"Error Message: {error_message}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Messenger Subscription Token: {messenger_subscription_token}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(message_id),
                'priority': '3',  # Highest priority for delivery failures
                'tag_ids': [(0, 0, {'name': 'Delivery Failed'})],  # Add failure tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_message_delivery_failed event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_message_delivery_failed event: {str(e)}")
            return False

    def _process_marketing_messages_subscriber_upload_status_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_messages_subscriber_upload_status event - Create CRM Lead from subscriber upload status.
        Marketing messages subscriber upload status represents the status of uploading subscribers to custom audiences.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_messages_subscriber_upload_status"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_messages_subscriber_upload_status",
            "value": {
                "field": "marketing_messages_subscriber_upload_status",
                "app_id": 12313123123123,
                "page_id": 134141414124123,
                "custom_audience_id": 140984918491243,
                "ad_account_id": "12348141984909088",
                "timestamp": 41412414141,
                "num_rows": 100,
                "business_id": 12313123123123,
                "approximate_count_lower_bound": 100,
                "approximate_count_upper_bound": 100,
                "batch_uploading_status": "SUCCESS"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract subscriber upload status data from value object
            if isinstance(value, dict):
                app_id = value.get('app_id', '')
                page_id = value.get('page_id', '')
                custom_audience_id = value.get('custom_audience_id', '')
                ad_account_id = value.get('ad_account_id', '')
                timestamp = value.get('timestamp', 0)
                num_rows = value.get('num_rows', 0)
                business_id = value.get('business_id', '')
                approximate_count_lower_bound = value.get('approximate_count_lower_bound', 0)
                approximate_count_upper_bound = value.get('approximate_count_upper_bound', 0)
                batch_uploading_status = value.get('batch_uploading_status', 'unknown')
            else:
                # Fallback for non-object values
                app_id = page_id = custom_audience_id = ad_account_id = business_id = batch_uploading_status = str(value) if value else ''
                timestamp = num_rows = approximate_count_lower_bound = approximate_count_upper_bound = 0
            
            lead_vals = {
                'name': f"[UPLOAD STATUS] {batch_uploading_status} - Audience {custom_audience_id}",
                'description': f"Marketing Messages Subscriber Upload Status Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"App ID: {app_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Custom Audience ID: {custom_audience_id}\n"
                              f"Ad Account ID: {ad_account_id}\n"
                              f"Business ID: {business_id}\n"
                              f"Batch Uploading Status: {batch_uploading_status}\n"
                              f"Number of Rows: {num_rows}\n"
                              f"Approximate Count: {approximate_count_lower_bound} - {approximate_count_upper_bound}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(custom_audience_id),
                'priority': '1',  # Medium priority for upload status tracking
                'tag_ids': [(0, 0, {'name': f'Upload: {batch_uploading_status}'})],  # Add status tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_messages_subscriber_upload_status event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_messages_subscriber_upload_status event: {str(e)}")
            return False

    def _process_marketing_message_reads_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_message_reads event - Create CRM Lead from marketing message read events.
        Marketing message reads represent when customers read marketing messages.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_message_reads"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_message_reads",
            "value": {
                "field": "marketing_message_reads",
                "recipient_id": 12313123123123,
                "page_id": 140984918491243,
                "timestamp": 41412414141,
                "marketing_message_tracking_id": "12313123123123",
                "messenger_subscription_token": "12348141984909088",
                "message_id": 124141414124
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract marketing message reads data from value object
            if isinstance(value, dict):
                recipient_id = value.get('recipient_id', '')
                page_id = value.get('page_id', '')
                timestamp = value.get('timestamp', 0)
                marketing_message_tracking_id = value.get('marketing_message_tracking_id', '')
                messenger_subscription_token = value.get('messenger_subscription_token', '')
                message_id = value.get('message_id', '')
            else:
                # Fallback for non-object values
                recipient_id = page_id = marketing_message_tracking_id = messenger_subscription_token = message_id = str(value) if value else ''
                timestamp = 0
            
            lead_vals = {
                'name': f"[MESSAGE READ] Message {message_id}",
                'description': f"Marketing Message Reads Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Message ID: {message_id}\n"
                              f"Marketing Message Tracking ID: {marketing_message_tracking_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Messenger Subscription Token: {messenger_subscription_token}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(recipient_id),
                'priority': '2',  # High priority for message engagement
                'contact_name': f"Recipient {recipient_id}",
                'tag_ids': [(0, 0, {'name': 'Message Read'})],  # Add read tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_message_reads event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_message_reads event: {str(e)}")
            return False

    def _process_marketing_message_echoes_event(self, entry, value, webhook_event, object_type=''):
        """
        Process marketing_message_echoes event - Create CRM Lead from marketing message echo events.
        Marketing message echoes represent automated responses or echoes to marketing messages.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "marketing_message_echoes"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "marketing_message_echoes",
            "value": {
                "field": "marketing_message_echoes",
                "recipient_id": 12313123123123,
                "page_id": 140984918491243,
                "app_id": 12313123123123,
                "timestamp": 41412414141,
                "mid": "mid.12313123123123",
                "marketing_message_tracking_id": "12313123123123",
                "messenger_subscription_token": "12348141984909088",
                "message_id": 124141414124
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract marketing message echoes data from value object
            if isinstance(value, dict):
                recipient_id = value.get('recipient_id', '')
                page_id = value.get('page_id', '')
                app_id = value.get('app_id', '')
                timestamp = value.get('timestamp', 0)
                mid = value.get('mid', '')
                marketing_message_tracking_id = value.get('marketing_message_tracking_id', '')
                messenger_subscription_token = value.get('messenger_subscription_token', '')
                message_id = value.get('message_id', '')
            else:
                # Fallback for non-object values
                recipient_id = page_id = app_id = mid = marketing_message_tracking_id = messenger_subscription_token = message_id = str(value) if value else ''
                timestamp = 0
            
            lead_vals = {
                'name': f"[MESSAGE ECHO] Message {message_id}",
                'description': f"Marketing Message Echoes Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Page ID: {page_id}\n"
                              f"App ID: {app_id}\n"
                              f"Message ID: {message_id}\n"
                              f"MID: {mid}\n"
                              f"Marketing Message Tracking ID: {marketing_message_tracking_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Messenger Subscription Token: {messenger_subscription_token}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(recipient_id),
                'priority': '1',  # Medium priority for automated responses
                'contact_name': f"Recipient {recipient_id}",
                'tag_ids': [(0, 0, {'name': 'Message Echo'})],  # Add echo tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from marketing_message_echoes event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing marketing_message_echoes event: {str(e)}")
            return False

    def _process_message_context_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_context event - Create CRM Lead from message context and purchase detections.
        Message context represents AI-powered analysis of messages including purchase intent detection.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_context"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_context",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "message_context": {
                    "detections": [
                        {
                            "type": "PURCHASE",
                            "id": "26272",
                            "mid": "98567",
                            "event_name": "payment_received",
                            "model": "model-0"
                        }
                    ],
                    "suggestions": [
                        {
                            "type": "PURCHASE",
                            "id": "26272",
                            "mid": "98567",
                            "event_name": "fb_mobile_purchase",
                            "model": "model-0"
                        }
                    ]
                }
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract message context data from value object
            if isinstance(value, dict):
                sender = value.get('sender', {})
                sender_id = sender.get('id', '') if sender else ''
                
                recipient = value.get('recipient', {})
                recipient_id = recipient.get('id', '') if recipient else ''
                
                timestamp = value.get('timestamp', '')
                message_context = value.get('message_context', {})
                
                detections = message_context.get('detections', []) if message_context else []
                suggestions = message_context.get('suggestions', []) if message_context else []
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = str(value) if value else ''
                detections = suggestions = []
            
            # Format detections and suggestions for display
            detections_text = ""
            if detections:
                detections_text = "Detections:\n" + "\n".join([
                    f"- {d.get('type', 'Unknown')}: {d.get('event_name', 'Unknown')} (ID: {d.get('id', 'N/A')})"
                    for d in detections
                ])
            
            suggestions_text = ""
            if suggestions:
                suggestions_text = "Suggestions:\n" + "\n".join([
                    f"- {s.get('type', 'Unknown')}: {s.get('event_name', 'Unknown')} (ID: {s.get('id', 'N/A')})"
                    for s in suggestions
                ])
            
            lead_vals = {
                'name': f"[MESSAGE CONTEXT] Sender {sender_id} to {recipient_id}",
                'description': f"Message Context Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"{detections_text}\n"
                              f"{suggestions_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(sender_id),
                'priority': '2',  # High priority for purchase intent detection
                'contact_name': f"Sender {sender_id}",
                'tag_ids': [(0, 0, {'name': 'Purchase Intent'})] if detections else [(0, 0, {'name': 'Message Context'})],
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_context event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_context event: {str(e)}")
            return False

    def _process_mention_event(self, entry, value, webhook_event, object_type=''):
        """
        Process mention event - Create CRM Lead from social media mentions.
        Mention represents when a page or user is mentioned in social media posts.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "mention"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "mention",
            "value": {
                "post_id": "44444444_444444444",
                "sender_name": "Example Name",
                "item": "post",
                "sender_id": "44444444",
                "verb": "add"
            }
        }
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract mention data from value object
            if isinstance(value, dict):
                post_id = value.get('post_id', '')
                sender_name = value.get('sender_name', 'Unknown')
                item = value.get('item', 'unknown')
                sender_id = value.get('sender_id', '')
                verb = value.get('verb', 'unknown')
            else:
                # Fallback for non-object values
                post_id = sender_name = item = sender_id = verb = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[MENTION] {sender_name} - {item}",
                'description': f"Mention Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Post ID: {post_id}\n"
                              f"Sender: {sender_name} ({sender_id})\n"
                              f"Item: {item}\n"
                              f"Verb: {verb}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(sender_id),
                'priority': '2',  # High priority for social media mentions
                'contact_name': sender_name,
                'tag_ids': [(0, 0, {'name': f'Mention: {item}'})],  # Add mention tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from mention event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing mention event: {str(e)}")
            return False

    def _process_members_event(self, entry, value, webhook_event, object_type=''):
        """
        Process members event - Update Partner with member information.
        Members represents group or page membership changes and information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "members"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "members",
            "value": {
                "user_id": "12345",
                "name": "John Doe",
                "role": "member",
                "joined_time": 1640995200
            }
        }
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract member data from value (may be string or object)
            if isinstance(value, str):
                member_text = value
                user_id = name = role = ""
                joined_time = 0
            elif isinstance(value, dict):
                user_id = value.get('user_id', '')
                name = value.get('name', 'Unknown Member')
                role = value.get('role', 'member')
                joined_time = value.get('joined_time', 0)
                member_text = f"{name} ({user_id}) - {role}"
            else:
                member_text = str(value) if value else 'Unknown member'
                user_id = name = role = ""
                joined_time = 0
            
            # Try to find existing partner or create new one
            partner_name = f"Meta Member - {name or user_id}"
            existing_partner = Partner.search([('name', 'ilike', partner_name)], limit=1)
            
            partner_vals = {
                'name': partner_name,
                'comment': f"Members Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Member: {member_text}\n"
                          f"User ID: {user_id}\n"
                          f"Name: {name}\n"
                          f"Role: {role}\n"
                          f"Joined Time: {joined_time}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with members event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from members event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing members event: {str(e)}")
            return False

    def _process_message_edits_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_edits event - Create CRM Lead from message edit events.
        Message edits represent when users modify their sent messages.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_edits"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_edits",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "message_edit": {
                    "mid": "test_message_id",
                    "text": "test_message"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing message edit data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract message edit data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                message_edit = value.get('message_edit', {}) if isinstance(value.get('message_edit'), dict) else {}
                message_id = message_edit.get('mid', '')
                message_text = message_edit.get('text', '')
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = message_id = message_text = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[MESSAGE EDIT] {message_id}",
                'description': f"Message Edits Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Message ID: {message_id}\n"
                              f"Edited Text: {message_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(message_id),
                'priority': '2',  # High priority for message edits (customer engagement)
                'tag_ids': [(0, 0, {'name': 'Message Edit'})],  # Add message edit tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_edits event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_edits event: {str(e)}")
            return False

    def _process_message_echoes_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_echoes event - Create CRM Lead from message echo events.
        Message echoes represent automated responses or echoed messages.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_echoes"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_echoes",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "message": {
                    "is_echo": true,
                    "mid": "test_message_id",
                    "text": "test_message"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing message echo data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract message echo data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                message = value.get('message', {}) if isinstance(value.get('message'), dict) else {}
                is_echo = message.get('is_echo', False)
                message_id = message.get('mid', '')
                message_text = message.get('text', '')
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = message_id = message_text = str(value) if value else 'unknown'
                is_echo = False
            
            lead_vals = {
                'name': f"[MESSAGE ECHO] {message_id}",
                'description': f"Message Echoes Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Is Echo: {is_echo}\n"
                              f"Message ID: {message_id}\n"
                              f"Echo Text: {message_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(message_id),
                'priority': '1',  # Medium priority for automated echoes
                'tag_ids': [(0, 0, {'name': 'Message Echo'})],  # Add message echo tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_echoes event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_echoes event: {str(e)}")
            return False

    def _process_message_deliveries_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_deliveries event - Create CRM Lead from message delivery events.
        Message deliveries represent successful message delivery confirmations.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_deliveries"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_deliveries",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "delivery": {
                    "watermark": "1648581633369",
                    "mids": [
                        "m_akKgiZwD2F344nARcDK1xPOUxPPq4EBLenS9igzjoTnYPHmhIN5Bu8J9E6Bk8S49C2fkbEMbarvzqNN7MuoQPQ"
                    ]
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing message delivery data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract message delivery data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                delivery = value.get('delivery', {}) if isinstance(value.get('delivery'), dict) else {}
                watermark = delivery.get('watermark', '')
                mids = delivery.get('mids', []) if isinstance(delivery.get('mids'), list) else []
                mids_text = ', '.join(mids) if mids else 'None'
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = watermark = mids_text = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[MESSAGE DELIVERY] {watermark}",
                'description': f"Message Deliveries Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Watermark: {watermark}\n"
                              f"Message IDs: {mids_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(watermark),
                'priority': '0',  # Low priority for delivery confirmations (routine)
                'tag_ids': [(0, 0, {'name': 'Message Delivery'})],  # Add message delivery tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_deliveries event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_deliveries event: {str(e)}")
            return False

    def _process_website_event(self, entry, value, webhook_event, object_type=''):
        """
        Process website event - Update Partner with website information.
        Website represents business website updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "website"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "website"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            website_value = str(value) if value else 'website_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'website': website_value,
                'comment': f"Website Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Website Update: {website_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with website event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from website event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing website event: {str(e)}")
            return False

    def _process_videos_event(self, entry, value, webhook_event, object_type=''):
        """
        Process videos event - Create CRM Lead from video content events.
        Videos represent video uploads, updates, or status changes.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "videos"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "videos",
            "value": {
                "id": "4444444",
                "status": {
                    "video_status": "ready"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing video data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract video data from value object
            if isinstance(value, dict):
                video_id = value.get('id', '')
                status = value.get('status', {}) if isinstance(value.get('status'), dict) else {}
                video_status = status.get('video_status', 'unknown') if isinstance(status, dict) else str(status)
            else:
                # Fallback for non-object values
                video_id = video_status = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[VIDEO] {video_status.upper()} - {video_id}",
                'description': f"Videos Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Video ID: {video_id}\n"
                              f"Video Status: {video_status}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(video_id),
                'priority': '1',  # Medium priority for video content
                'tag_ids': [(0, 0, {'name': f'Video: {video_status}'})],  # Add video status tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from videos event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing videos event: {str(e)}")
            return False

    def _process_send_cart_event(self, entry, value, webhook_event, object_type=''):
        """
        Process send_cart event - Create Sale Order from shopping cart events.
        Send cart represents customer shopping cart/order submissions.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "send_cart"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "send_cart",
            "value": {
                "sender": {
                    "id": "123"
                },
                "recipient": {
                    "id": "456"
                },
                "timestamp": "1234567890",
                "order": {
                    "products": [
                        {
                            "id": 123,
                            "retailer_id": "retailer_id_1",
                            "name": "name1",
                            "unit_price": 11,
                            "currency": "THB",
                            "quantity": 1
                        },
                        {
                            "id": 456,
                            "retailer_id": "retailer_id_2",
                            "name": "name2",
                            "unit_price": 22,
                            "currency": "THB",
                            "quantity": 2
                        }
                    ],
                    "note": "Foobar",
                    "source": "live_shopping",
                    "source_id": "123456789"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing cart/order data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: sale.order record or False
        """
        try:
            SaleOrder = request.env['sale.order'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract cart/order data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                order = value.get('order', {}) if isinstance(value.get('order'), dict) else {}
                products = order.get('products', []) if isinstance(order.get('products'), list) else []
                note = order.get('note', '')
                source = order.get('source', '')
                source_id = order.get('source_id', '')
                
                # Build products summary
                products_summary = []
                total_amount = 0
                for product in products:
                    if isinstance(product, dict):
                        prod_name = product.get('name', 'Unknown Product')
                        prod_price = product.get('unit_price', 0)
                        prod_qty = product.get('quantity', 1)
                        prod_currency = product.get('currency', 'USD')
                        prod_total = prod_price * prod_qty
                        total_amount += prod_total
                        products_summary.append(f"{prod_name} (x{prod_qty}) - {prod_currency} {prod_total}")
                
                products_text = '\n'.join(products_summary) if products_summary else 'No products'
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = note = source = source_id = products_text = str(value) if value else 'unknown'
                total_amount = 0
            
            order_vals = {
                'partner_id': False,  # Will be set if we can find/create a partner
                'name': f"Meta Cart - {source_id or timestamp}",
                'note': f"Send Cart Event from Meta\n"
                       f"Object Type: {object_type}\n"
                       f"Entry ID: {entry_id}\n"
                       f"Entry Time: {entry_time}\n"
                       f"Sender ID: {sender_id}\n"
                       f"Recipient ID: {recipient_id}\n"
                       f"Timestamp: {timestamp}\n"
                       f"Source: {source}\n"
                       f"Source ID: {source_id}\n"
                       f"Order Note: {note}\n"
                       f"Products:\n{products_text}\n"
                       f"Total Amount: {total_amount}\n"
                       f"Webhook Event ID: {webhook_event.id}\n"
                       f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'state': 'draft',
            }
            
            order = SaleOrder.create(order_vals)
            _logger.info(f"Created Sale Order {order.id} from send_cart event")
            return order
                
        except Exception as e:
            _logger.exception(f"Error processing send_cart event: {str(e)}")
            return False

    def _process_ratings_event(self, entry, value, webhook_event, object_type=''):
        """
        Process ratings event - Create CRM Lead from customer ratings and reviews.
        Ratings represent customer feedback and reviews.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "ratings"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "ratings",
            "value": {
                "comment_id": "44444444_444444444",
                "created_time": 1769247193,
                "item": "rating",
                "open_graph_story_id": "444444",
                "rating": 4,
                "recommendation_type": "POSITIVE",
                "review_text": "I like this!",
                "reviewer_id": "444444",
                "reviewer_name": "Test user",
                "verb": "add"
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing rating/review data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract rating/review data from value object
            if isinstance(value, dict):
                comment_id = value.get('comment_id', '')
                created_time = value.get('created_time', 0)
                item = value.get('item', '')
                open_graph_story_id = value.get('open_graph_story_id', '')
                rating = value.get('rating', 0)
                recommendation_type = value.get('recommendation_type', '')
                review_text = value.get('review_text', '')
                reviewer_id = value.get('reviewer_id', '')
                reviewer_name = value.get('reviewer_name', '')
                verb = value.get('verb', '')
            else:
                # Fallback for non-object values
                comment_id = open_graph_story_id = reviewer_id = reviewer_name = review_text = str(value) if value else 'unknown'
                created_time = rating = 0
                item = recommendation_type = verb = 'unknown'
            
            lead_vals = {
                'name': f"[RATING] {rating}/5 - {reviewer_name}",
                'description': f"Ratings Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Comment ID: {comment_id}\n"
                              f"Created Time: {created_time}\n"
                              f"Item: {item}\n"
                              f"Open Graph Story ID: {open_graph_story_id}\n"
                              f"Rating: {rating}/5\n"
                              f"Recommendation: {recommendation_type}\n"
                              f"Review Text: {review_text}\n"
                              f"Reviewer ID: {reviewer_id}\n"
                              f"Reviewer Name: {reviewer_name}\n"
                              f"Verb: {verb}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(comment_id),
                'priority': '2',  # High priority for customer feedback
                'tag_ids': [(0, 0, {'name': f'Rating: {rating}/5'})],  # Add rating tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from ratings event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing ratings event: {str(e)}")
            return False

    def _process_public_transit_event(self, entry, value, webhook_event, object_type=''):
        """
        Process public_transit event - Update Partner with public transit information.
        Public transit represents business transportation/accessibility information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "public_transit"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "public_transit"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            transit_value = str(value) if value else 'public_transit_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Public Transit Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Public Transit Update: {transit_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with public_transit event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from public_transit event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing public_transit event: {str(e)}")
            return False

    def _process_products_event(self, entry, value, webhook_event, object_type=''):
        """
        Process products event - Update Partner with product information.
        Products represent business product catalog or offerings.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "products"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "products",
            "value": "Milk, Cheese, etc."
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing product data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract product data from value
            products_value = str(value) if value else 'products_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Products Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Products: {products_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with products event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from products event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing products event: {str(e)}")
            return False

    def _process_product_review_event(self, entry, value, webhook_event, object_type=''):
        """
        Process product_review event - Create CRM Lead from product review events.
        Product reviews represent customer feedback on specific products.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "product_review"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "product_review",
            "value": {
                "product_item_id": "44444444",
                "status": "APPROVED"
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing product review data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract product review data from value object
            if isinstance(value, dict):
                product_item_id = value.get('product_item_id', '')
                status = value.get('status', '')
            else:
                # Fallback for non-object values
                product_item_id = status = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[PRODUCT REVIEW] {status} - {product_item_id}",
                'description': f"Product Review Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Product Item ID: {product_item_id}\n"
                              f"Status: {status}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(product_item_id),
                'priority': '2',  # High priority for product reviews
                'tag_ids': [(0, 0, {'name': f'Product Review: {status}'})],  # Add review status tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from product_review event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing product_review event: {str(e)}")
            return False

    def _process_price_range_event(self, entry, value, webhook_event, object_type=''):
        """
        Process price_range event - Update Partner with price range information.
        Price range represents business pricing tier or cost information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "price_range"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "price_range"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            price_value = str(value) if value else 'price_range_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Price Range Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Price Range Update: {price_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with price_range event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from price_range event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing price_range event: {str(e)}")
            return False

    def _process_picture_event(self, entry, value, webhook_event, object_type=''):
        """
        Process picture event - Update Partner with picture information.
        Picture represents business profile or cover image updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "picture"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "picture"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            picture_value = str(value) if value else 'picture_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Picture Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Picture Update: {picture_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with picture event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from picture event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing picture event: {str(e)}")
            return False

    def _process_phone_event(self, entry, value, webhook_event, object_type=''):
        """
        Process phone event - Update Partner with phone information.
        Phone represents business contact phone number updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "phone"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "phone"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            phone_value = str(value) if value else 'phone_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'phone': phone_value if phone_value != 'phone_update' else False,
                'comment': f"Phone Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Phone Update: {phone_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with phone event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from phone event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing phone event: {str(e)}")
            return False

    def _process_personal_interests_event(self, entry, value, webhook_event, object_type=''):
        """
        Process personal_interests event - Update Partner with personal interests information.
        Personal interests represents business or personal interest categories.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "personal_interests"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "personal_interests"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            interests_value = str(value) if value else 'personal_interests_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Personal Interests Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Personal Interests Update: {interests_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with personal_interests event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from personal_interests event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing personal_interests event: {str(e)}")
            return False

    def _process_personal_info_event(self, entry, value, webhook_event, object_type=''):
        """
        Process personal_info event - Update Partner with personal information.
        Personal info represents business personal or biographical information.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "personal_info"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "personal_info"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            info_value = str(value) if value else 'personal_info_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Personal Info Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Personal Info Update: {info_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with personal_info event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from personal_info event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing personal_info event: {str(e)}")
            return False

    def _process_payment_options_event(self, entry, value, webhook_event, object_type=''):
        """
        Process payment_options event - Update Partner with payment options information.
        Payment options represents business accepted payment methods.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "payment_options"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "payment_options"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            payment_value = str(value) if value else 'payment_options_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Payment Options Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Payment Options Update: {payment_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with payment_options event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from payment_options event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing payment_options event: {str(e)}")
            return False

    def _process_parking_event(self, entry, value, webhook_event, object_type=''):
        """
        Process parking event - Update Partner with parking information.
        Parking represents business parking availability and options.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "parking"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "parking"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value (may be empty for simple fields)
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # For simple fields without complex value, use the field name as identifier
            parking_value = str(value) if value else 'parking_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Parking Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Parking Update: {parking_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with parking event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from parking event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing parking event: {str(e)}")
            return False

    def _process_page_upcoming_change_event(self, entry, value, webhook_event, object_type=''):
        """
        Process page_upcoming_change event - Create CRM Lead from page upcoming change notifications.
        Page upcoming changes represent scheduled page modifications that need attention.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "page_upcoming_change", "action": "pending"}]}], "object": "page"}
        
        Full payload template:
        {
            "action": "pending",
            "field": "page_upcoming_change",
            "value": {
                "id": "1687992854601886",
                "page": {
                    "id": "134511164859",
                    "name": "Page name"
                },
                "effective_time": "2017-03-01 12:00:00",
                "change_type": "knowledge_proposal",
                "timer_status": "active",
                "proposal": {
                    "id": "1687992851268553",
                    "acceptance_status": "pending",
                    "category": "menu link"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing page change data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract page change data from value object
            if isinstance(value, dict):
                change_id = value.get('id', '')
                page = value.get('page', {}) if isinstance(value.get('page'), dict) else {}
                page_id = page.get('id', '') if isinstance(page, dict) else ''
                page_name = page.get('name', '') if isinstance(page, dict) else ''
                effective_time = value.get('effective_time', '')
                change_type = value.get('change_type', '')
                timer_status = value.get('timer_status', '')
                proposal = value.get('proposal', {}) if isinstance(value.get('proposal'), dict) else {}
                proposal_id = proposal.get('id', '') if isinstance(proposal, dict) else ''
                acceptance_status = proposal.get('acceptance_status', '') if isinstance(proposal, dict) else ''
                category = proposal.get('category', '') if isinstance(proposal, dict) else ''
            else:
                # Fallback for non-object values
                change_id = page_id = page_name = effective_time = change_type = timer_status = proposal_id = acceptance_status = category = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[PAGE CHANGE] {change_type.upper()} - {page_name}",
                'description': f"Page Upcoming Change Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Change ID: {change_id}\n"
                              f"Page ID: {page_id}\n"
                              f"Page Name: {page_name}\n"
                              f"Effective Time: {effective_time}\n"
                              f"Change Type: {change_type}\n"
                              f"Timer Status: {timer_status}\n"
                              f"Proposal ID: {proposal_id}\n"
                              f"Acceptance Status: {acceptance_status}\n"
                              f"Category: {category}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(change_id),
                'priority': '3',  # Very high priority for page changes that need attention
                'tag_ids': [(0, 0, {'name': f'Page Change: {change_type}'})],  # Add change type tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from page_upcoming_change event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing page_upcoming_change event: {str(e)}")
            return False

    def _process_page_change_proposal_event(self, entry, value, webhook_event, object_type=''):
        """
        Process page_change_proposal event - Create CRM Lead from page change proposal events.
        Page change proposals represent suggested modifications to page content.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "page_change_proposal", "action": "created"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "page_change_proposal",
            "action": "created",
            "value": {
                "id": "12345678",
                "category": "menu link",
                "acceptance_status": "pending",
                "upcoming_change_info": {
                    "id": "4564321",
                    "effective_time": "2019-03-01 12:00:00",
                    "timer_status": "active"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing proposal data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract proposal data from value object
            if isinstance(value, dict):
                proposal_id = value.get('id', '')
                category = value.get('category', '')
                acceptance_status = value.get('acceptance_status', '')
                upcoming_change_info = value.get('upcoming_change_info', {}) if isinstance(value.get('upcoming_change_info'), dict) else {}
                change_info_id = upcoming_change_info.get('id', '') if isinstance(upcoming_change_info, dict) else ''
                effective_time = upcoming_change_info.get('effective_time', '') if isinstance(upcoming_change_info, dict) else ''
                timer_status = upcoming_change_info.get('timer_status', '') if isinstance(upcoming_change_info, dict) else ''
            else:
                # Fallback for non-object values
                proposal_id = category = acceptance_status = change_info_id = effective_time = timer_status = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[PROPOSAL] {category.upper()} - {acceptance_status.upper()}",
                'description': f"Page Change Proposal Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Proposal ID: {proposal_id}\n"
                              f"Category: {category}\n"
                              f"Acceptance Status: {acceptance_status}\n"
                              f"Change Info ID: {change_info_id}\n"
                              f"Effective Time: {effective_time}\n"
                              f"Timer Status: {timer_status}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(proposal_id),
                'priority': '3',  # Very high priority for proposals that need review
                'tag_ids': [(0, 0, {'name': f'Proposal: {category}'})],  # Add proposal category tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from page_change_proposal event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing page_change_proposal event: {str(e)}")
            return False

    def _process_name_event(self, entry, value, webhook_event, object_type=''):
        """
        Process name event - Update Partner with name information.
        Name represents business name updates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "name"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "name",
            "value": "Test Page Name"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing name data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract name data from value
            name_value = str(value) if value else 'name_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': name_value if name_value != 'name_update' else f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Name Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Name Update: {name_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with name event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from name event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing name event: {str(e)}")
            return False

    def _process_mission_event(self, entry, value, webhook_event, object_type=''):
        """
        Process mission event - Update Partner with mission information.
        Mission represents business mission statement or purpose.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "mission"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "mission",
            "value": "Make the world more open and connected"
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing mission data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: res.partner record or False
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract mission data from value
            mission_value = str(value) if value else 'mission_update'
            
            # Try to find existing partner by entry_id or create new one
            existing_partner = Partner.search([('ref', '=', f"meta_{entry_id}")], limit=1)
            
            partner_vals = {
                'name': f"Meta Business - {entry_id}",
                'ref': f"meta_{entry_id}",
                'comment': f"Mission Event from Meta\n"
                          f"Object Type: {object_type}\n"
                          f"Entry ID: {entry_id}\n"
                          f"Entry Time: {entry_time}\n"
                          f"Mission Update: {mission_value}\n"
                          f"Webhook Event ID: {webhook_event.id}\n"
                          f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
            }
            
            if existing_partner:
                existing_partner.write(partner_vals)
                _logger.info(f"Updated Partner {existing_partner.id} with mission event")
                return existing_partner
            else:
                partner = Partner.create(partner_vals)
                _logger.info(f"Created Partner {partner.id} from mission event")
                return partner
                
        except Exception as e:
            _logger.exception(f"Error processing mission event: {str(e)}")
            return False

    def _process_messaging_referrals_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_referrals event - Create CRM Lead from messaging referral events.
        Messaging referrals represent customer referrals from ads or external sources.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_referrals"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_referrals",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "referral": {
                    "ref": "EXAMPLE_STRING_PAYLOAD",
                    "source": "SHORTLINK",
                    "type": "OPEN_THREAD",
                    "ads_context_data": {
                        "ad_title": "<TITLE_OF_THE_AD>",
                        "photo_url": "<URL_OF_THE_IMAGE_FROM_AD_THE_USER_IS_INTERESTED_IN>",
                        "video_url": "<THUMBNAIL_URL_OF_THE_VIDEO_FROM_THE_AD>",
                        "post_id": "<ID_OF_THE_POST>",
                        "product_id": "<PRODUCT_ID>"
                    }
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing referral data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract referral data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                referral = value.get('referral', {}) if isinstance(value.get('referral'), dict) else {}
                ref = referral.get('ref', '') if isinstance(referral, dict) else ''
                source = referral.get('source', '') if isinstance(referral, dict) else ''
                referral_type = referral.get('type', '') if isinstance(referral, dict) else ''
                ads_context_data = referral.get('ads_context_data', {}) if isinstance(referral.get('ads_context_data'), dict) else {}
                ad_title = ads_context_data.get('ad_title', '') if isinstance(ads_context_data, dict) else ''
                photo_url = ads_context_data.get('photo_url', '') if isinstance(ads_context_data, dict) else ''
                video_url = ads_context_data.get('video_url', '') if isinstance(ads_context_data, dict) else ''
                post_id = ads_context_data.get('post_id', '') if isinstance(ads_context_data, dict) else ''
                product_id = ads_context_data.get('product_id', '') if isinstance(ads_context_data, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = ref = source = referral_type = ad_title = photo_url = video_url = post_id = product_id = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[REFERRAL] {source.upper()} - {ref}",
                'description': f"Messaging Referrals Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Referral Ref: {ref}\n"
                              f"Source: {source}\n"
                              f"Type: {referral_type}\n"
                              f"Ad Title: {ad_title}\n"
                              f"Photo URL: {photo_url}\n"
                              f"Video URL: {video_url}\n"
                              f"Post ID: {post_id}\n"
                              f"Product ID: {product_id}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(ref),
                'priority': '2',  # High priority for customer referrals
                'tag_ids': [(0, 0, {'name': f'Referral: {source}'})],  # Add referral source tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_referrals event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_referrals event: {str(e)}")
            return False

    def _process_messaging_postbacks_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_postbacks event - Create CRM Lead from messaging postback events.
        Messaging postbacks represent customer interactions with call-to-action buttons.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_postbacks"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_postbacks",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "postback": {
                    "mid": "m_1457764197618:41d102a3e1ae206a38",
                    "title": "TITLE-FOR-THE-CTA",
                    "payload": "USER-DEFINED-PAYLOAD",
                    "referral": {
                        "ref": "USER-DEFINED-REFERRAL-PARAM",
                        "source": "SHORT-URL",
                        "type": "OPEN_THREAD"
                    }
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing postback data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract postback data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                postback = value.get('postback', {}) if isinstance(value.get('postback'), dict) else {}
                mid = postback.get('mid', '') if isinstance(postback, dict) else ''
                title = postback.get('title', '') if isinstance(postback, dict) else ''
                payload = postback.get('payload', '') if isinstance(postback, dict) else ''
                referral = postback.get('referral', {}) if isinstance(postback.get('referral'), dict) else {}
                ref = referral.get('ref', '') if isinstance(referral, dict) else ''
                source = referral.get('source', '') if isinstance(referral, dict) else ''
                referral_type = referral.get('type', '') if isinstance(referral, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = mid = title = payload = ref = source = referral_type = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[POSTBACK] {title} - {payload}",
                'description': f"Messaging Postbacks Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Message ID: {mid}\n"
                              f"Title: {title}\n"
                              f"Payload: {payload}\n"
                              f"Referral Ref: {ref}\n"
                              f"Source: {source}\n"
                              f"Referral Type: {referral_type}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(mid),
                'priority': '2',  # High priority for customer postback interactions
                'tag_ids': [(0, 0, {'name': f'Postback: {title}'})],  # Add postback title tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_postbacks event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_postbacks event: {str(e)}")
            return False

    def _process_messaging_policy_enforcement_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_policy_enforcement event - Create CRM Lead from messaging policy enforcement events.
        Messaging policy enforcement represents policy violations or warnings.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_policy_enforcement"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_policy_enforcement",
            "value": {
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "policy_enforcement": {
                    "action": "warning",
                    "reason": "Warning reason message"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing policy enforcement data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract policy enforcement data from value object
            if isinstance(value, dict):
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                policy_enforcement = value.get('policy_enforcement', {}) if isinstance(value.get('policy_enforcement'), dict) else {}
                action = policy_enforcement.get('action', '') if isinstance(policy_enforcement, dict) else ''
                reason = policy_enforcement.get('reason', '') if isinstance(policy_enforcement, dict) else ''
            else:
                # Fallback for non-object values
                recipient_id = timestamp = action = reason = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[POLICY] {action.upper()} - {recipient_id}",
                'description': f"Messaging Policy Enforcement Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Action: {action}\n"
                              f"Reason: {reason}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(recipient_id),
                'priority': '3',  # Very high priority for policy enforcement issues
                'tag_ids': [(0, 0, {'name': f'Policy: {action}'})],  # Add policy action tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_policy_enforcement event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_policy_enforcement event: {str(e)}")
            return False

    def _process_message_reactions_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_reactions event - Create CRM Lead from message reaction events.
        Message reactions represent customer emoji reactions to messages.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_reactions"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_reactions",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "reaction": {
                    "mid": "m_loPB-VGAnPg",
                    "action": "react",
                    "emoji": "ud83dudc4d",
                    "reaction": "like"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing reaction data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract reaction data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                reaction = value.get('reaction', {}) if isinstance(value.get('reaction'), dict) else {}
                mid = reaction.get('mid', '') if isinstance(reaction, dict) else ''
                action = reaction.get('action', '') if isinstance(reaction, dict) else ''
                emoji = reaction.get('emoji', '') if isinstance(reaction, dict) else ''
                reaction_type = reaction.get('reaction', '') if isinstance(reaction, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = mid = action = emoji = reaction_type = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[REACTION] {reaction_type.upper()} - {emoji}",
                'description': f"Message Reactions Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Message ID: {mid}\n"
                              f"Action: {action}\n"
                              f"Emoji: {emoji}\n"
                              f"Reaction: {reaction_type}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(mid),
                'priority': '1',  # Medium priority for message reactions
                'tag_ids': [(0, 0, {'name': f'Reaction: {reaction_type}'})],  # Add reaction type tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_reactions event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_reactions event: {str(e)}")
            return False

    def _process_message_reads_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_reads event - Create CRM Lead from message read events.
        Message reads represent message read confirmations with watermarks.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_reads"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_reads",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "read": {
                    "watermark": "1458668856253"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing read data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract read data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                read = value.get('read', {}) if isinstance(value.get('read'), dict) else {}
                watermark = read.get('watermark', '') if isinstance(read, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = watermark = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[READ] {watermark}",
                'description': f"Message Reads Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Watermark: {watermark}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(watermark),
                'priority': '0',  # Low priority for read confirmations
                'tag_ids': [(0, 0, {'name': 'Message Read'})],  # Add message read tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_reads event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_reads event: {str(e)}")
            return False

    def _process_message_template_status_update_event(self, entry, value, webhook_event, object_type=''):
        """
        Process message_template_status_update event - Create CRM Lead from message template status updates.
        Message template status updates represent approval/rejection of message templates.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "message_template_status_update"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "message_template_status_update",
            "value": {
                "business_id": 123456789,
                "timestamp": 1234567890,
                "changes": [
                    {
                        "field": "message_template_status_update",
                        "value": {
                            "event": "REJECTED",
                            "message_template_id": 123456789,
                            "message_template_name": "Messenger template",
                            "message_template_language": "en-US",
                            "reason": "ABUSIVE_CONTENT"
                        }
                    }
                ]
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing template status data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract template status data from value object
            if isinstance(value, dict):
                business_id = value.get('business_id', '')
                timestamp = value.get('timestamp', '')
                changes = value.get('changes', []) if isinstance(value.get('changes'), list) else []
                
                # Process first change if available
                change_info = {}
                if changes and len(changes) > 0 and isinstance(changes[0], dict):
                    change_value = changes[0].get('value', {}) if isinstance(changes[0].get('value'), dict) else {}
                    change_info = {
                        'event': change_value.get('event', ''),
                        'message_template_id': change_value.get('message_template_id', ''),
                        'message_template_name': change_value.get('message_template_name', ''),
                        'message_template_language': change_value.get('message_template_language', ''),
                        'reason': change_value.get('reason', '')
                    }
                
                event = change_info.get('event', '')
                template_id = change_info.get('message_template_id', '')
                template_name = change_info.get('message_template_name', '')
                reason = change_info.get('reason', '')
            else:
                # Fallback for non-object values
                business_id = timestamp = event = template_id = template_name = reason = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[TEMPLATE] {event.upper()} - {template_name}",
                'description': f"Message Template Status Update Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Business ID: {business_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Event: {event}\n"
                              f"Template ID: {template_id}\n"
                              f"Template Name: {template_name}\n"
                              f"Reason: {reason}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(template_id),
                'priority': '2',  # High priority for template status changes
                'tag_ids': [(0, 0, {'name': f'Template: {event}'})],  # Add template event tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from message_template_status_update event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing message_template_status_update event: {str(e)}")
            return False

    def _process_messages_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messages event - Create CRM Lead from general message events.
        Messages represent incoming customer messages with optional commands.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messages"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messages",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "message": {
                    "mid": "test_message_id",
                    "text": "test_message",
                    "commands": [
                        {
                            "name": "command123"
                        },
                        {
                            "name": "command456"
                        }
                    ]
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing message data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract message data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                message = value.get('message', {}) if isinstance(value.get('message'), dict) else {}
                mid = message.get('mid', '') if isinstance(message, dict) else ''
                text = message.get('text', '') if isinstance(message, dict) else ''
                commands = message.get('commands', []) if isinstance(message.get('commands'), list) else []
                
                # Build commands summary
                commands_text = ', '.join([cmd.get('name', '') for cmd in commands if isinstance(cmd, dict)]) if commands else 'None'
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = mid = text = commands_text = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[MESSAGE] {text[:50]}..." if len(text) > 50 else f"[MESSAGE] {text}",
                'description': f"Messages Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Message ID: {mid}\n"
                              f"Text: {text}\n"
                              f"Commands: {commands_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(mid),
                'priority': '2',  # High priority for customer messages
                'tag_ids': [(0, 0, {'name': 'Customer Message'})],  # Add customer message tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messages event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messages event: {str(e)}")
            return False

    def _process_messaging_account_linking_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_account_linking event - Create CRM Lead from account linking events.
        Account linking represents customer account linking/unlinking actions.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_account_linking"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_account_linking",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "account_linking": {
                    "status": "linked",
                    "authorization_code": "PASS_THROUGH_AUTHORIZATION_CODE"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing account linking data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract account linking data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                account_linking = value.get('account_linking', {}) if isinstance(value.get('account_linking'), dict) else {}
                status = account_linking.get('status', '') if isinstance(account_linking, dict) else ''
                authorization_code = account_linking.get('authorization_code', '') if isinstance(account_linking, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = status = authorization_code = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[ACCOUNT LINK] {status.upper()} - {sender_id}",
                'description': f"Messaging Account Linking Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Status: {status}\n"
                              f"Authorization Code: {authorization_code}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(sender_id),
                'priority': '2',  # High priority for account linking events
                'tag_ids': [(0, 0, {'name': f'Account: {status}'})],  # Add account status tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_account_linking event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_account_linking event: {str(e)}")
            return False

    def _process_messaging_customer_information_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_customer_information event - Create CRM Lead from customer information collection.
        Customer information represents structured data collection from customers.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_customer_information"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_customer_information",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "messaging_customer_information": {
                    "screens": [
                        {
                            "screen_id": "ID2",
                            "responses": [
                                {
                                    "key": "name",
                                    "value": "John Doe"
                                },
                                {
                                    "key": "email",
                                    "value": "email"
                                }
                            ]
                        }
                    ]
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing customer information data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract customer information data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                messaging_customer_info = value.get('messaging_customer_information', {}) if isinstance(value.get('messaging_customer_information'), dict) else {}
                screens = messaging_customer_info.get('screens', []) if isinstance(messaging_customer_info.get('screens'), list) else []
                
                # Build responses summary
                responses_summary = []
                for screen in screens:
                    if isinstance(screen, dict):
                        screen_id = screen.get('screen_id', '')
                        responses = screen.get('responses', []) if isinstance(screen.get('responses'), list) else []
                        for response in responses:
                            if isinstance(response, dict):
                                key = response.get('key', '')
                                val = response.get('value', '')
                                responses_summary.append(f"{key}: {val}")
                
                responses_text = '\n'.join(responses_summary) if responses_summary else 'No responses'
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = responses_text = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[CUSTOMER INFO] {sender_id}",
                'description': f"Messaging Customer Information Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Customer Responses:\n{responses_text}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(sender_id),
                'priority': '3',  # Very high priority for customer information collection
                'tag_ids': [(0, 0, {'name': 'Customer Information'})],  # Add customer info tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_customer_information event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_customer_information event: {str(e)}")
            return False

    def _process_messaging_handovers_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_handovers event - Create CRM Lead from conversation handover events.
        Handovers represent conversation transfers between different apps/agents.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_handovers"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_handovers",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "take_thread_control": {
                    "previous_owner_app_id": 1234567890,
                    "new_owner_app_id": 9876543210,
                    "metadata": "Information about the conversation"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing handover data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract handover data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                take_thread_control = value.get('take_thread_control', {}) if isinstance(value.get('take_thread_control'), dict) else {}
                previous_owner_app_id = take_thread_control.get('previous_owner_app_id', '') if isinstance(take_thread_control, dict) else ''
                new_owner_app_id = take_thread_control.get('new_owner_app_id', '') if isinstance(take_thread_control, dict) else ''
                metadata = take_thread_control.get('metadata', '') if isinstance(take_thread_control, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = previous_owner_app_id = new_owner_app_id = metadata = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[HANDOVER] {previous_owner_app_id} → {new_owner_app_id}",
                'description': f"Messaging Handovers Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Previous Owner App ID: {previous_owner_app_id}\n"
                              f"New Owner App ID: {new_owner_app_id}\n"
                              f"Metadata: {metadata}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(new_owner_app_id),
                'priority': '2',  # High priority for conversation handovers
                'tag_ids': [(0, 0, {'name': 'Conversation Handover'})],  # Add handover tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_handovers event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_handovers event: {str(e)}")
            return False

    def _process_messaging_in_thread_lead_form_submit_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_in_thread_lead_form_submit event - Create CRM Lead from in-thread lead form submissions.
        In-thread lead form submissions represent lead generation within conversations.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_in_thread_lead_form_submit"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_in_thread_lead_form_submit",
            "value": {
                "sender": {
                    "id": "123"
                },
                "recipient": {
                    "id": "456"
                },
                "timestamp": "1234567890",
                "form": {
                    "id": "789"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing form submission data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract form submission data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                form = value.get('form', {}) if isinstance(value.get('form'), dict) else {}
                form_id = form.get('id', '') if isinstance(form, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = form_id = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[LEAD FORM] {form_id} - {sender_id}",
                'description': f"Messaging In-Thread Lead Form Submit Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Form ID: {form_id}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(form_id),
                'priority': '3',  # Very high priority for lead form submissions
                'tag_ids': [(0, 0, {'name': 'Lead Form Submission'})],  # Add lead form tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_in_thread_lead_form_submit event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_in_thread_lead_form_submit event: {str(e)}")
            return False

    def _process_messaging_optins_event(self, entry, value, webhook_event, object_type=''):
        """
        Process messaging_optins event - Create CRM Lead from messaging opt-in events.
        Opt-ins represent customer consent for messaging communications.
        
        Sample minimal payload:
        {"entry": [{"id": "0", "time": 1769052520, "changes": [{"field": "messaging_optins"}]}], "object": "page"}
        
        Full payload template:
        {
            "field": "messaging_optins",
            "value": {
                "sender": {
                    "id": "12334"
                },
                "recipient": {
                    "id": "23245"
                },
                "timestamp": "1527459824",
                "optin": {
                    "type": "notification_messages",
                    "payload": "test_payload",
                    "notification_messages_token": "123",
                    "notification_messages_frequency": "daily",
                    "token_expiry_timestamp": 2592000000,
                    "user_token_status": "REFRESHED"
                }
            }
        }
        
        :param entry: dict - The webhook entry data
        :param value: dict - The event value containing opt-in data
        :param webhook_event: recordset - The webhook event record
        :param object_type: str - The object type from webhook
        :return: crm.lead record or False
        """
        try:
            CrmLead = request.env['crm.lead'].sudo()
            
            entry_id = entry.get('id', 'Unknown')
            entry_time = entry.get('time', 0)
            
            # Extract opt-in data from value object
            if isinstance(value, dict):
                sender_id = value.get('sender', {}).get('id', '') if isinstance(value.get('sender'), dict) else ''
                recipient_id = value.get('recipient', {}).get('id', '') if isinstance(value.get('recipient'), dict) else ''
                timestamp = value.get('timestamp', '')
                optin = value.get('optin', {}) if isinstance(value.get('optin'), dict) else {}
                optin_type = optin.get('type', '') if isinstance(optin, dict) else ''
                payload = optin.get('payload', '') if isinstance(optin, dict) else ''
                notification_messages_token = optin.get('notification_messages_token', '') if isinstance(optin, dict) else ''
                notification_messages_frequency = optin.get('notification_messages_frequency', '') if isinstance(optin, dict) else ''
                token_expiry_timestamp = optin.get('token_expiry_timestamp', '') if isinstance(optin, dict) else ''
                user_token_status = optin.get('user_token_status', '') if isinstance(optin, dict) else ''
            else:
                # Fallback for non-object values
                sender_id = recipient_id = timestamp = optin_type = payload = notification_messages_token = notification_messages_frequency = token_expiry_timestamp = user_token_status = str(value) if value else 'unknown'
            
            lead_vals = {
                'name': f"[OPT-IN] {optin_type.upper()} - {sender_id}",
                'description': f"Messaging Optins Event from Meta\n"
                              f"Object Type: {object_type}\n"
                              f"Entry ID: {entry_id}\n"
                              f"Entry Time: {entry_time}\n"
                              f"Sender ID: {sender_id}\n"
                              f"Recipient ID: {recipient_id}\n"
                              f"Timestamp: {timestamp}\n"
                              f"Opt-in Type: {optin_type}\n"
                              f"Payload: {payload}\n"
                              f"Notification Token: {notification_messages_token}\n"
                              f"Frequency: {notification_messages_frequency}\n"
                              f"Token Expiry: {token_expiry_timestamp}\n"
                              f"User Token Status: {user_token_status}\n"
                              f"Webhook Event ID: {webhook_event.id}\n"
                              f"Raw Data: {json.dumps(value, indent=2) if value else 'N/A'}",
                'meta_lead_id': str(sender_id),
                'priority': '2',  # High priority for opt-in events
                'tag_ids': [(0, 0, {'name': f'Opt-in: {optin_type}'})],  # Add opt-in type tag
            }
            
            lead = CrmLead.create(lead_vals)
            _logger.info(f"Created CRM Lead {lead.id} from messaging_optins event")
            return lead
                
        except Exception as e:
            _logger.exception(f"Error processing messaging_optins event: {str(e)}")
            return False
        
    @http.route('/ads_sync/webhook/<string:subscription_id>', 
                type='http', auth='public', methods=['GET'], csrf=False)
    def webhook_verify(self, subscription_id, **kwargs):
        """
        Handle webhook verification requests (GET).
        Meta sends a GET request to verify the webhook URL.
        """
        subscription = request.env['ads.subscription'].sudo().search([
            ('subscription_id', '=', subscription_id),
            ('state', '=', 'subscribed')
        ], limit=1)
        
        if not subscription:
            return Response('Subscription not found', status=404)
        
        # Meta webhook verification
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')
        
        if mode == 'subscribe' and token == subscription.webhook_verify_token:
            _logger.info(f"Webhook verified for subscription: {subscription_id}")
            return Response(challenge, status=200)
        
        return Response('Verification failed', status=403)

    @http.route('/ads_sync/webhook/<string:subscription_id>', 
                type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def webhook_receive(self, subscription_id, **kwargs):
        """
        Handle incoming webhook events (POST).
        """
        subscription = request.env['ads.subscription'].sudo().search([
            ('subscription_id', '=', subscription_id),
            ('state', '=', 'subscribed')
        ], limit=1)
        
        if not subscription:
            return {'error': 'Subscription not found'}, 404
        
        # Get the JSON payload
        data = request.jsonrequest
        
        _logger.info(f"Received webhook event for {subscription_id}: {json.dumps(data)}")
        
        # Process the webhook event
        # This can be extended based on specific event types
        
        return {'status': 'received'}

    @http.route('/ads_sync/api/subscribe', type='jsonrpc', auth='user', methods=['POST'])
    def api_subscribe(self, **kwargs):
        """
        API endpoint to create a subscription by calling the external server.
        """
        data = request.jsonrequest
        
        required_fields = ['name', 'platform']
        for field in required_fields:
            if not data.get(field):
                return {'error': f'Missing required field: {field}'}
        
        # Build payload for external server
        payload = {
            'name': data['name'],
            'platform': data['platform'],
        }
        
        if data['platform'] == 'meta':
            meta_creds = data.get('meta_credentials', {})
            if not meta_creds.get('access_token'):
                return {'error': 'Missing meta_credentials.access_token'}
            if not meta_creds.get('pixel_id'):
                return {'error': 'Missing meta_credentials.pixel_id'}
            
            payload['meta_credentials'] = {
                'access_token': meta_creds.get('access_token'),
                'pixel_id': meta_creds.get('pixel_id'),
                'test_event_code': meta_creds.get('test_event_code'),
            }
        
        # Call external server
        try:
            server_url = self._get_server_url()
            response = requests.post(
                f"{server_url}/subscribe",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as e:
            _logger.error(f"Failed to subscribe to external server: {e}")
            return {'error': f'External server error: {str(e)}'}
        
        # Store subscription locally
        vals = {
            'name': data['name'],
            'platform': data['platform'],
            'subscription_id': result.get('subscription_id'),
            'api_key': result.get('api_key'),
            'webhook_verify_token': result.get('webhook_verify_token'),
            'callback_url': result.get('callback_url'),
        }
        
        if data['platform'] == 'meta':
            vals.update({
                'meta_access_token': meta_creds.get('access_token'),
                'meta_pixel_id': meta_creds.get('pixel_id'),
                'meta_app_secret': meta_creds.get('app_secret'),
                'meta_test_event_code': meta_creds.get('test_event_code'),
            })
        
        subscription = request.env['ads.subscription'].create(vals)
        subscription.write({'state': 'subscribed'})
        
        return result
