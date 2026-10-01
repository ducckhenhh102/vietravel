"""
superset_config.py
==================
Tài liệu kỹ thuật: Cấu hình Apache Superset kết nối PostgreSQL Wagtail

File này KHÔNG phải config Superset thực sự — đây là tài liệu hướng dẫn
được viết dưới dạng Python có comment đầy đủ để dễ tra cứu.

Đặt file này tại: /app/superset_config.py  (bên trong Docker container Superset)
Rồi set biến môi trường:  SUPERSET_CONFIG_PATH=/app/superset_config.py
"""

# ===========================================================================
# PHẦN 1: SQLALCHEMY URI — Kết nối Superset (Docker) → PostgreSQL (Host)
# ===========================================================================

# Vấn đề cốt lõi:
#   - Django/Wagtail chạy trên MÁY HOST  →  port 5432
#   - Superset chạy trong DOCKER CONTAINER
#   - Container KHÔNG thể dùng "localhost" để trỏ về host máy thật!
#
# Giải pháp theo từng OS:
#
# ┌─────────────────┬──────────────────────────────────────────────────┐
# │ OS              │ Host DNS từ trong Docker                         │
# ├─────────────────┼──────────────────────────────────────────────────┤
# │ Windows / macOS │ host.docker.internal  (tự động có sẵn)          │
# │ Linux           │ 172.17.0.1  (gateway mặc định của bridge network)│
# │ Linux (new)     │ host-gateway  (dùng với --add-host flag)         │
# └─────────────────┴──────────────────────────────────────────────────┘

SQLALCHEMY_URI_TEMPLATES = {

    # --- Windows / macOS (phổ biến nhất khi dev) ---
    "windows_macos": (
        "postgresql+psycopg2://{db_user}:{db_password}"
        "@host.docker.internal:5432/{wagtail_db_name}"
    ),

    # --- Linux: dùng IP gateway ---
    "linux_gateway": (
        "postgresql+psycopg2://{db_user}:{db_password}"
        "@172.17.0.1:5432/{wagtail_db_name}"
    ),

    # --- Cùng Docker network (nếu Wagtail cũng chạy trong Docker) ---
    "same_docker_network": (
        "postgresql+psycopg2://{db_user}:{db_password}"
        "@db:5432/{wagtail_db_name}"
        # "db" là tên service trong docker-compose.yml
    ),
}

# Ví dụ thực tế — điền thông tin thật vào đây:
EXAMPLE_URI = (
    "postgresql+psycopg2://wagtail_user:SuperSecret123"
    "@host.docker.internal:5432/travel_erp_db"
)


# ===========================================================================
# PHẦN 2: THIẾT LẬP TRONG SUPERSET UI
# ===========================================================================
#
# BƯỚC 1: Vào Settings (⚙️ bánh răng góc trên phải)
# BƯỚC 2: Database Connections  →  + Database
# BƯỚC 3: Chọn PostgreSQL từ danh sách
# BƯỚC 4: Điền:
#   • Display Name : Wagtail ERP Production
#   • SQLAlchemy URI : (dán URI bên trên vào)
# BƯỚC 5: Nhấn TEST CONNECTION  →  phải ra thông báo "Connection looks good!"
# BƯỚC 6: Nhấn CONNECT  →  sau đó FINISH
#
# LƯU Ý QUAN TRỌNG:
#   Phải mở PostgreSQL cho phép kết nối từ IP Docker:
#   File: postgresql.conf   →   listen_addresses = '*'
#   File: pg_hba.conf       →   host all all 0.0.0.0/0 md5
#   Sau đó restart PostgreSQL service.


# ===========================================================================
# PHẦN 3: SQL QUERY — Virtual Dataset "DS_Booking_Revenue_CRM"
# ===========================================================================
#
# Dán câu SQL này vào: SQL Lab → SQL Editor → Run → Save as Dataset
# Tên Dataset: DS_Booking_Revenue_CRM
#

VIRTUAL_DATASET_SQL = """
-- ============================================================
-- DS_Booking_Revenue_CRM — Flat table phục vụ phân tích BI
-- Kết hợp: Booking + Customer + TourDeparture + TourProduct
-- Chỉ lấy đơn hàng PAID và COMPLETED (doanh thu thực tế)
-- ============================================================

SELECT
    -- ── Booking fields ──────────────────────────────────────
    b.id                                        AS booking_id,
    b.booking_code                              AS "Mã đặt chỗ",
    b.booking_date::DATE                        AS "Ngày đặt",
    DATE_TRUNC('month', b.booking_date)::DATE   AS booking_month,  -- nhóm theo tháng
    DATE_TRUNC('quarter', b.booking_date)::DATE AS booking_quarter,
    EXTRACT(YEAR  FROM b.booking_date)::INT     AS booking_year,
    EXTRACT(MONTH FROM b.booking_date)::INT     AS booking_month_num,
    b.num_adults                                AS so_nguoi_lon,
    b.num_children                              AS so_tre_em,
    (b.num_adults + b.num_children)             AS "Tổng hành khách",
    b.total_amount                              AS total_amount_raw,
    b.discount_amount,
    b.final_amount                              AS "Tổng tiền",
    b.status                                    AS "Trạng thái đơn",

    -- ── Customer fields ─────────────────────────────────────
    c.id                                        AS customer_id,
    (au.first_name || ' ' || au.last_name)      AS "Tên khách hàng",
    au.email                                    AS email_kh,
    c.phone                                     AS dien_thoai,
    c.membership_tier                           AS "Hạng thành viên",
    c.total_spent                               AS tong_chi_tieu_kh,
    c.loyalty_points,

    -- ── TourDeparture fields ─────────────────────────────────
    td.id                                       AS departure_id,
    td.departure_code                           AS ma_chuyen,
    td.start_date                               AS "Ngày khởi hành",
    td.end_date                                 AS ngay_ve,
    (td.end_date - td.start_date)               AS so_ngay_tour,
    td.departure_point                          AS diem_khoi_hanh,
    td.total_seats,
    td.available_seats,
    td.guide_name                               AS ten_hdv,

    -- ── TourProduct fields ───────────────────────────────────
    tp.id                                       AS product_id,
    tp.sku_code                                 AS "Mã Tour (SKU)",
    tp.base_price                               AS gia_goc,

    -- ── TourPage fields (qua JOIN) ───────────────────────────
    wp.title                                    AS "Tên Tour",
    wp.slug                                     AS tour_slug

FROM core_booking AS b

-- JOIN lấy thông tin khách hàng
INNER JOIN core_customer AS c
    ON b.customer_id = c.id

-- JOIN lấy user (tên, email)
INNER JOIN auth_user AS au
    ON c.user_id = au.id

-- JOIN lấy lịch khởi hành
INNER JOIN core_tourdeparture AS td
    ON b.departure_id = td.id

-- JOIN lấy sản phẩm tour
INNER JOIN core_tourproduct AS tp
    ON td.tour_product_id = tp.id

-- JOIN lấy tên tour từ Wagtail Page
INNER JOIN wagtailcore_page AS wp
    ON tp.tour_page_id = wp.id

-- ── Chỉ lấy đơn hàng thực sự tạo doanh thu ─────────────────
WHERE b.status IN ('PAID', 'COMPLETED')

-- ── Sắp xếp mới nhất lên trước ──────────────────────────────
ORDER BY b.booking_date DESC;
"""


# ===========================================================================
# PHẦN 4: CẤU HÌNH 4 BIỂU ĐỒ TRONG SUPERSET
# ===========================================================================

CHART_CONFIGS = {

    # ------------------------------------------------------------------
    # CHART 1: Big Number with Trendline — Tổng doanh thu
    # ------------------------------------------------------------------
    "chart_1_big_number": {
        "chart_type":  "Big Number with Trendline",
        "dataset":     "DS_Booking_Revenue_CRM",
        "purpose":     "KPI box đặt ở góc trên Dashboard — cái nhìn đầu tiên của CEO",
        "config": {
            "Metric":        "SUM(Tổng tiền)",
            "Time Column":   "Ngày đặt",
            "Time Grain":    "Month",
            "Subheader":     "Tổng Doanh Thu Năm 2026",
        },
        "formatting": {
            "Number Format": ",.0f",           # 2,400,000
            "Currency":      "đ",
            "Color Scheme":  "Green → Teal",
        },
        "notes": (
            "Trendline bên dưới số lớn sẽ tự vẽ xu hướng tháng gần nhất. "
            "Dùng Filter Box lọc theo năm để so sánh YoY."
        ),
    },

    # ------------------------------------------------------------------
    # CHART 2: Bar Chart (Time-series) — Doanh thu theo tháng
    # ------------------------------------------------------------------
    "chart_2_revenue_trend": {
        "chart_type":  "Bar Chart",                # hoặc "Time-series Chart"
        "dataset":     "DS_Booking_Revenue_CRM",
        "purpose":     "Phân tích tính mùa vụ — tháng cao điểm / thấp điểm",
        "config": {
            "X-Axis (Time Column)": "Ngày đặt",
            "Time Grain":           "Month",        # nhóm theo tháng
            "Metrics":              ["SUM(Tổng tiền)", "COUNT(Mã đặt chỗ)"],
            "Breakdowns":           "Trạng thái đơn",   # PAID vs COMPLETED
            "Sort by":              "Time",
        },
        "formatting": {
            "Y-Axis Format":    ",.0f",
            "Bar Stacked":      True,               # xếp chồng theo trạng thái
            "Show Legend":      True,
            "Color Scheme":     "Superset Colors",
        },
        "filters": {
            "booking_year": "2026",
        },
        "notes": (
            "Có thể thêm Breakdowns = 'Mã Tour (SKU)' để thấy tour nào "
            "đóng góp doanh thu nhiều nhất theo từng tháng."
        ),
    },

    # ------------------------------------------------------------------
    # CHART 3: Pie Chart — Tỷ trọng Khách hàng theo hạng thành viên
    # ------------------------------------------------------------------
    "chart_3_customer_tier": {
        "chart_type":  "Pie Chart",
        "dataset":     "DS_Booking_Revenue_CRM",
        "purpose":     "Đánh giá cơ cấu khách hàng — VIP chiếm bao nhiêu % booking?",
        "config": {
            "Dimension":        "Hạng thành viên",
            "Metric":           "COUNT(Mã đặt chỗ)",   # số đơn hàng theo hạng
            "Sort Descending":  True,
            "Show Labels":      True,
            "Show Legend":      True,
        },
        "formatting": {
            "Label Type":       "key_percent",      # "VIP (23%)"
            "Outer Radius":     0.7,
            "Inner Radius":     0.35,               # Donut style
            "Color Scheme":     "Sunset",
        },
        "notes": (
            "Thêm Metric thứ 2 = SUM(Tổng tiền) để thấy VIP tuy ít người "
            "nhưng đóng góp bao nhiêu % doanh thu. "
            "Insight quan trọng cho chiến lược CRM."
        ),
    },

    # ------------------------------------------------------------------
    # CHART 4: Table Chart — Top Tour theo doanh thu
    # ------------------------------------------------------------------
    "chart_4_top_tour": {
        "chart_type":  "Table",
        "dataset":     "DS_Booking_Revenue_CRM",
        "purpose":     "Bảng xếp hạng tour — tour nào đang bán chạy nhất?",
        "config": {
            "Dimensions":       ["Mã Tour (SKU)", "Tên Tour"],
            "Metrics": {
                "so_don":        "COUNT(Mã đặt chỗ)",
                "doanh_thu":     "SUM(Tổng tiền)",
                "tb_per_booking": "AVG(Tổng tiền)",
                "so_khach":      "SUM(Tổng hành khách)",
            },
            "Sort by":          "SUM(Tổng tiền) DESC",
            "Row Limit":        10,
        },
        "formatting": {
            "doanh_thu":        ",.0f",
            "tb_per_booking":   ",.0f",
            "Conditional Formatting": {
                # Tô màu xanh ô doanh_thu nếu > 500 triệu
                "column":       "SUM(Tổng tiền)",
                "threshold":    500_000_000,
                "color_high":   "#22c55e",
                "color_low":    "#ef4444",
            },
            "Page Length": 10,
        },
        "notes": (
            "Dùng bảng này để trình bày trực tiếp trong meeting. "
            "Có thể kéo thả cột để sắp xếp realtime."
        ),
    },
}


# ===========================================================================
# PHẦN 5: BỐ CỤC DASHBOARD — TRAVEL CRM EXECUTIVE DASHBOARD
# ===========================================================================

DASHBOARD_LAYOUT = """
┌─────────────────────────────────────────────────────────────────────┐
│  TRAVEL CRM EXECUTIVE DASHBOARD              [ Filter: Năm | Tour ] │
├──────────────────┬──────────────────────────────────────────────────┤
│                  │                                                   │
│  💰 Big Number   │        📊 Bar Chart — Doanh thu theo Tháng       │
│  $2,400,000      │  Q1   Q2   Q3   Q4                              │
│  Tổng doanh thu  │  ▄▄▄  ███  ▄▄▄  ▄▄                             │
│  ↑ 18.3% YoY    │                                                   │
│                  │                                                   │
├──────────────────┴──────────────────────────────────────────────────┤
│   🥧 Pie Chart               │  (Trống cho Filter / Note)           │
│   Tỷ trọng Hạng thành viên  │                                       │
│   STANDARD 55% | VIP 23%    │                                       │
│   GOLD 12% | SILVER 10%     │                                       │
├──────────────────────────────┴──────────────────────────────────────┤
│                                                                     │
│  📋 Table Chart — Top 10 Tour theo Doanh thu                        │
│  SKU          │ Tên Tour          │ Đơn │ Doanh thu   │ TB/đơn     │
│  TOUR-PQ-004  │ Phú Quốc Biển Đảo│ 342 │ 486,000,000 │ 9,200,000  │
│  TOUR-HN-001  │ Hà Nội – Hạ Long │ 281 │ 394,000,000 │ 8,500,000  │
│  ...          │ ...               │ ... │ ...         │ ...        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Row 1 (Top)    : Filter Box (30%) + Big Number (70%)
Row 2 (Middle) : Bar Chart (60%) + Pie Chart (40%)
Row 3 (Bottom) : Table Chart (100% width)
"""


# ===========================================================================
# PHẦN 6: CHECKLIST KIỂM TRA DỮ LIỆU (Data Validation)
# ===========================================================================

DATA_VALIDATION_CHECKLIST = """
QUY TRÌNH ĐỐI SOÁT DỮ LIỆU (Data Validation)
==============================================

Mục tiêu: Xác nhận con số Superset Dashboard KHỚP với dữ liệu gốc trong DB.

BƯỚC 1 — Ghi nhận con số trên Superset
  • Lọc Filter: Ngày đặt = Tháng 10/2026
  • Ghi nhận: Tổng doanh thu Big Number = X đồng
  • Ghi nhận: Số đơn COUNT = Y đơn

BƯỚC 2 — Truy vấn trực tiếp PostgreSQL
  Chạy trong SQL Lab hoặc psql:

  SELECT
      COUNT(*)            AS so_don,
      SUM(final_amount)   AS tong_doanh_thu
  FROM core_booking
  WHERE status IN ('PAID', 'COMPLETED')
    AND DATE_TRUNC('month', booking_date) = '2026-10-01';

BƯỚC 3 — So sánh kết quả
  Superset Dashboard  ==  SQL trực tiếp  →  ✅ KHỚP → Nghiệm thu
  Superset Dashboard  ≠   SQL trực tiếp  →  ❌ LỆCH → Kiểm tra cache

BƯỚC 4 — Nếu lệch: Refresh Dataset
  Superset → Dataset → ... → Invalidate Cache & Refresh

"""
