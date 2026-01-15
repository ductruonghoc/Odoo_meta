# 📘 Meta Integration - Tích Hợp Facebook cho Odoo

## Giới thiệu

**Meta Integration** là addon Odoo giúp doanh nghiệp kết nối liền mạch giữa hệ thống quản lý bán hàng Odoo và nền tảng quảng cáo Facebook (Meta). Addon này tự động hóa việc đồng bộ dữ liệu khách hàng và đơn hàng, giúp tối ưu hóa chiến dịch quảng cáo và nâng cao hiệu quả marketing.

---

## 🎯 Tính Năng Chính

### 1. Tự Động Nhận Lead từ Facebook (Facebook Lead Webhook)

Khi khách hàng điền form quảng cáo trên Facebook, thông tin lead sẽ được **tự động đồng bộ** về hệ thống Odoo CRM ngay lập tức.

**Lợi ích:**
- ⚡ **Phản hồi nhanh chóng**: Nhân viên sales nhận được thông tin khách hàng tiềm năng ngay khi họ quan tâm sản phẩm
- 🎯 **Không bỏ sót lead**: Mọi lead từ Facebook đều được ghi nhận đầy đủ vào hệ thống
- 📊 **Theo dõi nguồn dễ dàng**: Lead được đánh dấu nguồn từ Facebook, hỗ trợ phân tích hiệu quả chiến dịch

**Thông tin được đồng bộ:**
| Thông tin | Mô tả |
|-----------|-------|
| Họ tên | Tên đầy đủ của khách hàng |
| Email | Địa chỉ email liên hệ |
| Số điện thoại | Số điện thoại khách hàng |
| Nguồn | Tự động gắn nhãn "Facebook" |

---

### 2. Gửi Dữ Liệu Đơn Hàng về Meta Conversions API (CAPI)

Khi đơn hàng được xác nhận trong Odoo, hệ thống sẽ **tự động gửi thông tin mua hàng** về Facebook Pixel thông qua Conversions API.

**Lợi ích:**
- 📈 **Tối ưu quảng cáo**: Facebook nhận được dữ liệu chuyển đổi thực tế, giúp thuật toán quảng cáo thông minh hơn
- 💰 **Giảm chi phí quảng cáo**: Nhắm đúng đối tượng khách hàng có khả năng mua hàng cao
- 📊 **Đo lường chính xác ROI**: Theo dõi được doanh thu thực tế từ chiến dịch quảng cáo
- 🔒 **Bảo mật dữ liệu**: Thông tin khách hàng được mã hóa (hash) trước khi gửi

**Dữ liệu được gửi về Meta:**
| Dữ liệu | Mô tả |
|---------|-------|
| Sự kiện | Purchase (Mua hàng) |
| Tổng giá trị | Tổng tiền đơn hàng |
| Đơn vị tiền tệ | VND, USD, v.v. |
| Danh sách sản phẩm | Mã sản phẩm, số lượng, đơn giá |
| Email khách hàng | Đã được mã hóa bảo mật |

---

## 🔄 Quy Trình Hoạt Động

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Facebook Ads  │────▶│   Meta Server   │────▶│     Odoo CRM    │
│   (Lead Form)   │     │   (Webhook)     │     │   (Tạo Lead)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Odoo Sales    │────▶│   Meta CAPI     │────▶│  Facebook Pixel │
│ (Xác nhận ĐH)   │     │   (Purchase)    │     │ (Tối ưu QC)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 💼 Ai Nên Sử Dụng?

Addon này phù hợp với:

- 🛒 **Doanh nghiệp E-commerce** chạy quảng cáo Facebook thường xuyên
- 🏢 **Công ty B2C** có nhu cầu thu thập lead từ mạng xã hội
- 📱 **Shop online** muốn đo lường chính xác hiệu quả quảng cáo
- 🎯 **Team Marketing** cần dữ liệu chuyển đổi để tối ưu chiến dịch

---

## ✅ Yêu Cầu Hệ Thống

- Odoo phiên bản 14.0 trở lên
- Module phụ thuộc: `base`, `web`, `sale`, `crm`
- Tài khoản Facebook Business với quyền truy cập:
  - Facebook Pixel
  - Conversions API Access Token
  - Lead Ads (nếu sử dụng tính năng nhận lead)

---

## 📞 Hỗ Trợ

Nếu bạn cần hỗ trợ cài đặt hoặc cấu hình, vui lòng liên hệ đội ngũ kỹ thuật để được tư vấn chi tiết.

---

*© 2026 - Meta Integration for Odoo*
