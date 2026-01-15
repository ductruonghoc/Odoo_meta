# -*- coding: utf-8 -*-
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase


class TestSaleOrderMetaIntegration(TransactionCase):
    """Test cases for Meta CAPI integration with Sale Order"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Tạo partner test
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'test@example.com',
        })
        # Tạo product test
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
        })

    def _create_sale_order(self):
        """Helper method để tạo sale order test"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        return sale_order

    def test_sale_order_creation(self):
        """Test tạo sale order thành công"""
        sale_order = self._create_sale_order()
        self.assertTrue(sale_order, "Sale order should be created")
        self.assertEqual(sale_order.partner_id, self.partner)
        self.assertEqual(len(sale_order.order_line), 1)

    def test_sale_order_amount_total(self):
        """Test tính toán tổng tiền đơn hàng"""
        sale_order = self._create_sale_order()
        # 2 sản phẩm x 100 = 200
        self.assertEqual(sale_order.amount_total, 200.0)

    @patch('odoo.addons.meta_integration.models.sale_order.requests.post')
    def test_action_confirm_calls_meta_capi(self, mock_post):
        """Test xác nhận đơn hàng gọi Meta CAPI"""
        mock_post.return_value = MagicMock(status_code=200)
        
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        
        # Kiểm tra requests.post đã được gọi
        self.assertTrue(mock_post.called, "Meta CAPI should be called on confirm")

    @patch('odoo.addons.meta_integration.models.sale_order.requests.post')
    def test_meta_capi_payload_structure(self, mock_post):
        """Test cấu trúc payload gửi đến Meta CAPI"""
        mock_post.return_value = MagicMock(status_code=200)
        
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        
        # Lấy payload từ lần gọi cuối cùng
        call_args = mock_post.call_args
        payload = call_args.kwargs.get('json') or call_args[1].get('json')
        
        # Kiểm tra cấu trúc payload
        self.assertIn('data', payload)
        self.assertEqual(len(payload['data']), 1)
        
        event_data = payload['data'][0]
        self.assertEqual(event_data['event_name'], 'Purchase')
        self.assertEqual(event_data['action_source'], 'email')
        self.assertIn('user_data', event_data)
        self.assertIn('custom_data', event_data)

    @patch('odoo.addons.meta_integration.models.sale_order.requests.post')
    def test_meta_capi_email_hashing(self, mock_post):
        """Test email được hash SHA256 trước khi gửi"""
        import hashlib
        mock_post.return_value = MagicMock(status_code=200)
        
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        
        call_args = mock_post.call_args
        payload = call_args.kwargs.get('json') or call_args[1].get('json')
        
        # Email hash expected
        expected_hash = hashlib.sha256(
            self.partner.email.strip().lower().encode()
        ).hexdigest()
        
        # Kiểm tra email đã được hash
        user_data = payload['data'][0]['user_data']
        self.assertIn(expected_hash, user_data['em'])

    @patch('odoo.addons.meta_integration.models.sale_order.requests.post')
    def test_meta_capi_custom_data(self, mock_post):
        """Test custom_data chứa đúng thông tin đơn hàng"""
        mock_post.return_value = MagicMock(status_code=200)
        
        sale_order = self._create_sale_order()
        sale_order.action_confirm()
        
        call_args = mock_post.call_args
        payload = call_args.kwargs.get('json') or call_args[1].get('json')
        
        custom_data = payload['data'][0]['custom_data']
        self.assertEqual(custom_data['value'], sale_order.amount_total)
        self.assertEqual(custom_data['currency'], sale_order.currency_id.name)

    @patch('odoo.addons.meta_integration.models.sale_order.requests.post')
    def test_meta_capi_handles_exception(self, mock_post):
        """Test xử lý lỗi khi gọi Meta CAPI thất bại"""
        mock_post.side_effect = Exception("Network error")
        
        sale_order = self._create_sale_order()
        # Không nên raise exception khi Meta CAPI fail
        try:
            result = sale_order.action_confirm()
            self.assertTrue(result, "Order should still be confirmed even if CAPI fails")
        except Exception:
            self.fail("Exception should be handled gracefully")

    def test_sale_order_state_after_confirm(self):
        """Test trạng thái đơn hàng sau khi xác nhận"""
        with patch('odoo.addons.meta_integration.models.sale_order.requests.post'):
            sale_order = self._create_sale_order()
            sale_order.action_confirm()
            self.assertEqual(sale_order.state, 'sale')
