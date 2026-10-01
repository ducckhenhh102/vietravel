# TÀI LIỆU VẬN HÀNH — Travel ERP System

## 🚀 Khởi chạy hệ thống (1 lệnh)

```bash
cd d:\web\ban_ve_du_lich
docker-compose up --build
```

## 📌 Địa chỉ truy cập sau khi chạy

| Dịch vụ | URL | Tài khoản |
|---------|-----|-----------|
| **Website** | http://localhost:8000 | Tự đăng ký |
| **Wagtail Admin** | http://localhost:8000/admin/ | admin / admin123 |
| **Superset BI** | http://localhost:8088 | admin / admin123 |
| **API Stats** | http://localhost:8000/api/stats/ | Công khai |

## 🗄️ Sinh dữ liệu mẫu

```bash
docker-compose exec web python manage.py generate_mock_data --customers 500 --bookings 2000
```

## 🔌 Kết nối Superset → PostgreSQL

Vào Superset: Settings ⚙️ → Database Connections → + Database → PostgreSQL

```
Display Name : Wagtail ERP Production
URI          : postgresql+psycopg2://postgres:postgres123@db:5432/travel_erp
```

## 📊 Tạo Virtual Dataset trong Superset

Vào SQL Lab → SQL Editor, dán SQL từ file `docs/SUPERSET_GUIDE.md`

## 🛑 Dừng hệ thống

```bash
docker-compose down
```

## 🗑️ Xóa toàn bộ (kể cả database)

```bash
docker-compose down -v
```
