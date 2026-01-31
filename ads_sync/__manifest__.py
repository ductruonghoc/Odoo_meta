# -*- coding: utf-8 -*-
{
    'name': 'Ads Sync',
    'version': '1.0.0',
    'category': 'Marketing/Marketing',
    'summary': 'Synchronize conversion events and webhooks with Meta (Facebook) and ad platforms',
    'description': """
Ads Sync Module
===============
This module streamlines the integration between Odoo and external advertising platforms.

Key Features:
-------------
* **Webhook Management**: Create and manage subscriptions to advertising platform webhooks.
* **Meta Pixel Integration**: Seamlessly manage Meta (Facebook) Pixel tracking.
* **Conversion Sync**: Push Odoo events (CRM, Sales, Accounting) back to ad platforms to optimize ad spend.
* **Monitoring**: Integrated dashboards to monitor event push status and errors.
    """,
    'author': 'Evan',
    'website': 'https://www.eonsr.com',
    'license': 'LGPL-3',
    'depends': [
        'base', 
        'web', 
        'mail', 
        'crm', 
        'sale', 
        'account', 
        'calendar', 
        'mass_mailing'
    ],
    'external_dependencies': {
        'python': ['facebook_business'],  # Recommended if using the Meta SDK
    },
    'data': [
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'data/meta_event_config_data.xml',
        'views/ads_subscription_views.xml',
        'views/meta_webhook_event_views.xml',
        'views/meta_event_push_views.xml',
        'views/meta_event_push_views_monitor.xml',
        'views/meta_event_config_views.xml',
        'views/view_extensions.xml',
        'views/menu_views.xml', # Best practice: Menus last so they reference existing views
    ],
    'assets': {
        'web.assets_backend': [
            # Add any custom CSS/JS for your monitoring views here
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
    'post_init_hook': 'post_init_hook',
}