# 🔐 Hệ thống License cho Claude via Browser
## Tổng quan kiến trúc

```
keygen.py          →  BẠN dùng để tạo/quản lý key
license_server.py  →  Deploy lên cloud (Railway/Render)
license_validator.py →  Nhúng vào app
app_with_license.py  →  App  (tích hợp license gate)
app.py là nơi logic thực sự dự án tôi ko mún để lộ logic ở đây 
dashboard.py là nơi thực hiện logic hiển thị vs front ended 
tabs là nơi chứa các front ended
 tabs: chứa +tab.account+tab.tab_api_history+tab.tab_license+tab.tab_profile
```

---

## Bước 1: Đổi SECRET KEY

Mở **cả 3 file** và đổi dòng này thành chuỗi bí mật của bạn:
```python
SECRET_KEY = "MY_SUPER_SECRET_KEY_CHANGE_THIS_2024"
# →
SECRET_KEY = "abc123xyz_chuoi_bi_mat_cua_ban_khong_ai_biet"
```
⚠️ **3 file phải dùng cùng 1 SECRET_KEY**

---

## Bước 2: Deploy License Server

### Dùng Railway (miễn phí):
```bash
# 1. Tạo tài khoản railway.app
# 2. New Project → Deploy from GitHub
# 3. Upload license_server.py + licenses.json
# 4. Set PORT=8080 trong environment variables
```

### Sau khi deploy, cập nhật URL trong license_validator.py:
```python
LICENSE_SERVER = "https://your-app.railway.app"
```

---

## Bước 3: Tạo key cho khách hàng

```bash
# Tạo key 30 ngày
python keygen.py --email khachhang@gmail.com --days 30

# Tạo key 1 năm
python keygen.py --email khachhang@gmail.com --days 365

# Xem tất cả key
python keygen.py --list

# Thu hồi key (khi refund hoặc vi phạm)
python keygen.py --revoke XXXXX-XXXXX-XXXXX-XXXXX-CCCC
```

⚠️ **Copy file licenses.json lên server sau mỗi lần tạo key mới!**

---

## Bước 4: Đóng gói thành .exe
cần cải thiện thêm 1 tí
đầu tiên việc connect hay chạy app có thể dc thực hiện bằng cách enter nút button connect
tiếp theo yêu cầu có 1 ô để setup cai đặc profile 
để nạp vào 
code như sau FIREFOX_PROFILE = (
    r"C:\Users\Admin\AppData\Roaming\Mozilla\Firefox\Profiles\RHVILscw.Profile 1"
)

MODEL_ID = "claude-via-browser"

# Giảm từ 240s → 60s; nếu Claude không trả lời trong 60s coi như lỗi
CLIENT_TIMEOUT = 240

# Chỉ giữ N messages cuối cùng trước khi gửi (tránh prompt quá dài)
MAX_HISTORY_MESSAGES = 10

# Số lần retry khi chat_id bị stale
MAX_RETRIES = 2
ở màn hình chính là cho chỉnh FIREFOX_PROFILE còn các max historu messages và max_retries, client time out cho chỉnh ở tab_profile 
 
 nếu  FIREFOX_PROFILE là null thì ko cho chạy 
 tiếp theo là cơ chế để có thể đảm bảo họ ko chs mất dạy cố gắng crak hệ thống của mik 
 hiện tại điều tối mún là như sau:
có 1 cơ chế để code dc chạy
đó là sử dụng khóa 2 chiều
ở phía ng dùng chỉ đọc được, ko tạo được
ở phía server sẽ tạo được 
có 1 đoạn code trước khi chương trình chạy connect đó là
nghĩa là ng dùng sẽ mún chạy sẽ gửi cái key họ mua trc đó
để server tạo ra 1 token 
ng dùng chỉ có thể validate dc cái token đó ở đoạn code đó
ko bt cách tạo và chỉ khi có token ms chạy dc

```bash
pip install pyinstaller

# Đóng gói
pyinstaller --onefile --noconsole --name "ClaudeBrowser" app_with_license.py

# File .exe nằm ở: dist/ClaudeBrowser.exe
```

---

## Flow hoạt động

```
User chạy .exe
    │
    ▼
Có cache hợp lệ? ──YES──→ Ping server (check revoke) ──OK──→ Chạy app
    │                                                   │
    NO                                              REVOKED → Thoát
    │
    ▼
Hiện dialog nhập key
    │
    ▼
Verify online (server)
    │
    ├── Không có internet → Verify offline (cache cũ)
    │
    ├── Key sai/hết hạn/bị revoke → Hiện lỗi
    │
    └── Key hợp lệ → Lưu cache → Chạy app
                         │
                         └── Background thread ping 24h/lần
```

---

## Bảo mật

| Tấn công | Bảo vệ bằng |
|----------|-------------|
| Share key | Ping server check revoke mỗi 24h |
| Giả mạo key | HMAC-SHA256 signature |
| Sửa cache | Base64 obfuscation (cơ bản) |
| Dùng sau hết hạn | Server check + local date check |
| Bypass hoàn toàn | PyInstaller obfuscation |

> 💡 Không có hệ thống nào bảo mật 100% nếu user có .exe. 
> Mục tiêu là làm khó crack đủ để không đáng công crack.
