"""
wagtail_hooks.py — Ứng dụng core
Đăng ký giao diện quản trị Wagtail cho nhóm người dùng ERP/CRM/Sales.

Cấu trúc:
    - CustomerViewSet      : Quản lý hồ sơ khách hàng (CRM)
    - TourProductViewSet   : Quản lý sản phẩm tour (ERP)
    - TourDepartureViewSet : Quản lý lịch khởi hành (ERP)
    - BookingViewSet       : Quản lý đơn đặt chỗ (Sales)
    - PaymentViewSet       : Lịch sử giao dịch thanh toán
"""

from django.contrib.admin.utils import display_for_value
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from wagtail import hooks
from wagtail.admin.menu import Menu, MenuItem, SubmenuMenuItem
from wagtail.admin.panels import (
    FieldPanel,
    FieldRowPanel,
    InlinePanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)
from wagtail.admin.ui.tables import Column, DateColumn
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import Booking, Customer, Payment, TourDeparture, TourProduct


# ===========================================================================
# HELPER — Cột hiển thị màu sắc theo trạng thái
# ===========================================================================

# Mapping trạng thái → màu badge (Bootstrap-style)
STATUS_COLORS = {
    # Booking status
    "PENDING":   ("warning",  "⏳ Chờ xác nhận"),
    "CONFIRMED": ("info",     "📋 Đã xác nhận"),
    "PAID":      ("success",  "✅ Đã thanh toán"),
    "CANCELLED": ("danger",   "❌ Đã hủy"),
    "COMPLETED": ("secondary","🏠 Hoàn thành"),
    "REFUNDED":  ("dark",     "↩️ Hoàn tiền"),
    # Departure status
    "OPEN":      ("success",  "🟢 Đang mở đặt"),
    "FULL":      ("warning",  "🟡 Hết chỗ"),
    "CLOSED":    ("secondary","⚪ Đã đóng"),
    "DEPARTED":  ("info",     "✈️ Đã khởi hành"),
    # Payment status
    "SUCCESS":   ("success",  "✅ Thành công"),
    "FAILED":    ("danger",   "❌ Thất bại"),
    # Membership tier
    "STANDARD":  ("secondary","🥉 Thường"),
    "SILVER":    ("light",    "🥈 Bạc"),
    "GOLD":      ("warning",  "🥇 Vàng"),
    "VIP":       ("primary",  "💎 VIP"),
    "DIAMOND":   ("info",     "💠 Kim cương"),
}


def render_status_badge(value: str) -> str:
    """Trả về HTML badge màu sắc cho một giá trị trạng thái."""
    color, label = STATUS_COLORS.get(value, ("secondary", value))
    return format_html(
        '<span style="'
        "display:inline-block;padding:3px 10px;border-radius:12px;"
        "font-size:0.78em;font-weight:600;white-space:nowrap;"
        "background:var(--w-color-{}-200,#eee);color:var(--w-color-{}-800,#333)"
        '">{}</span>',
        color, color, label,
    )


# ===========================================================================
# VIEWSET — Customer (CRM)
# ===========================================================================

class CustomerViewSet(SnippetViewSet):
    """
    Giao diện quản lý hồ sơ khách hàng.
    Nhân viên CRM xem lịch sử, phân hạng và ghi chú khách hàng.
    """

    model = Customer
    icon = "user"
    menu_label = _("Khách hàng")
    menu_order = 210
    name = "customers"
    add_to_admin_menu = True

    # --- Danh sách (list view) ---
    list_display = [
        "get_full_name",
        "get_email",
        "phone",
        "membership_tier_badge",
        "total_spent_fmt",
        "loyalty_points",
        "created_at",
    ]
    list_filter = ["membership_tier", "gender", "created_at"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "phone",
        "id_number",
    ]
    list_per_page = 25
    ordering = ["-total_spent"]

    # --- Chi tiết (edit view) ---
    panels = [
        TabbedInterface([
            ObjectList([
                MultiFieldPanel([
                    FieldRowPanel([
                        FieldPanel("user"),
                        FieldPanel("phone"),
                    ]),
                    FieldRowPanel([
                        FieldPanel("date_of_birth"),
                        FieldPanel("gender"),
                    ]),
                    FieldPanel("id_number"),
                    FieldPanel("address"),
                ], heading="Thông tin cá nhân"),
            ], heading="👤 Thông tin"),

            ObjectList([
                MultiFieldPanel([
                    FieldRowPanel([
                        FieldPanel("membership_tier"),
                        FieldPanel("loyalty_points"),
                    ]),
                    FieldPanel("total_spent"),
                    FieldPanel("notes"),
                ], heading="Phân hạng & CRM"),
            ], heading="💎 CRM / Thành viên"),
        ])
    ]

    # --- Custom columns ---

# ===========================================================================
# VIEWSET — TourProduct (ERP)
# ===========================================================================

class TourProductViewSet(SnippetViewSet):
    """
    Giao diện quản lý sản phẩm tour.
    ERP Manager xem giá, SKU và trạng thái kinh doanh từng tour.
    """

    model = TourProduct
    icon = "tag"
    menu_label = _("Sản phẩm Tour")
    menu_order = 220
    name = "tour_products"
    add_to_admin_menu = True

    # --- Danh sách ---
    list_display = [
        "sku_code",
        "get_tour_name",
        "base_price_fmt",
        "child_price_fmt",
        "product_status_badge",
        "get_departure_count",
        "updated_at",
    ]
    list_filter = ["status", "tour_page__category"]
    search_fields = [
        "sku_code",
        "tour_page__title",
        "tour_page__destination__name",
    ]
    list_per_page = 20
    ordering = ["sku_code"]

    # --- Chi tiết ---
    panels = [
        MultiFieldPanel([
            FieldPanel("tour_page"),
            FieldRowPanel([
                FieldPanel("sku_code"),
                FieldPanel("status"),
            ]),
            FieldRowPanel([
                FieldPanel("base_price"),
                FieldPanel("child_price"),
            ]),
        ], heading="Thông tin Sản phẩm"),
    ]

    # --- Custom columns ---

# ===========================================================================
# VIEWSET — TourDeparture (ERP)
# ===========================================================================

class TourDepartureViewSet(SnippetViewSet):
    """
    Giao diện quản lý lịch khởi hành.
    Nhân viên Sale theo dõi số ghế trống và đóng/mở chuyến đi.
    """

    model = TourDeparture
    icon = "date"
    menu_label = _("Lịch khởi hành")
    menu_order = 230
    name = "tour_departures"
    add_to_admin_menu = True

    # --- Danh sách ---
    list_display = [
        "departure_code",
        "get_tour_name",
        "start_date",
        "end_date",
        "departure_point",
        "seats_display",
        "effective_price_fmt",
        "departure_status_badge",
        "guide_name",
    ]
    list_filter = [
        "status",
        "tour_product__status",
        "start_date",
        "tour_product__tour_page__category",
    ]
    search_fields = [
        "departure_code",
        "tour_product__sku_code",
        "tour_product__tour_page__title",
        "guide_name",
        "departure_point",
    ]
    list_per_page = 20
    ordering = ["start_date"]

    # --- Chi tiết ---
    panels = [
        TabbedInterface([
            ObjectList([
                MultiFieldPanel([
                    FieldPanel("tour_product"),
                    FieldRowPanel([
                        FieldPanel("departure_code"),
                        FieldPanel("status"),
                    ]),
                    FieldRowPanel([
                        FieldPanel("start_date"),
                        FieldPanel("end_date"),
                    ]),
                    FieldPanel("departure_point"),
                ], heading="Thông tin chuyến"),
            ], heading="✈️ Chuyến đi"),

            ObjectList([
                MultiFieldPanel([
                    FieldRowPanel([
                        FieldPanel("total_seats"),
                        FieldPanel("available_seats"),
                    ]),
                    FieldPanel("price_override"),
                    FieldPanel("guide_name"),
                    FieldPanel("notes"),
                ], heading="Vận hành"),
            ], heading="⚙️ Vận hành"),
        ])
    ]

    # --- Custom columns ---

# ===========================================================================
# VIEWSET — Booking (Sales)
# ===========================================================================

class BookingViewSet(SnippetViewSet):
    """
    Giao diện quản lý đơn đặt chỗ.
    Nhân viên Sale xem và xử lý đơn, đổi trạng thái Pending → Paid.
    """

    model = Booking
    icon = "form"
    menu_label = _("Đơn đặt chỗ")
    menu_order = 240
    name = "bookings"
    add_to_admin_menu = True

    # --- Danh sách ---
    list_display = [
        "booking_code",
        "get_customer_name",
        "get_tour_name",
        "get_departure_date",
        "num_passengers_fmt",
        "final_amount_fmt",
        "booking_status_badge",
        "booking_date",
        "get_payment_status",
    ]
    list_filter = [
        "status",
        "booking_date",
        "departure__status",
        "departure__tour_product__tour_page__category",
        "customer__membership_tier",
    ]
    search_fields = [
        "booking_code",
        "customer__user__first_name",
        "customer__user__last_name",
        "customer__user__email",
        "customer__phone",
        "departure__departure_code",
        "departure__tour_product__sku_code",
        "departure__tour_product__tour_page__title",
    ]
    list_per_page = 30
    ordering = ["-booking_date"]

    # --- Chi tiết ---
    panels = [
        TabbedInterface([
            ObjectList([
                MultiFieldPanel([
                    FieldRowPanel([
                        FieldPanel("booking_code"),
                        FieldPanel("status"),
                    ]),
                    FieldRowPanel([
                        FieldPanel("customer"),
                        FieldPanel("departure"),
                    ]),
                    FieldPanel("booking_date"),
                    FieldPanel("special_request"),
                ], heading="Thông tin đặt chỗ"),
            ], heading="📋 Đặt chỗ"),

            ObjectList([
                MultiFieldPanel([
                    FieldRowPanel([
                        FieldPanel("num_adults"),
                        FieldPanel("num_children"),
                    ]),
                    FieldRowPanel([
                        FieldPanel("total_amount"),
                        FieldPanel("discount_amount"),
                    ]),
                    FieldPanel("final_amount"),
                ], heading="Tài chính"),
            ], heading="💰 Tài chính"),

            ObjectList([
                MultiFieldPanel([
                    FieldPanel("cancelled_at"),
                    FieldPanel("cancel_reason"),
                ], heading="Thông tin hủy"),
            ], heading="❌ Hủy đơn"),
        ])
    ]

    # --- Custom columns ---

# ===========================================================================
# VIEWSET — Payment (Finance)
# ===========================================================================

class PaymentViewSet(SnippetViewSet):
    """
    Lịch sử giao dịch thanh toán (chỉ đọc cho kế toán).
    """

    model = Payment
    icon = "clipboard-list"
    menu_label = _("Thanh toán")
    menu_order = 250
    name = "payments"
    add_to_admin_menu = True

    # --- Danh sách ---
    list_display = [
        "get_transaction_id",
        "get_booking_code",
        "get_customer_name",
        "amount_fmt",
        "method_badge",
        "payment_status_badge",
        "paid_at",
        "created_at",
    ]
    list_filter = [
        "status",
        "method",
        "created_at",
        "paid_at",
    ]
    search_fields = [
        "transaction_id",
        "booking__booking_code",
        "booking__customer__user__first_name",
        "booking__customer__user__last_name",
        "booking__customer__phone",
    ]
    list_per_page = 30
    ordering = ["-created_at"]

    panels = [
        MultiFieldPanel([
            FieldRowPanel([
                FieldPanel("booking"),
                FieldPanel("method"),
            ]),
            FieldRowPanel([
                FieldPanel("amount"),
                FieldPanel("status"),
            ]),
            FieldPanel("transaction_id"),
            FieldPanel("paid_at"),
            FieldPanel("receipt_image"),
            FieldPanel("note"),
        ], heading="Chi tiết Giao dịch"),
    ]

    # --- Custom columns ---

# ===========================================================================
# Đăng ký trực tiếp các ViewSet vào menu Wagtail thay vì dùng Group
# ===========================================================================
register_snippet(CustomerViewSet)
register_snippet(TourProductViewSet)
register_snippet(TourDepartureViewSet)
register_snippet(BookingViewSet)
register_snippet(PaymentViewSet)


# ===========================================================================
# HOOKS — Tuỳ chỉnh bổ sung
# ===========================================================================

@hooks.register("construct_main_menu")
def reorder_menu_items(request, menu_items):
    """
    Sắp xếp lại thứ tự menu trong Wagtail Admin:
    1. Pages (CMS)
    2. Các module ERP được đưa ra ngoài
    3. Images / Documents / Snippets
    4. Reports & Settings
    """
    ORDER_MAP = {
        "explorer":  100,   # Pages
        "customers": 210,
        "tour_products": 220,
        "tour_departures": 230,
        "bookings": 240,
        "payments": 250,
        "images":    300,
        "documents": 310,
        "snippets":  320,
        "reports":   800,
        "settings":  900,
    }
    for item in menu_items:
        if item.name in ORDER_MAP:
            item.order = ORDER_MAP[item.name]


@hooks.register("construct_snippet_listing_buttons")
def add_booking_action_buttons(buttons, snippet, user, context=None, **kwargs):
    """
    Thêm nút hành động nhanh 'Xác nhận đã TT' trên danh sách Booking.
    Chỉ hiển thị khi Booking đang ở trạng thái PENDING hoặc CONFIRMED.
    """
    if not isinstance(snippet, Booking):
        return

    from wagtail.snippets.action_menu import ActionMenuItem

    if snippet.status in ("PENDING", "CONFIRMED"):
        buttons.append(
            ActionMenuItem(
                label="✅ Đánh dấu Đã TT",
                url=f"/admin/confirm-payment/{snippet.pk}/",
                icon_name="tick",
                classname="button button-small button--icon",
            )
        )


@hooks.register("construct_reports_menu")
def hide_reports_from_sales(request, menu_items):
    """
    Ẩn các report nhạy cảm khỏi nhóm Sales (chỉ admin mới xem).
    """
    if not request.user.is_superuser:
        menu_items[:] = [
            item for item in menu_items
            if item.name not in ("locked-pages", "workflow-tasks")
        ]


@hooks.register('insert_global_admin_css')
def global_admin_css():
    return format_html('<link rel="stylesheet" href="/static/css/custom_admin.css">')
