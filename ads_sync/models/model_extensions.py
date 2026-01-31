# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrmLeadMetaEvent(models.Model):
    """Add Meta event control to CRM Lead/Opportunity"""
    _inherit = 'crm.lead'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this lead/opportunity will not trigger Meta conversion events'
    )


class SaleOrderMetaEvent(models.Model):
    """Add Meta event control to Sale Order"""
    _inherit = 'sale.order'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this sale order will not trigger Meta conversion events'
    )


class ResPartnerMetaEvent(models.Model):
    """Add Meta event control to Contact/Partner"""
    _inherit = 'res.partner'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this contact will not trigger Meta conversion events'
    )


class ResUsersMetaEvent(models.Model):
    """Add Meta event control to Users"""
    _inherit = 'res.users'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this user will not trigger Meta conversion events'
    )


class AccountMoveMetaEvent(models.Model):
    """Add Meta event control to Invoice/Bill"""
    _inherit = 'account.move'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this invoice/bill will not trigger Meta conversion events'
    )


class SaleOrderLineMetaEvent(models.Model):
    """Add Meta event control to Sale Order Line"""
    _inherit = 'sale.order.line'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this order line will not trigger Meta conversion events'
    )


class ProductProductMetaEvent(models.Model):
    """Add Meta event control to Product"""
    _inherit = 'product.product'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this product will not trigger Meta conversion events'
    )


class AccountPaymentMetaEvent(models.Model):
    """Add Meta event control to Payment"""
    _inherit = 'account.payment'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this payment will not trigger Meta conversion events'
    )

class ProductCategoryMetaEvent(models.Model):
    """Add Meta event control to Product Category"""
    _inherit = 'product.category'
    
    meta_event_enabled = fields.Boolean(
        string='Enable Meta Event Tracking',
        default=True,
        help='When unchecked, this product category will not trigger Meta conversion events'
    )