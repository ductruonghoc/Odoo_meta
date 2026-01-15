{
    'name': 'Meta Integration',
    'version': '1.3',
    'category': 'Tools',
    'summary': 'Meta (Facebook) Webhook & CAPI Integration',
    'depends': ['base', 'web', 'sale', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/meta_message_views.xml',
        'views/meta_outgoing_event_views.xml',
        # 'views/crm_lead_views.xml',  # Temporarily disabled - enable after first upgrade
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}