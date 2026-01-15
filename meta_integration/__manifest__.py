{
    'name': 'Meta Integration',
    'version': '1.3',
    'category': 'Tools',
    'summary': 'Meta (Facebook) Webhook & CAPI Integration',
    
    # --- CÁC THÔNG TIN BỔ SUNG ---
    'author': 'Evan',
    'website': 'https://www.eonsr.com', # Nên có nếu có author
    'description': 
        """
        Mô tả chi tiết về module:
        - Tích hợp Facebook Webhook.
        - Cấu hình Conversion API (CAPI).
        - Theo dõi sự kiện CRM và Sale.
        """,
    'price': 189.00,        # Giá trị số (không để trong ngoặc kép)
    'currency': 'USD',     # Odoo App Store thường mặc định dùng EUR hoặc USD
    'license': 'OPL-1',    # LƯU Ý: Nếu bán có phí, bạn nên dùng license 'OPL-1' thay vì 'LGPL-3'
    # ----------------------------

    'depends': ['base', 'web', 'sale', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/meta_message_views.xml',
        'views/meta_outgoing_event_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}