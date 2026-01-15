import hashlib
import requests
import time
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        _logger.info("=== META CAPI: action_confirm CALLED, orders=%s ===" % self.ids)
        
        # 1. Gọi hàm gốc của Odoo để xác nhận đơn hàng
        res = super(SaleOrder, self).action_confirm()
        
        _logger.info("=== META CAPI: After super(), starting CAPI calls ===")
        
        # 2. Kích hoạt gửi dữ liệu sang Meta CAPI
        for order in self:
            _logger.info("=== META CAPI: Calling _send_to_meta_capi for order %s ===" % order.name)
            order._send_to_meta_capi()
        return res

    def _send_to_meta_capi(self):
        _logger.info("=== META CAPI: _send_to_meta_capi STARTED for %s ===" % self.name)
        # Thông số cấu hình (Nên để trong System Parameters)
        ACCESS_TOKEN = 'EAAKWCZAoKZBZB0BQWVauSCt2bZCAkZCeoM6ZAsBPLZA5kWVmWkkPdeHIgRZCchXfXd7W2Md2xCo67Rz3rd3aJ0kkPpGGAXaFdYGaKcXucZBr7JXiHFqBkQdisvJoKvj33o5g28GylyZC9q9cXcrtA6Oh9kO1hY8OdOckaACIAJnvT3c3cF5iUYeIs5ZBGrmhfoxj9ilL1KJAva7nHZBZBkeqqEzZCnEjVpuRUBgU38egZA0'
        PIXEL_ID = '1572264680686179'
        TEST_CODE = 'TEST42631'  # Lấy trong tab Test Events của Meta

        # Hash dữ liệu khách hàng (Email)
        email = self.partner_id.email or ""
        hashed_email = hashlib.sha256(email.lower().encode()).hexdigest()

        # Chuẩn bị dữ liệu sản phẩm (Catalog Mapping)
        items = []
        for line in self.order_line:
            items.append({
                'id': line.product_id.default_code or str(line.product_id.id),
                'quantity': int(line.product_uom_qty),
                'item_price': line.price_unit
            })

        # Payload gửi sang Meta
        payload = {
            "data": [{
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "action_source": "email",
                "user_data": {
                    "em": [hashed_email]
                },
                "custom_data": {
                    "currency": self.currency_id.name,
                    "value": self.amount_total,
                    "contents": items,
                    "content_type": "product"
                },
            }],
            "test_event_code": TEST_CODE  # Chỉ dùng khi đang TEST
        }

        url = f"https://graph.facebook.com/v24.0/{PIXEL_ID}/events?access_token={ACCESS_TOKEN}"
        
        _logger.info("=== META CAPI: Sending payload to %s ===" % url[:50])
        _logger.info("=== META CAPI: Payload = %s ===" % payload)
        
        # Create outgoing event record
        outgoing_event = self.env['meta.outgoing.event'].sudo().create_from_sale_order(
            order=self,
            event_name='Purchase',
            payload=payload,
            pixel_id=PIXEL_ID
        )
        
        try:
            response = requests.post(url, json=payload)
            _logger.info("=== META CAPI: Response status=%s, body=%s ===" % (response.status_code, response.text))
            
            # Update outgoing event with response
            if response.status_code == 200:
                outgoing_event.mark_success(response.status_code, response.text)
            else:
                outgoing_event.mark_failed(
                    error_message=f"HTTP {response.status_code}",
                    response_status=response.status_code,
                    response_body=response.text
                )
        except Exception as e:
            _logger.error("=== META CAPI: Error = %s ===" % str(e))
            outgoing_event.mark_failed(error_message=str(e))