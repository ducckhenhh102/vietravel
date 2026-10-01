"""
management/commands/generate_mock_data.py

Django management command sinh dữ liệu giả lập cho hệ thống bán vé du lịch.

Cách dùng:
    python manage.py generate_mock_data
    python manage.py generate_mock_data --customers 500 --bookings 2000
    python manage.py generate_mock_data --clear    # Xóa toàn bộ dữ liệu cũ trước khi sinh mới
    python manage.py generate_mock_data --customers 100 --bookings 500 --no-color
"""

import random
import string
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from faker import Faker

# Khởi tạo Faker với locale Tiếng Việt
fake = Faker("vi_VN")
Faker.seed(42)          # Cố định seed để kết quả tái tạo được
random.seed(42)


# ---------------------------------------------------------------------------
# Helpers — ANSI color terminal output
# ---------------------------------------------------------------------------

class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"


def colorize(text: str, *colors) -> str:
    """Bọc text với màu ANSI (bỏ qua nếu không hỗ trợ)."""
    if not sys.stdout.isatty():
        return text
    return "".join(colors) + str(text) + Color.RESET


# ---------------------------------------------------------------------------
# Progress Bar
# ---------------------------------------------------------------------------

class ProgressBar:
    """
    Thanh tiến trình hiển thị trên terminal.

    Ví dụ:
        Tạo Booking  [████████████░░░░░░░░]  600/2000  30%  ⚡ 120 rec/s
    """

    BAR_WIDTH = 24
    FILL_CHAR = "█"
    EMPTY_CHAR = "░"

    def __init__(self, total: int, label: str = "", color: str = Color.CYAN):
        self.total = max(total, 1)
        self.label = label
        self.color = color
        self.current = 0
        self._start_time = datetime.now()
        self._last_print_pct = -1

    def update(self, step: int = 1) -> None:
        self.current = min(self.current + step, self.total)
        pct = int(self.current / self.total * 100)
        # Chỉ in lại khi % thay đổi (tránh spam terminal)
        if pct == self._last_print_pct and self.current < self.total:
            return
        self._last_print_pct = pct
        self._render(pct)

    def _render(self, pct: int) -> None:
        filled = int(self.BAR_WIDTH * pct / 100)
        bar = self.FILL_CHAR * filled + self.EMPTY_CHAR * (self.BAR_WIDTH - filled)

        elapsed = (datetime.now() - self._start_time).total_seconds()
        speed = f"{self.current / elapsed:.0f} rec/s" if elapsed > 0.1 else ""

        label_str = f"{self.label:<20}" if self.label else ""
        bar_str   = colorize(f"[{bar}]", self.color)
        count_str = colorize(f"{self.current:>6}/{self.total}", Color.WHITE)
        pct_str   = colorize(f"{pct:>3}%", Color.BOLD)
        speed_str = colorize(f"⚡ {speed}", Color.DIM) if speed else ""

        line = f"\r  {label_str} {bar_str} {count_str}  {pct_str}  {speed_str}"
        sys.stdout.write(line)
        sys.stdout.flush()

    def finish(self, message: str = "") -> None:
        self.current = self.total
        self._render(100)
        elapsed = (datetime.now() - self._start_time).total_seconds()
        suffix = colorize(f"  ✓ {message or 'Xong!'} ({elapsed:.1f}s)", Color.GREEN)
        sys.stdout.write(f"\n  {suffix}\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Dữ liệu tĩnh cho tours Việt Nam
# ---------------------------------------------------------------------------

TOUR_DATA = [
    {
        "title":      "Khám phá Hà Nội – Hạ Long 5N4Đ",
        "sku_code":   "TOUR-HN-HL-001",
        "base_price": Decimal("8_500_000"),
        "duration":   5,
        "region":     "Miền Bắc",
    },
    {
        "title":      "Đà Nẵng – Hội An – Huế Tuyệt Vời 4N3Đ",
        "sku_code":   "TOUR-DN-HAN-002",
        "base_price": Decimal("6_800_000"),
        "duration":   4,
        "region":     "Miền Trung",
    },
    {
        "title":      "Sài Gòn – Mũi Né – Đà Lạt Khởi Hành Hàng Tuần",
        "sku_code":   "TOUR-SG-DL-003",
        "base_price": Decimal("5_500_000"),
        "duration":   3,
        "region":     "Miền Nam",
    },
    {
        "title":      "Phú Quốc Thiên Đường Biển Đảo 4N3Đ",
        "sku_code":   "TOUR-PQ-004",
        "base_price": Decimal("9_200_000"),
        "duration":   4,
        "region":     "Miền Nam",
    },
    {
        "title":      "Sapa – Bắc Hà Chợ Phiên Cuối Tuần 3N2Đ",
        "sku_code":   "TOUR-SAPA-005",
        "base_price": Decimal("4_200_000"),
        "duration":   3,
        "region":     "Miền Bắc",
    },
]

DEPARTURE_POINTS = [
    "Sân bay Nội Bài – 06:00",
    "Sân bay Tân Sơn Nhất – 07:30",
    "Sân bay Đà Nẵng – 08:00",
    "Bến xe Mỹ Đình – 05:30",
    "Ga Hà Nội – 22:00 (tàu đêm)",
]

GUIDE_NAMES = [
    "Nguyễn Minh Tuấn", "Trần Thị Thu Hà", "Lê Văn Phúc",
    "Phạm Ngọc Lan", "Vũ Đức Anh", "Đỗ Thị Mỹ Linh",
    "Hoàng Quốc Việt", "Ngô Thanh Hương", "Bùi Trọng Nghĩa",
    "Đinh Thị Kim Ngân",
]

MEMBERSHIP_WEIGHTS = {
    "STANDARD": 55,
    "SILVER":   25,
    "GOLD":     12,
    "VIP":       6,
    "DIAMOND":   2,
}

PAYMENT_METHODS = ["BANK_TRANSFER", "MOMO", "VNPAY", "CASH", "CREDIT_CARD", "ZALOPAY"]
PAYMENT_METHOD_WEIGHTS = [35, 25, 20, 10, 7, 3]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def generate_booking_code() -> str:
    """Sinh mã đặt tour dạng BK20260101-XXXX."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"BK{date.today().strftime('%Y%m%d')}-{suffix}"


def random_date_in_year(year: int = 2026) -> datetime:
    """Random datetime rải rác trong năm 2026."""
    start = datetime(year, 1, 1)
    end   = datetime(year, 12, 31, 23, 59, 59)
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    result = start + timedelta(seconds=random_seconds)
    return timezone.make_aware(result)


def weighted_choice(choices_weights: dict) -> str:
    """Chọn ngẫu nhiên theo trọng số."""
    keys    = list(choices_weights.keys())
    weights = list(choices_weights.values())
    return random.choices(keys, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Main Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Sinh dữ liệu giả lập (mock data) cho hệ thống bán vé du lịch.\n"
        "Tạo Tours, Lịch khởi hành, Khách hàng, Đơn hàng và Thanh toán."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--customers",
            type=int,
            default=500,
            metavar="N",
            help="Số lượng khách hàng cần tạo (mặc định: 500)",
        )
        parser.add_argument(
            "--bookings",
            type=int,
            default=2000,
            metavar="N",
            help="Số lượng đơn đặt tour cần tạo (mặc định: 2000)",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            metavar="YYYY",
            help="Năm dữ liệu (mặc định: 2026)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Xóa toàn bộ dữ liệu cũ trước khi sinh mới",
        )
        parser.add_argument(
            "--skip-tours",
            action="store_true",
            help="Bỏ qua bước tạo Tour và Departure (dùng dữ liệu cũ)",
        )

    # -----------------------------------------------------------------------

    def handle(self, *args, **options):
        self._print_banner()

        num_customers = options["customers"]
        num_bookings  = options["bookings"]
        year          = options["year"]
        do_clear      = options["clear"]
        skip_tours    = options["skip_tours"]

        # Lazy import models (tránh lỗi nếu app chưa migrate)
        from core.models import (
            Booking, Customer, Payment,
            TourDeparture, TourPage, TourProduct,
        )

        # --- Xóa dữ liệu cũ ---
        if do_clear:
            self._clear_data()

        # --- Bước 1: Tạo Tour & Departure ---
        if not skip_tours:
            tour_products = self._create_tour_products(year)
            departures    = self._create_departures(tour_products, year)
        else:
            tour_products = list(TourProduct.objects.all())
            departures    = list(TourDeparture.objects.filter(status="OPEN"))
            self.stdout.write(
                colorize(
                    f"  ⏩ Bỏ qua tạo Tour — dùng {len(departures)} lịch khởi hành hiện có\n",
                    Color.YELLOW,
                )
            )

        if not departures:
            raise CommandError(
                "Không có lịch khởi hành nào. "
                "Hãy chạy lại mà không có --skip-tours."
            )

        # --- Bước 2: Tạo Customers ---
        customers = self._create_customers(num_customers)

        # --- Bước 3: Tạo Bookings ---
        bookings = self._create_bookings(num_bookings, customers, departures, year)

        # --- Bước 4: Tạo Payments ---
        self._create_payments(bookings)

        # --- Bước 5: Cập nhật tổng hợp ---
        self._finalize_stats(customers)

        # --- Tóm tắt ---
        self._print_summary(tour_products, departures, customers, bookings)

    # -----------------------------------------------------------------------
    # STEP 0: Clear
    # -----------------------------------------------------------------------

    def _clear_data(self):
        from core.models import (
            Booking, Customer, Payment,
            TourDeparture, TourPage, TourProduct,
        )

        self.stdout.write(colorize("\n  🗑️  Đang xóa dữ liệu cũ...\n", Color.RED))
        Payment.objects.all().delete()
        Booking.objects.all().delete()
        Customer.objects.all().delete()
        TourDeparture.objects.all().delete()
        TourProduct.objects.all().delete()
        # Xóa User mock (username bắt đầu bằng "mock_")
        User.objects.filter(username__startswith="mock_").delete()
        self.stdout.write(colorize("  ✓ Đã xóa toàn bộ dữ liệu mock cũ.\n\n", Color.GREEN))

    # -----------------------------------------------------------------------
    # STEP 1: Tour Products & Departures
    # -----------------------------------------------------------------------

    def _create_tour_products(self, year: int) -> list:
        """Tạo 5 TourProduct từ dữ liệu tĩnh TOUR_DATA."""
        from core.models import Category, Destination, TourPage, TourProduct

        self.stdout.write(colorize("\n  📦 BƯỚC 1/4 — Tạo Tour & Lịch khởi hành\n", Color.BOLD))

        # Đảm bảo có Category và Destination tối thiểu
        cat_domestic, _ = Category.objects.get_or_create(
            slug="trong-nuoc",
            defaults={"name": "Tour Trong Nước", "icon": "🇻🇳"},
        )
        cat_beach, _ = Category.objects.get_or_create(
            slug="bien-dao",
            defaults={"name": "Tour Biển Đảo", "icon": "🏖️"},
        )

        tour_products = []
        bar = ProgressBar(len(TOUR_DATA), "Tạo TourProduct", Color.BLUE)

        for data in TOUR_DATA:
            # Tạo TourPage (Wagtail Page — cần parent page)
            try:
                from wagtail.models import Page
                root_page = Page.objects.filter(depth=1).first()
                parent    = root_page.get_children().first() or root_page
            except Exception:
                parent = None

            # Kiểm tra đã tồn tại chưa
            existing = TourProduct.objects.filter(sku_code=data["sku_code"]).first()
            if existing:
                tour_products.append(existing)
                bar.update()
                continue

            # Tạo TourPage nếu có parent Wagtail
            tour_page = None
            if parent:
                try:
                    from core.models import TourPage as TP
                    tp = TP(
                        title=data["title"],
                        slug=data["sku_code"].lower().replace("-", "_"),
                        duration_days=data["duration"],
                        duration_nights=data["duration"] - 1,
                        category=cat_domestic,
                    )
                    parent.add_child(instance=tp)
                    tour_page = tp
                except Exception:
                    pass

            if not tour_page:
                # Fallback: dùng TourPage đầu tiên nếu không tạo được
                from core.models import TourPage as TP
                tour_page = TP.objects.first()

            if not tour_page:
                bar.update()
                continue

            tp_obj = TourProduct.objects.create(
                tour_page=tour_page,
                sku_code=data["sku_code"],
                base_price=data["base_price"],
                child_price=data["base_price"] * Decimal("0.7"),
                status="ACTIVE",
            )
            tour_products.append(tp_obj)
            bar.update()

        bar.finish(f"Hoàn thành {len(tour_products)} TourProduct")
        return tour_products

    def _create_departures(self, tour_products: list, year: int) -> list:
        """Tạo 20 TourDeparture trải rác trong năm 2026 (4 chuyến/tour)."""
        from core.models import TourDeparture

        DEPARTURES_PER_TOUR = 4
        total = len(tour_products) * DEPARTURES_PER_TOUR
        bar   = ProgressBar(total, "Tạo TourDeparture", Color.CYAN)

        departures = []
        # Chia đều 4 chuyến vào 4 quý trong năm
        quarters = [
            (date(year, 1, 15),  date(year, 3, 31)),
            (date(year, 4, 1),   date(year, 6, 30)),
            (date(year, 7, 1),   date(year, 9, 30)),
            (date(year, 10, 1),  date(year, 12, 20)),
        ]

        for tp in tour_products:
            for q_idx, (q_start, q_end) in enumerate(quarters):
                # Random ngày khởi hành trong quý
                delta = (q_end - q_start).days
                start = q_start + timedelta(days=random.randint(0, delta - tp.tour_page.duration_days))
                end   = start + timedelta(days=tp.tour_page.duration_days)

                total_seats = random.choice([20, 25, 30, 35, 40])
                # Các chuyến quá khứ đã đặt gần hết, tương lai còn nhiều chỗ
                if start < date.today():
                    booked = random.randint(int(total_seats * 0.6), total_seats)
                else:
                    booked = random.randint(0, int(total_seats * 0.4))
                available = max(total_seats - booked, 0)

                dep_code = f"{tp.sku_code}-Q{q_idx + 1}-{year}"

                dep, created = TourDeparture.objects.get_or_create(
                    departure_code=dep_code,
                    defaults={
                        "tour_product":    tp,
                        "start_date":      start,
                        "end_date":        end,
                        "departure_point": random.choice(DEPARTURE_POINTS),
                        "total_seats":     total_seats,
                        "available_seats": available,
                        "guide_name":      random.choice(GUIDE_NAMES),
                        "status":          "OPEN" if available > 0 else "FULL",
                        "price_override":  (
                            tp.base_price * Decimal(str(round(random.uniform(0.9, 1.15), 2)))
                            if random.random() < 0.3 else None
                        ),
                    },
                )
                departures.append(dep)
                bar.update()

        bar.finish(f"Hoàn thành {len(departures)} TourDeparture")
        return departures

    # -----------------------------------------------------------------------
    # STEP 2: Customers
    # -----------------------------------------------------------------------

    def _create_customers(self, num_customers: int) -> list:
        """Tạo N Customer với thông tin giả lập bằng Faker."""
        from core.models import Customer

        self.stdout.write(colorize("\n  👥 BƯỚC 2/4 — Tạo Khách hàng\n", Color.BOLD))
        bar = ProgressBar(num_customers, "Tạo Customer", Color.MAGENTA)

        customers   = []
        batch_size  = 50
        user_batch  = []
        profile_batch = []

        for i in range(num_customers):
            # Sinh thông tin ngẫu nhiên
            first = fake.first_name()
            last  = fake.last_name()
            username = f"mock_{fake.user_name()[:12]}_{i}"

            user = User(
                username=username,
                email=f"{username}@{fake.free_email_domain()}",
                first_name=first,
                last_name=last,
                is_active=True,
            )
            user.set_unusable_password()
            user.save()
            
            tier = weighted_choice(MEMBERSHIP_WEIGHTS)
            profile = Customer(
                user=user,
                phone=fake.phone_number()[:15],
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=70),
                gender=random.choice(["M", "F"]),
                address=fake.address()[:255],
                id_number=fake.numerify("0##########"),
                membership_tier=tier,
                total_spent=Decimal("0"),
                loyalty_points=random.randint(0, 5000),
            )
            profile_batch.append(profile)
            customers.append(profile)

            # Bulk create mỗi batch_size
            if len(profile_batch) >= batch_size or i == num_customers - 1:
                Customer.objects.bulk_create(profile_batch, ignore_conflicts=True)
                profile_batch.clear()

            bar.update()

        bar.finish(f"Hoàn thành {len(customers)} Customer")
        return customers

    # -----------------------------------------------------------------------
    # STEP 3: Bookings
    # -----------------------------------------------------------------------

    def _create_bookings(
        self,
        num_bookings: int,
        customers: list,
        departures: list,
        year: int,
    ) -> list:
        """
        Tạo N Booking phân bổ ngẫu nhiên.
        - booking_date rải rác trong năm 2026
        - Tự trừ available_seats của TourDeparture
        - Tự cộng total_amount vào Customer.total_spent
        """
        from core.models import Booking

        self.stdout.write(colorize("\n  📋 BƯỚC 3/4 — Tạo Đơn đặt chỗ\n", Color.BOLD))
        bar = ProgressBar(num_bookings, "Tạo Booking", Color.YELLOW)

        # Cache available_seats để không query DB liên tục
        seat_cache: dict[int, int] = {d.pk: d.available_seats for d in departures}
        open_deps = [d for d in departures if seat_cache[d.pk] > 0]

        if not open_deps:
            self.stdout.write(colorize("\n  ⚠️  Không còn chuyến nào có chỗ trống!\n", Color.RED))
            return []

        bookings_to_create = []
        created_codes      = set()
        customer_spent     = {}      # pk → tổng cộng dồn
        skipped            = 0

        for i in range(num_bookings):
            if not open_deps:
                skipped += num_bookings - i
                bar.update(num_bookings - i)
                break

            customer  = random.choice(customers)
            departure = random.choice(open_deps)

            num_adults   = random.choices([1, 2, 3, 4], weights=[30, 45, 15, 10])[0]
            num_children = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
            num_pax      = num_adults + num_children

            # Không đặt quá số chỗ còn lại
            avail = seat_cache[departure.pk]
            if num_pax > avail:
                num_adults   = min(num_adults, avail)
                num_children = 0
                num_pax      = num_adults

            if num_pax == 0:
                # Xóa departure khỏi danh sách mở
                open_deps.remove(departure)
                bar.update()
                continue

            # Tính tiền
            price         = departure.effective_price
            child_price   = departure.tour_product.child_price or price * Decimal("0.7")
            total_amount  = price * num_adults + child_price * num_children

            discount_pct  = random.choices(
                [0, 5, 10, 15],
                weights=[60, 20, 15, 5],
            )[0]
            discount_amt  = total_amount * Decimal(str(discount_pct)) / 100
            final_amount  = total_amount - discount_amt

            # Sinh booking_code duy nhất
            for _ in range(10):
                code = generate_booking_code()
                if code not in created_codes:
                    created_codes.add(code)
                    break

            # Trạng thái đơn hàng
            booking_date = random_date_in_year(year)
            if departure.start_date < date.today():
                # Chuyến đã đi: hầu hết đã hoàn thành
                status = random.choices(
                    ["COMPLETED", "PAID", "CANCELLED", "REFUNDED"],
                    weights=[55, 20, 15, 10],
                )[0]
            else:
                # Chuyến tương lai: hầu hết đang chờ / đã confirm
                status = random.choices(
                    ["PENDING", "CONFIRMED", "PAID", "CANCELLED"],
                    weights=[25, 35, 30, 10],
                )[0]

            bookings_to_create.append(
                Booking(
                    customer=customer,
                    departure=departure,
                    booking_code=code,
                    booking_date=booking_date,
                    num_adults=num_adults,
                    num_children=num_children,
                    total_amount=total_amount,
                    discount_amount=discount_amt,
                    final_amount=final_amount,
                    status=status,
                    special_request=(
                        fake.sentence(nb_words=8) if random.random() < 0.2 else ""
                    ),
                )
            )

            # Cập nhật cache chỗ ngồi
            seat_cache[departure.pk] -= num_pax
            if seat_cache[departure.pk] <= 0:
                open_deps.remove(departure)

            # Cộng dồn total_spent (chỉ với booking PAID / COMPLETED)
            if status in ("PAID", "COMPLETED"):
                customer_spent[customer.pk] = (
                    customer_spent.get(customer.pk, Decimal("0")) + final_amount
                )

            # Bulk create mỗi 200 records
            if len(bookings_to_create) >= 200 or i == num_bookings - 1:
                Booking.objects.bulk_create(bookings_to_create, ignore_conflicts=True)
                bookings_to_create.clear()

            bar.update()

        if skipped > 0:
            self.stdout.write(
                colorize(f"\n  ⚠️  Bỏ qua {skipped} booking do hết chỗ trống.\n", Color.YELLOW)
            )

        bar.finish(f"Hoàn thành {len(created_codes)} Booking")

        # Cập nhật available_seats vào DB
        self._update_seat_cache(seat_cache, departures)

        # Cập nhật tổng chi tiêu customer (tạm thời, sẽ chính xác hóa ở step 5)
        if customer_spent:
            self._bulk_update_spent(customer_spent)

        return list(Booking.objects.all())

    def _update_seat_cache(self, seat_cache: dict, departures: list) -> None:
        """Đồng bộ lại available_seats từ cache vào DB (1 lần duy nhất)."""
        from core.models import TourDeparture

        updates = []
        for dep in departures:
            dep.available_seats = seat_cache.get(dep.pk, dep.available_seats)
            dep.status = "FULL" if dep.available_seats <= 0 else "OPEN"
            updates.append(dep)

        TourDeparture.objects.bulk_update(updates, ["available_seats", "status"])

    def _bulk_update_spent(self, customer_spent: dict) -> None:
        """Cộng dồn total_spent vào Customer theo dict {pk: amount}."""
        from core.models import Customer

        customers_to_update = Customer.objects.filter(pk__in=customer_spent.keys())
        for c in customers_to_update:
            c.total_spent += customer_spent.get(c.pk, Decimal("0"))
        Customer.objects.bulk_update(customers_to_update, ["total_spent"])

    # -----------------------------------------------------------------------
    # STEP 4: Payments
    # -----------------------------------------------------------------------

    def _create_payments(self, bookings: list) -> None:
        """
        Tạo Payment cho các Booking có status PAID / COMPLETED.
        Mỗi booking PAID sẽ có 1–2 payment (đặt cọc + thanh toán nốt).
        """
        from core.models import Payment

        self.stdout.write(colorize("\n  💳 BƯỚC 4/4 — Tạo Thanh toán\n", Color.BOLD))

        paid_bookings = [
            b for b in bookings
            if b.status in ("PAID", "COMPLETED")
        ]

        if not paid_bookings:
            self.stdout.write(
                colorize("  ⚠️  Không có booking PAID nào để tạo payment.\n", Color.YELLOW)
            )
            return

        bar = ProgressBar(len(paid_bookings), "Tạo Payment", Color.GREEN)

        payments_to_create = []
        batch_size = 300

        for booking in paid_bookings:
            method = random.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS)[0]
            paid_at = booking.booking_date + timedelta(
                minutes=random.randint(5, 60 * 24 * 3)
            )

            # 70% trả 1 lần, 30% đặt cọc trước + trả nốt
            if random.random() < 0.7:
                payments_to_create.append(
                    Payment(
                        booking=booking,
                        transaction_id=f"TXN-{fake.uuid4()[:16].upper()}",
                        amount=booking.final_amount,
                        method=method,
                        status="SUCCESS",
                        paid_at=paid_at,
                        note="Thanh toán toàn bộ",
                    )
                )
            else:
                # Đặt cọc 30%
                deposit = (booking.final_amount * Decimal("0.3")).quantize(Decimal("1"))
                remaining = booking.final_amount - deposit

                payments_to_create.append(
                    Payment(
                        booking=booking,
                        transaction_id=f"TXN-{fake.uuid4()[:16].upper()}",
                        amount=deposit,
                        method=method,
                        status="SUCCESS",
                        paid_at=paid_at,
                        note="Đặt cọc 30%",
                    )
                )
                payments_to_create.append(
                    Payment(
                        booking=booking,
                        transaction_id=f"TXN-{fake.uuid4()[:16].upper()}",
                        amount=remaining,
                        method=random.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS)[0],
                        status="SUCCESS",
                        paid_at=paid_at + timedelta(days=random.randint(1, 14)),
                        note="Thanh toán nốt 70%",
                    )
                )

            if len(payments_to_create) >= batch_size:
                Payment.objects.bulk_create(payments_to_create, ignore_conflicts=True)
                payments_to_create.clear()

            bar.update()

        if payments_to_create:
            Payment.objects.bulk_create(payments_to_create, ignore_conflicts=True)

        bar.finish(f"Hoàn thành cho {len(paid_bookings)} booking PAID")

    # -----------------------------------------------------------------------
    # STEP 5: Finalize — cập nhật membership_tier chính xác
    # -----------------------------------------------------------------------

    def _finalize_stats(self, customers: list) -> None:
        """
        Tính lại total_spent từ Payment thực tế và cập nhật membership_tier.
        Đảm bảo tính nhất quán sau khi bulk_create xong.
        """
        from django.db.models import Sum

        from core.models import Customer, Payment

        self.stdout.write(colorize("\n  🔄 Finalize — Cập nhật hạng thành viên...", Color.DIM))

        # Tính total_spent chính xác từ Payment SUCCESS
        from django.db.models import Sum, Q
        spent_data = (
            Payment.objects
            .filter(status="SUCCESS")
            .values("booking__customer_id")
            .annotate(total=Sum("amount"))
        )
        spent_map = {row["booking__customer_id"]: row["total"] for row in spent_data}

        to_update = []
        all_customers = Customer.objects.select_related("user").all()

        for c in all_customers:
            real_spent = spent_map.get(c.pk, Decimal("0"))
            c.total_spent = real_spent

            # Tính hạng thành viên
            if real_spent >= 100_000_000:
                c.membership_tier = "DIAMOND"
            elif real_spent >= 50_000_000:
                c.membership_tier = "VIP"
            elif real_spent >= 20_000_000:
                c.membership_tier = "GOLD"
            elif real_spent >= 5_000_000:
                c.membership_tier = "SILVER"
            else:
                c.membership_tier = "STANDARD"

            to_update.append(c)

        Customer.objects.bulk_update(to_update, ["total_spent", "membership_tier"])
        self.stdout.write(colorize(f" ✓ Đã cập nhật {len(to_update)} hồ sơ\n", Color.GREEN))

    # -----------------------------------------------------------------------
    # Banner & Summary
    # -----------------------------------------------------------------------

    def _print_banner(self) -> None:
        banner = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║    🌏  TRAVEL ERP — Mock Data Generator v1.0             ║
  ║    Sinh dữ liệu giả lập cho hệ thống đặt vé du lịch     ║
  ╚══════════════════════════════════════════════════════════╝
"""
        self.stdout.write(colorize(banner, Color.CYAN, Color.BOLD))

    def _print_summary(
        self,
        tour_products: list,
        departures: list,
        customers: list,
        bookings: list,
    ) -> None:
        from core.models import Booking, Payment

        total_revenue = (
            Payment.objects.filter(status="SUCCESS").aggregate(
                t=__import__("django.db.models", fromlist=["Sum"]).Sum("amount")
            )["t"]
            or Decimal("0")
        )

        paid_count      = Booking.objects.filter(status__in=["PAID", "COMPLETED"]).count()
        cancelled_count = Booking.objects.filter(status="CANCELLED").count()

        summary = f"""
  ╔══════════════════════════════════════════════════════════╗
  ║  ✅  HOÀN THÀNH — Tóm tắt dữ liệu đã sinh               ║
  ╠══════════════════════════════════════════════════════════╣
  ║  📦  TourProduct    : {len(tour_products):<5}  (5 tour)                    ║
  ║  ✈️   TourDeparture  : {len(departures):<5}  (20 chuyến, cả năm 2026)      ║
  ║  👥  Customer       : {len(customers):<5}  (mock users)                ║
  ║  📋  Booking        : {Booking.objects.count():<5}  tổng ({paid_count} PAID, {cancelled_count} HỦY)        ║
  ║  💳  Payment        : {Payment.objects.count():<5}  giao dịch               ║
  ║  💰  Doanh thu GIẢ  : {total_revenue:>15,.0f} VNĐ           ║
  ╠══════════════════════════════════════════════════════════╣
  ║  👉  Chạy Superset để xem Dashboard phân tích!           ║
  ╚══════════════════════════════════════════════════════════╝
"""
        self.stdout.write(colorize(summary, Color.GREEN, Color.BOLD))
