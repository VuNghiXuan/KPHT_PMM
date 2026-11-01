# LedgerEase Project Manifest

## 1. Hệ thống Modules (Apps)
- **accounting**: [Điền mô tả nghiệp vụ tại đây]
- **core**: [Điền mô tả nghiệp vụ tại đây]
- **subscriptions**: [Điền mô tả nghiệp vụ tại đây]
- **test_com_info**: [Điền mô tả nghiệp vụ tại đây]

## 2. Bản đồ Class & Phương thức

### App: accounting
#### File: `admin.py`
- **Class VoucherAdmin**: Cấu hình hiển thị Chứng từ trong Admin.
Tự động lọc dữ liệu theo công ty của Admin đang đăng nhập.
  - *Method*: `get_queryset()`
#### File: `apps.py`
- **Class AccountingConfig**: Chưa có mô tả
#### File: `models.py`
- **Class Voucher**: Model Chứng từ kế toán (Phiếu thu, phiếu chi, hóa đơn...).
Kế thừa từ CompanyScopedModel để tự động phân tách dữ liệu theo công ty.
  - *Method*: `__str__()`
#### File: `tests.py`
#### File: `urls.py`
#### File: `views.py`

### App: core
#### File: `admin.py`
- **Class CompanyAdmin**: Cấu hình hiển thị Công ty trong Admin.
- **Class ProfileAdmin**: Cấu hình hiển thị Profile trong Admin.
#### File: `apps.py`
- **Class CoreConfig**: Chưa có mô tả
#### File: `forms_register.py`
- **Class RegistrationForm**: Chưa có mô tả
  - *Method*: `clean_tax_code()`
#### File: `middleware.py`
- **Class CompanyMiddleware**: Middleware chặn mọi request để xác định công ty của User.
  - *Method*: `process_request()`
#### File: `models.py`
- **Class User**: User model tùy chỉnh, dùng làm đối tượng xác thực chính của hệ thống.
  - *Method*: `has_profile()`
- **Class Company**: Đại diện cho một đơn vị kinh doanh (Tenant).
  - *Method*: `__str__()`
- **Class CompanyManager**: Manager tự động lọc dữ liệu theo công ty đang đăng nhập qua Middleware.
  - *Method*: `get_queryset()`
- **Class CompanyScopedModel**: Abstract Model bắt buộc kế thừa cho mọi dữ liệu nghiệp vụ kế toán (Chứng từ, Sổ cái).
- **Class Profile**: Mở rộng thông tin người dùng gắn với công ty.
  - *Method*: `__str__()`
#### File: `tests.py`
#### File: `urls.py`
#### File: `views.py`

### App: subscriptions
#### File: `admin.py`
- **Class FeatureAdmin**: Chưa có mô tả
- **Class SubscriptionPlanAdmin**: Chưa có mô tả
  - *Method*: `get_features()`
#### File: `apps.py`
- **Class SubscriptionsConfig**: Chưa có mô tả
#### File: `models.py`
- **Class Feature**: Định nghĩa các App/Tính năng trong hệ thống.
  - *Method*: `__str__()`
- **Class SubscriptionPlan**: Các gói dịch vụ.
  - *Method*: `__str__()`
#### File: `tests.py`
#### File: `utils.py`
#### File: `views.py`

### App: test_com_info