# -*- coding: utf-8 -*-

import json
from odoo import models, fields, api


class MetaWebhookEvent(models.Model):
    _name = 'ads.meta.webhook.event'
    _description = 'Meta Webhook Event'
    _order = 'received_at desc'

    name = fields.Char(
        string='Event Name',
        compute='_compute_name',
        store=True,
    )
    
    event_type = fields.Char(
        string='Event Type',
        help='Type of the webhook event (e.g., leadgen, messages, etc.)'
    )
    
    object_type = fields.Char(
        string='Object Type',
        help='The object type from Meta (e.g., page, user, etc.)'
    )
    
    entry_id = fields.Char(
        string='Entry ID',
        help='The ID from the entry in the webhook payload'
    )
    
    payload_json = fields.Text(
        string='Raw Payload (JSON)',
        required=True,
        help='The complete raw JSON payload received from Meta'
    )
    
    payload_formatted = fields.Text(
        string='Formatted Payload',
        compute='_compute_payload_formatted',
        help='Pretty-printed JSON for display'
    )
    
    received_at = fields.Datetime(
        string='Received At',
        default=fields.Datetime.now,
        readonly=True,
    )
    
    source_ip = fields.Char(
        string='Source IP',
        help='IP address from which the webhook was received'
    )
    
    state = fields.Selection([
        ('received', 'Received'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('error', 'Error'),
        ('ignored', 'Ignored'),
    ], string='Status', default='received', readonly=True)
    
    processing_notes = fields.Text(
        string='Processing Notes',
        help='Notes or error messages from processing'
    )
    
    subscription_id = fields.Many2one(
        'ads.subscription',
        string='Subscription',
        ondelete='set null',
        help='Related subscription if identified'
    )

    @api.depends('event_type', 'received_at')
    def _compute_name(self):
        for record in self:
            event_type = record.event_type or 'webhook'
            timestamp = record.received_at.strftime('%Y-%m-%d %H:%M:%S') if record.received_at else ''
            record.name = f"{event_type} - {timestamp}"

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

    def action_mark_processed(self):
        """Mark the event as processed."""
        self.write({'state': 'processed'})
    
    def action_mark_ignored(self):
        """Mark the event as ignored."""
        self.write({'state': 'ignored'})
    
    def action_reprocess(self):
        """Reset to received state for reprocessing."""
        self.write({'state': 'received', 'processing_notes': ''})

    @api.model
    def create_from_webhook(self, payload, source_ip=None, subscription=None):
        """
        Create a webhook event record from the received payload.
        
        :param payload: dict - The JSON payload from the webhook
        :param source_ip: str - The source IP address
        :param subscription: recordset - Related ads.subscription record
        :return: recordset - Created ads.meta.webhook.event record
        """
        # Extract event details from Meta webhook format
        object_type = payload.get('object', '')
        event_type = ''
        entry_id = ''
        
        # Try to extract event type from the entry
        entries = payload.get('entry', [])
        if entries and isinstance(entries, list):
            first_entry = entries[0]
            entry_id = str(first_entry.get('id', ''))
            
            # Check for different event types
            if 'changes' in first_entry:
                changes = first_entry.get('changes', [])
                if changes and isinstance(changes, list):
                    event_type = changes[0].get('field', '')
            elif 'messaging' in first_entry:
                event_type = 'messaging'
            elif 'leadgen' in first_entry:
                event_type = 'leadgen'
        
        # If no specific event type found, use the object type
        if not event_type:
            event_type = object_type
        
        values = {
            'event_type': event_type,
            'object_type': object_type,
            'entry_id': entry_id,
            'payload_json': json.dumps(payload, ensure_ascii=False),
            'source_ip': source_ip,
            'state': 'received',
        }
        
        if subscription:
            values['subscription_id'] = subscription.id
        
        return self.create(values)
