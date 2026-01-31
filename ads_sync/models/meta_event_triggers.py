# -*- coding: utf-8 -*-
"""
Model extensions to trigger Meta events when specific actions occur in Odoo.

These extensions hook into existing Odoo models and check if the corresponding
Meta event is active in meta.event.config before pushing events to Meta CAPI.
"""

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


def _safe_trigger_event(env, technical_name, record, extra_data=None):
    """Safely trigger a Meta event, handling exceptions gracefully."""
    try:
        MetaEventConfig = env.get('meta.event.config')
        if MetaEventConfig is None:
            _logger.debug(f"[MetaEventTrigger] meta.event.config model not available")
            return None
        
        result = MetaEventConfig.sudo().trigger_event(technical_name, record, extra_data)
        return result
    except Exception as e:
        _logger.exception(f"[MetaEventTrigger] Error triggering event '{technical_name}': {e}")
        return None


class CrmLeadMetaEvents(models.Model):
    """Extend crm.lead to trigger Meta events on key actions."""
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'Lead' event when a new lead is created."""
        records = super().create(vals_list)
        
        for record in records:
            _logger.info(f"[MetaEventTrigger] New lead created: {record.id} - {record.name}")
            try:
                result = self.env['meta.event.config'].sudo().trigger_event(
                    'lead', 
                    record,
                    extra_data={'creation_source': 'odoo_crm'}
                )
                _logger.info(f"[MetaEventTrigger] Lead event result: {result}")
            except Exception as e:
                _logger.exception(f"[MetaEventTrigger] Failed to trigger Meta 'lead' event for lead {record.id}: {e}")
        
        return records

    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        """Trigger 'QualifiedLead' event when lead is converted to opportunity."""
        res = super().convert_opportunity(partner_id, user_ids=user_ids, team_id=team_id)
        
        for record in self:
            _logger.info(f"[MetaEventTrigger] Lead converted to opportunity: {record.id} - {record.name}")
            try:
                result = self.env['meta.event.config'].sudo().trigger_event(
                    'qualified_lead',
                    record,
                    extra_data={'conversion_type': 'lead_to_opportunity'}
                )
                _logger.info(f"[MetaEventTrigger] QualifiedLead event result: {result}")
            except Exception as e:
                _logger.exception(f"[MetaEventTrigger] Failed to trigger Meta 'qualified_lead' event for lead {record.id}: {e}")
        
        return res

    def action_set_won_rainbowman(self):
        """Trigger 'ConvertedLead' event when opportunity is marked as Won."""
        res = super().action_set_won_rainbowman()
        
        for record in self:
            _logger.info(f"[MetaEventTrigger] Opportunity marked as Won: {record.id} - {record.name}")
            try:
                result = self.env['meta.event.config'].sudo().trigger_event(
                    'converted_lead',
                    record,
                    extra_data={'outcome': 'won'}
                )
                _logger.info(f"[MetaEventTrigger] ConvertedLead event result: {result}")
            except Exception as e:
                _logger.exception(f"[MetaEventTrigger] Failed to trigger Meta 'converted_lead' event for lead {record.id}: {e}")
        
        return res


class SaleOrderMetaEvents(models.Model):
    """Extend sale.order to trigger Meta events on key actions."""
    _inherit = 'sale.order'

    def action_confirm(self):
        """Trigger 'Purchase' event when sale order is confirmed."""
        res = super().action_confirm()
        
        for record in self:
            _logger.info(f"[MetaEventTrigger] Sale order confirmed: {record.id} - {record.name}")
            try:
                # Build items list for contents
                contents = []
                for line in record.order_line:
                    contents.append({
                        'id': line.product_id.default_code or str(line.product_id.id),
                        'quantity': int(line.product_uom_qty),
                        'item_price': float(line.price_unit),
                    })
                
                result = self.env['meta.event.config'].sudo().trigger_event(
                    'purchase',
                    record,
                    extra_data={
                        'contents': contents,
                        'content_type': 'product',
                    }
                )
                _logger.info(f"[MetaEventTrigger] Purchase event result: {result}")
            except Exception as e:
                _logger.exception(f"[MetaEventTrigger] Failed to trigger Meta 'purchase' event for order {record.id}: {e}")
        
        return res

    def action_quotation_sent(self):
        """Trigger 'InitiateCheckout' event when quotation is sent."""
        res = super().action_quotation_sent()
        
        for record in self:
            _logger.info(f"[MetaEventTrigger] Quotation sent: {record.id} - {record.name}")
            try:
                result = self.env['meta.event.config'].sudo().trigger_event(
                    'initiate_checkout',
                    record,
                    extra_data={'stage': 'quotation_sent'}
                )
                _logger.info(f"[MetaEventTrigger] InitiateCheckout event result: {result}")
            except Exception as e:
                _logger.exception(f"[MetaEventTrigger] Failed to trigger Meta 'initiate_checkout' event for order {record.id}: {e}")
        
        return res


class ResPartnerMetaEvents(models.Model):
    """Extend res.partner to trigger Meta events on contact creation."""
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'Contact' event when a new contact is created."""
        records = super().create(vals_list)
        
        for record in records:
            _logger.info(f"[MetaEventTrigger] New partner created: {record.id} - {record.name}")
            try:
                # Trigger for all contacts that have name (to avoid system-created records)
                if record.name:
                    _logger.info(f"[MetaEventTrigger] Attempting to trigger 'contact' event for partner {record.id}")
                    result = self.env['meta.event.config'].sudo().trigger_event(
                        'contact',
                        record,
                        extra_data={'contact_type': 'company' if record.is_company else 'individual'}
                    )
                    if result:
                        _logger.info(f"[MetaEventTrigger] Contact event result: {result}")
                    else:
                        _logger.info(f"[MetaEventTrigger] Contact event not active or no result")
            except Exception as e:
                _logger.exception(f"[MetaEventTrigger] Failed to trigger Meta 'contact' event for partner {record.id}: {e}")
        
        return records


class ResUsersMetaEvents(models.Model):
    """Extend res.users to trigger Meta events on user registration."""
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'CompleteRegistration' event when a new user is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                # Only trigger for portal/public users (not internal users)
                if record.has_group('base.group_portal') or record.has_group('base.group_public'):
                    self.env['meta.event.config'].sudo().trigger_event(
                        'complete_registration',
                        record,
                        extra_data={'registration_type': 'portal_user'}
                    )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'complete_registration' event for user {record.id}: {e}")
        
        return records


class AccountMoveMetaEvents(models.Model):
    """Extend account.move to trigger Meta events on invoice posting."""
    _inherit = 'account.move'

    def action_post(self):
        """Trigger 'AddPaymentInfo' event when invoice is posted."""
        res = super().action_post()
        
        for record in self:
            # Only trigger for customer invoices
            if record.move_type in ('out_invoice', 'out_refund'):
                try:
                    self.env['meta.event.config'].sudo().trigger_event(
                        'add_payment_info',
                        record,
                        extra_data={
                            'invoice_type': record.move_type,
                            'payment_state': record.payment_state,
                        }
                    )
                except Exception as e:
                    _logger.warning(f"Failed to trigger Meta 'add_payment_info' event for invoice {record.id}: {e}")
        
        return res


class CalendarEventMetaEvents(models.Model):
    """Extend calendar.event to trigger Meta events on meeting scheduling."""
    _inherit = 'calendar.event'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'Schedule' event when a meeting is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                # Only trigger if there are attendees (real meetings)
                if record.partner_ids:
                    self.env['meta.event.config'].sudo().trigger_event(
                        'schedule',
                        record,
                        extra_data={
                            'event_type': 'meeting',
                            'attendee_count': len(record.partner_ids),
                        }
                    )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'schedule' event for calendar event {record.id}: {e}")
        
        return records


class SaleOrderLineMetaEvents(models.Model):
    """Extend sale.order.line to trigger Meta events on cart actions."""
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'AddToCart' event when a new order line is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                # Only trigger if it's a real product line (not service/delivery)
                if record.product_id and record.product_id.type == 'product':
                    _safe_trigger_event(
                        self.env,
                        'add_to_cart',
                        record,
                        extra_data={
                            'product_id': record.product_id.id,
                            'product_name': record.product_id.name,
                            'quantity': record.product_uom_qty,
                            'price': record.price_unit,
                        }
                    )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'add_to_cart' event for order line {record.id}: {e}")
        
        return records


class ProductProductMetaEvents(models.Model):
    """Extend product.product to trigger Meta events on product views."""
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'ViewContent' event when a new product is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                _safe_trigger_event(
                    self.env,
                    'view_content',
                    record,
                    extra_data={
                        'content_type': 'product',
                        'product_category': record.categ_id.name if record.categ_id else '',
                    }
                )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'view_content' event for product {record.id}: {e}")
        
        return records


class AccountPaymentMetaEvents(models.Model):
    """Extend account.payment to trigger Meta events on payment actions."""
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'AddPaymentInfo' event when a payment is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                _safe_trigger_event(
                    self.env,
                    'add_payment_info',
                    record,
                    extra_data={
                        'payment_type': record.payment_type,
                        'amount': record.amount,
                        'currency': record.currency_id.name,
                    }
                )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'add_payment_info' event for payment {record.id}: {e}")
        
        return records


class ResPartnerUpdateMetaEvents(models.Model):
    """Extend res.partner to trigger Meta events on profile updates."""
    _inherit = 'res.partner'

    def write(self, vals):
        """Trigger 'UpdateProfile' event when partner is updated."""
        result = super().write(vals)
        
        # Only trigger if significant fields were updated
        significant_fields = ['name', 'email', 'phone', 'mobile', 'street', 'city', 'country_id']
        if any(field in vals for field in significant_fields):
            for record in self:
                try:
                    _safe_trigger_event(
                        self.env,
                        'update_profile',
                        record,
                        extra_data={
                            'updated_fields': list(vals.keys()),
                            'partner_type': 'company' if record.is_company else 'individual',
                        }
                    )
                except Exception as e:
                    _logger.warning(f"Failed to trigger Meta 'update_profile' event for partner {record.id}: {e}")
        
        return result

class SaleOrderInitiateCheckoutMetaEvents(models.Model):
    """Extend sale.order to trigger Meta events on order initiation."""
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'InitiateCheckout' event when a sale order is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                # Only trigger for orders with lines
                if record.order_line:
                    _safe_trigger_event(
                        self.env,
                        'initiate_checkout',
                        record,
                        extra_data={
                            'order_line_count': len(record.order_line),
                            'total_amount': record.amount_total,
                            'creation_source': 'backend',
                        }
                    )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'initiate_checkout' event for order {record.id}: {e}")
        
        return records


class AccountMovePaymentMetaEvents(models.Model):
    """Extend account.move to trigger Meta events on invoice payment."""
    _inherit = 'account.move'

    def action_post(self):
        """Trigger 'AddPaymentInfo' event when invoice is posted."""
        result = super().action_post()
        
        for record in self:
            # Only for customer invoices
            if record.move_type in ('out_invoice', 'out_refund'):
                try:
                    _safe_trigger_event(
                        self.env,
                        'add_payment_info',
                        record,
                        extra_data={
                            'invoice_type': record.move_type,
                            'amount': record.amount_total,
                            'posted_date': record.date,
                        }
                    )
                except Exception as e:
                    _logger.warning(f"Failed to trigger Meta 'add_payment_info' event for invoice {record.id}: {e}")
        
        return result


class CrmLeadSearchMetaEvents(models.Model):
    """Extend crm.lead to trigger Meta events on search actions."""
    _inherit = 'crm.lead'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Trigger 'Search' event when leads are searched."""
        result = super().search(args, offset=offset, limit=limit, order=order, count=count)
        
        # Only trigger if there are actual search results and not just count
        if not count and result and len(result) > 0:
            try:
                # Create a dummy record for the search event
                search_record = self.env['crm.lead'].new({
                    'name': f'Search Results ({len(result)} leads)',
                    'description': f'Search args: {args}',
                })
                _safe_trigger_event(
                    self.env,
                    'search',
                    search_record,
                    extra_data={
                        'search_type': 'crm_lead',
                        'result_count': len(result),
                        'search_args': str(args),
                    }
                )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'search' event: {e}")
        
        return result


class ProductCategoryMetaEvents(models.Model):
    """Extend product.category to trigger Meta events on category views."""
    _inherit = 'product.category'

    @api.model_create_multi
    def create(self, vals_list):
        """Trigger 'ViewCategory' event when a category is created."""
        records = super().create(vals_list)
        
        for record in records:
            try:
                _safe_trigger_event(
                    self.env,
                    'view_category',
                    record,
                    extra_data={
                        'category_name': record.name,
                        'parent_category': record.parent_id.name if record.parent_id else '',
                    }
                )
            except Exception as e:
                _logger.warning(f"Failed to trigger Meta 'view_category' event for category {record.id}: {e}")
        
        return records
