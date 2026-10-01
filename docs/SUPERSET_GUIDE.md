# Superset Configuration Guide — Travel ERP BI Dashboard

> **File tham khảo:** [superset_config_guide.py](file:///d:/web/ban_ve_du_lich/docs/superset_config_guide.py)

---

## PHẦN 1 — Cấu hình SQLAlchemy URI

### Tình huống: Wagtail trên Host, Superset trong Docker

```
┌─────────────────────────────────────────────────────────────┐
│  MÁY HOST                      │  DOCKER CONTAINER          │
│                                │                            │
│  Django/Wagtail                │  Apache Superset           │
│  PostgreSQL :5432              │  port 8088                 │
│                                │                            │
│  ❌ "localhost"  ──────────────┼─X──── không tới được      │
│  ✅ host.docker.internal ──────┼──────── tới được!          │
└─────────────────────────────────────────────────────────────┘
```

### URI theo từng môi trường

| OS | SQLAlchemy URI |
|----|---------------|
| **Windows / macOS** | `postgresql+psycopg2://user:pass@host.docker.internal:5432/db_name` |
| **Linux** | `postgresql+psycopg2://user:pass@172.17.0.1:5432/db_name` |
| **Cùng Docker network** | `postgresql+psycopg2://user:pass@db:5432/db_name` |

### Bật PostgreSQL nhận kết nối từ Docker

> [!IMPORTANT]
> Phải sửa 2 file cấu hình PostgreSQL trên máy host, sau đó restart.

```ini
# postgresql.conf
listen_addresses = '*'

# pg_hba.conf — thêm dòng này
host    all    all    0.0.0.0/0    md5
```

```bash
# Restart PostgreSQL (Windows Service)
net stop postgresql-x64-16
net start postgresql-x64-16
```

### Điền vào Superset UI

```
Settings ⚙️  →  Database Connections  →  + Database  →  PostgreSQL

  Display Name  :  Wagtail ERP Production
  URI           :  postgresql+psycopg2://wagtail_user:SuperSecret123
                   @host.docker.internal:5432/travel_erp_db

  → [ TEST CONNECTION ]  ✅ Connection looks good!
  → [ CONNECT ]  →  [ FINISH ]
```

---

## PHẦN 2 — SQL Query: Virtual Dataset

> Dán vào `SQL Lab → SQL Editor`, chạy → `Save → Save as dataset`
> **Tên dataset:** `DS_Booking_Revenue_CRM`

```sql
-- ============================================================
-- DS_Booking_Revenue_CRM — Flat table phục vụ phân tích BI
-- JOIN: Booking + Customer + TourDeparture + TourProduct
-- Chỉ lấy đơn PAID & COMPLETED (doanh thu thực)
-- ============================================================

SELECT
    -- ── Booking ─────────────────────────────────────────────
    b.id                                        AS booking_id,
    b.booking_code                              AS "Mã đặt chỗ",
    b.booking_date::DATE                        AS "Ngày đặt",
    DATE_TRUNC('month', b.booking_date)::DATE   AS booking_month,
    DATE_TRUNC('quarter',b.booking_date)::DATE  AS booking_quarter,
    EXTRACT(YEAR  FROM b.booking_date)::INT     AS booking_year,
    EXTRACT(MONTH FROM b.booking_date)::INT     AS booking_month_num,
    (b.num_adults + b.num_children)             AS "Tổng hành khách",
    b.final_amount                              AS "Tổng tiền",
    b.status                                    AS "Trạng thái đơn",

    -- ── Customer ────────────────────────────────────────────
    (au.first_name || ' ' || au.last_name)      AS "Tên khách hàng",
    c.membership_tier                           AS "Hạng thành viên",
    c.total_spent                               AS tong_chi_tieu_kh,

    -- ── TourDeparture ────────────────────────────────────────
    td.departure_code                           AS ma_chuyen,
    td.start_date                               AS "Ngày khởi hành",
    (td.end_date - td.start_date)               AS so_ngay_tour,
    td.guide_name                               AS ten_hdv,

    -- ── TourProduct + TourPage ───────────────────────────────
    tp.sku_code                                 AS "Mã Tour (SKU)",
    wp.title                                    AS "Tên Tour"

FROM core_booking          AS b
INNER JOIN core_customer      AS c   ON b.customer_id   = c.id
INNER JOIN auth_user          AS au  ON c.user_id        = au.id
INNER JOIN core_tourdeparture AS td  ON b.departure_id   = td.id
INNER JOIN core_tourproduct   AS tp  ON td.tour_product_id = tp.id
INNER JOIN wagtailcore_page   AS wp  ON tp.tour_page_id  = wp.id

WHERE b.status IN ('PAID', 'COMPLETED')
ORDER BY b.booking_date DESC;
```

### Sơ đồ JOIN

```
core_booking  ──── customer_id ────▶  core_customer ──── user_id ────▶  auth_user
     │                                                                      (tên, email)
     └──── departure_id ────▶  core_tourdeparture
                                        │
                               tour_product_id ────▶  core_tourproduct
                                                              │
                                                       tour_page_id ────▶  wagtailcore_page
                                                                              (tên tour)
```

---

## PHẦN 3 — Cấu hình 4 Biểu đồ

### Chart 1 — Big Number with Trendline

> `Charts → + Chart → Big Number with Trendline`

| Trường | Giá trị |
|--------|---------|
| **Dataset** | `DS_Booking_Revenue_CRM` |
| **Metric** | `SUM(Tổng tiền)` |
| **Time Column** | `Ngày đặt` |
| **Time Grain** | `Month` |
| **Number Format** | `,.0f` |
| **Subheader** | `Tổng Doanh Thu Năm 2026` |

> [!TIP]
> Trendline nhỏ bên dưới con số lớn tự vẽ xu hướng. Đây là chart đặt ở **Row 1** để CEO thấy ngay khi mở Dashboard.

---

### Chart 2 — Bar Chart (Time-series) — Xu hướng Doanh thu

> `Charts → + Chart → Bar Chart`

| Trường | Giá trị |
|--------|---------|
| **Dataset** | `DS_Booking_Revenue_CRM` |
| **X-Axis** | `Ngày đặt` |
| **Time Grain** | `Month` — nhóm theo tháng |
| **Metrics** | `SUM(Tổng tiền)`, `COUNT(Mã đặt chỗ)` |
| **Breakdowns** | `Hạng thành viên` *(tô màu VIP vs Standard)* |
| **Bar Stacked** | `True` |
| **Sort by** | `Time` |

```
Kết quả trực quan:

Triệu đ
  500 │        ██
  400 │     ██ ██ ██
  300 │  ██ ██ ██ ██ ██
  200 │  ██ ██ ██ ██ ██ ██ ██
  100 │  ██ ██ ██ ██ ██ ██ ██ ██
      └──T1─T2─T3─T4─T5─T6─T7─T8─→
         ■ VIP  ■ GOLD  ■ STANDARD
```

> [!NOTE]
> Đổi Breakdowns sang `Mã Tour (SKU)` để thấy tour nào chiếm doanh thu nhiều nhất theo từng tháng.

---

### Chart 3 — Pie Chart — Tỷ trọng Hạng Thành viên

> `Charts → + Chart → Pie Chart`

| Trường | Giá trị |
|--------|---------|
| **Dataset** | `DS_Booking_Revenue_CRM` |
| **Dimension** | `Hạng thành viên` |
| **Metric** | `COUNT(Mã đặt chỗ)` |
| **Label Type** | `key_percent` — hiển thị `"VIP (23%)"` |
| **Outer Radius** | `0.7` |
| **Inner Radius** | `0.35` *(Donut style)* |
| **Show Legend** | `True` |

> [!TIP]
> Thêm **Metric thứ 2** = `SUM(Tổng tiền)` để tooltip hiện cả số đơn lẫn doanh thu khi hover. Insight: VIP chỉ 6% khách nhưng đóng góp ~30% doanh thu.

---

### Chart 4 — Table Chart — Top Tour Performance

> `Charts → + Chart → Table`

| Trường | Giá trị |
|--------|---------|
| **Dataset** | `DS_Booking_Revenue_CRM` |
| **Dimensions** | `Mã Tour (SKU)`, `Tên Tour` |
| **Metric 1** | `COUNT(Mã đặt chỗ)` — Số đơn |
| **Metric 2** | `SUM(Tổng tiền)` — Tổng doanh thu |
| **Metric 3** | `AVG(Tổng tiền)` — Doanh thu TB/đơn |
| **Metric 4** | `SUM(Tổng hành khách)` — Tổng khách |
| **Sort by** | `SUM(Tổng tiền) DESC` |
| **Row Limit** | `10` |

**Conditional Formatting (tô màu cột doanh thu):**

| Cột | Nếu giá trị | Màu |
|-----|-------------|-----|
| `SUM(Tổng tiền)` | > 400,000,000 | 🟢 Xanh |
| `SUM(Tổng tiền)` | < 100,000,000 | 🔴 Đỏ |

---

## PHẦN 4 — Bố cục Dashboard

> `Dashboards → + Dashboard` → Đặt tên: **TRAVEL CRM EXECUTIVE DASHBOARD**

```
┌────────────────┬────────────────────────────────────────────┐
│ Filter Box     │   💰 Big Number + Trendline                 │
│ (Năm | Tour)   │   $2,478,390,000                           │
│                │   ↑ 18.3% so với tháng trước               │
├────────────────┴─────────────┬─────────────────────────────-┤
│  📊 Bar Chart                │  🥧 Pie Chart                 │
│  Doanh thu theo tháng        │  Tỷ trọng Hạng thành viên    │
│  (breakdown theo hạng KH)    │  (Donut chart)               │
├──────────────────────────────┴──────────────────────────────┤
│  📋 Table — Top 10 Tour Performance                          │
│  SKU │ Tên Tour │ Đơn │ Doanh thu │ TB/đơn │ Tổng khách    │
└─────────────────────────────────────────────────────────────┘

Row 1 : Filter (25%) + Big Number (75%)
Row 2 : Bar Chart (60%) + Pie Chart (40%)
Row 3 : Table (100%)
```

---

## PHẦN 5 — Quy trình Kiểm tra Dữ liệu (Data Validation)

> [!IMPORTANT]
> Đây là bước **nghiệm thu** — xác nhận con số Superset KHỚP với DB gốc.

**Bước 1:** Lọc Dashboard: `Ngày đặt = Tháng 10/2026` → ghi nhận con số Big Number

**Bước 2:** Chạy query SQL trực tiếp trong Superset SQL Lab:

```sql
SELECT
    COUNT(*)          AS so_don,
    SUM(final_amount) AS tong_doanh_thu
FROM core_booking
WHERE status IN ('PAID', 'COMPLETED')
  AND DATE_TRUNC('month', booking_date) = '2026-10-01';
```

**Bước 3:** So sánh

```
Superset Dashboard  ──── $50,000,000
SQL trực tiếp       ──── $50,000,000
                    ────────────────
                         ✅ KHỚP → Nghiệm thu ✔
```

> [!WARNING]
> Nếu hai con số **LỆCH nhau**: Vào `Dataset → ⋯ → Invalidate Cache & Refresh` rồi kiểm tra lại. Thường do Superset cache kết quả cũ.
