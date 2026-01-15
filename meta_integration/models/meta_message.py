import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MetaMessage(models.Model):
    _name = 'meta.message'
    _description = 'Meta Incoming Messages'
    _order = 'timestamp desc, id desc'

    # Message identifiers
    message_id = fields.Char(string='Message ID', index=True, help='Meta message mid')
    sender_id = fields.Char(string='Sender ID', index=True, help='Sender user ID from Meta')
    recipient_id = fields.Char(string='Recipient ID', index=True, help='Recipient page/user ID')
    
    # Message content
    text = fields.Text(string='Message Text')
    timestamp = fields.Datetime(string='Timestamp', help='Message timestamp from Meta')
    timestamp_raw = fields.Char(string='Raw Timestamp', help='Original Unix timestamp string')
    
    # Commands (stored as JSON)
    commands = fields.Text(string='Commands', help='JSON array of commands')
    
    # Raw payload for debugging
    raw_payload = fields.Text(string='Raw Payload', help='Full JSON payload received')
    
    # Processing status
    state = fields.Selection([
        ('received', 'Received'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ], string='Status', default='received', index=True)
    
    error_message = fields.Text(string='Error Message')

    @api.model
    def create_from_webhook(self, message_data):
        """
        Create a message record from webhook payload.
        
        :param message_data: dict with structure:
            {
                "sender": {"id": "12334"},
                "recipient": {"id": "23245"},
                "timestamp": "1527459824",
                "message": {
                    "mid": "test_message_id",
                    "text": "test_message",
                    "commands": [{"name": "command123"}, ...]
                }
            }
        :return: created meta.message record
        """
        import json
        from datetime import datetime
        
        try:
            sender = message_data.get('sender', {})
            recipient = message_data.get('recipient', {})
            message = message_data.get('message', {})
            timestamp_raw = message_data.get('timestamp', '')
            
            # Convert Unix timestamp to datetime
            timestamp_dt = False
            if timestamp_raw:
                try:
                    timestamp_dt = datetime.fromtimestamp(int(timestamp_raw))
                except (ValueError, TypeError):
                    _logger.warning(f"Could not parse timestamp: {timestamp_raw}")
            
            # Extract commands as JSON string
            commands = message.get('commands', [])
            commands_json = json.dumps(commands) if commands else ''
            
            vals = {
                'message_id': message.get('mid', ''),
                'sender_id': sender.get('id', ''),
                'recipient_id': recipient.get('id', ''),
                'text': message.get('text', ''),
                'timestamp': timestamp_dt,
                'timestamp_raw': timestamp_raw,
                'commands': commands_json,
                'raw_payload': json.dumps(message_data),
                'state': 'received',
            }
            
            record = self.create(vals)
            _logger.info(f"Created meta.message record ID={record.id}, message_id={record.message_id}")
            return record
            
        except Exception as e:
            _logger.error(f"Failed to create meta.message: {str(e)}")
            raise
