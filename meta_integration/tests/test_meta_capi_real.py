# -*- coding: utf-8 -*-
"""
Test thật gọi đến Meta CAPI
Chạy file này để kiểm tra dữ liệu có vào Meta Events Manager không

Cách chạy:
    python test_meta_capi_real.py
"""
import hashlib
import requests
import time
import json

# ============== CẤU HÌNH ==============
PIXEL_ID = '1572264680686179'
ACCESS_TOKEN = 'EAAKWCZAoKZBZB0BQWVauSCt2bZCAkZCeoM6ZAsBPLZA5kWVmWkkPdeHIgRZCchXfXd7W2Md2xCo67Rz3rd3aJ0kkPpGGAXaFdYGaKcXucZBr7JXiHFqBkQdisvJoKvj33o5g28GylyZC9q9cXcrtA6Oh9kO1hY8OdOckaACIAJnvT3c3cF5iUYeIs5ZBGrmhfoxj9ilL1KJAva7nHZBZBkeqqEzZCnEjVpuRUBgU38egZA0'

# Test event code từ Meta Events Manager (để test mà không ảnh hưởng data thật)
# Lấy từ: Events Manager > Test Events > Your test event code
TEST_EVENT_CODE = 'TEST42631'  # Ví dụ: 'TEST12345' - Đặt None nếu muốn gửi data thật

# ============== DỮ LIỆU TEST ==============
TEST_EMAIL = 'test@example.com'
TEST_PHONE = '0901234567'
TEST_ORDER_VALUE = 500000  # VND
TEST_CURRENCY = 'VND'


def send_test_event():
    """Gửi một event test đến Meta CAPI"""
    
    # Hash email theo chuẩn Meta
    email_hashed = hashlib.sha256(TEST_EMAIL.strip().lower().encode()).hexdigest()
    
    # Hash phone (bỏ ký tự đặc biệt, giữ số)
    phone_clean = ''.join(filter(str.isdigit, TEST_PHONE))
    phone_hashed = hashlib.sha256(phone_clean.encode()).hexdigest()
    
    payload = {
        "data": [{
            "event_name": "Purchase",
            "event_time": int(time.time()),
            "event_id": f"test_order_{int(time.time())}",  # Unique ID để dedupe
            "action_source": "website",
            "user_data": {
                "em": [email_hashed],
                "ph": [phone_hashed],
                "client_ip_address": "1.2.3.4",
                "client_user_agent": "Mozilla/5.0 Test Agent",
                "country": [hashlib.sha256("vn".encode()).hexdigest()],
            },
            "custom_data": {
                "currency": TEST_CURRENCY,
                "value": TEST_ORDER_VALUE,
                "content_name": "Test Product",
                "content_type": "product",
                "order_id": f"SO-TEST-{int(time.time())}"
            }
        }]
    }
    
    # Thêm test_event_code nếu đang test
    if TEST_EVENT_CODE:
        payload["test_event_code"] = TEST_EVENT_CODE
        print(f"🧪 Đang gửi với TEST EVENT CODE: {TEST_EVENT_CODE}")
        print("   (Dữ liệu sẽ hiển thị trong tab 'Test Events' của Events Manager)")
    else:
        print("⚠️  Đang gửi DATA THẬT (không có test_event_code)")
    
    url = f"https://graph.facebook.com/v21.0/{PIXEL_ID}/events?access_token={ACCESS_TOKEN}"
    
    print("\n" + "="*50)
    print("📤 PAYLOAD GỬI ĐI:")
    print("="*50)
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        print("\n" + "="*50)
        print("📥 RESPONSE TỪ META:")
        print("="*50)
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response_data, indent=2))
        
        if response.status_code == 200:
            print("\n✅ GỬI THÀNH CÔNG!")
            if 'events_received' in response_data:
                print(f"   Events received: {response_data['events_received']}")
            if 'messages' in response_data:
                print(f"   Messages: {response_data['messages']}")
        else:
            print("\n❌ GỬI THẤT BẠI!")
            if 'error' in response_data:
                print(f"   Error: {response_data['error'].get('message', 'Unknown')}")
                
    except Exception as e:
        print(f"\n❌ LỖI KẾT NỐI: {e}")
    
    print("\n" + "="*50)
    print("📊 KIỂM TRA KẾT QUẢ:")
    print("="*50)
    print("1. Vào Meta Events Manager:")
    print("   https://business.facebook.com/events_manager")
    print(f"2. Chọn Pixel ID: {PIXEL_ID}")
    if TEST_EVENT_CODE:
        print("3. Vào tab 'Test Events' để xem event vừa gửi")
    else:
        print("3. Vào tab 'Overview' hoặc 'Diagnostics' để xem event")
    print("4. Event có thể mất 1-5 phút để hiển thị")


def test_connection():
    """Test kết nối đến Meta API"""
    print("🔌 Đang kiểm tra kết nối...")
    
    # Test lấy thông tin Pixel
    url = f"https://graph.facebook.com/v21.0/{PIXEL_ID}?access_token={ACCESS_TOKEN}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            print(f"✅ Kết nối OK!")
            print(f"   Pixel Name: {data.get('name', 'N/A')}")
            print(f"   Pixel ID: {data.get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Lỗi: {data.get('error', {}).get('message', 'Unknown')}")
            return False
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 META CAPI TEST TOOL")
    print("="*50 + "\n")
    
    # Test kết nối trước
    if test_connection():
        print("\n")
        send_test_event()
