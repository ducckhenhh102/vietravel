"""
models.py — Ứng dụng core
Hệ thống Quản trị Đặt vé Du lịch

Cấu trúc phân hệ:
    - CMS        : Category, Destination, TourPage
    - ERP        : TourProduct, TourDeparture
    - CRM        : Customer
    - Giao dịch  : Booking, Passenger, Payment
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.blocks import (
    CharBlock,
    RichTextBlock,
    StreamBlock,
    StructBlock,
    TimeBlock,
)
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet


from django.utils.html import format_html

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
# PHÂN HỆ CMS — Content Management System
# ===========================================================================


@register_snippet
class Category(models.Model):
    """
    Danh mục tour du lịch (ví dụ: Trong nước, Quốc tế, Nghỉ dưỡng...).
    Đăng ký dạng Snippet để Admin quản lý trực tiếp trong Wagtail.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Tên danh mục"),
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("Định danh URL, ví dụ: trong-nuoc"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Mô tả"),
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Icon (emoji hoặc class)"),
        help_text=_("Ví dụ: ✈️ hoặc fa-plane"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("icon"),
    ]

    class Meta:
        verbose_name = _("Danh mục")
        verbose_name_plural = _("Danh mục Tour")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


@register_snippet
class Destination(models.Model):
    """
    Điểm đến du lịch (ví dụ: Hà Nội, Đà Nẵng, Phú Quốc...).
    Đăng ký dạng Snippet để tái sử dụng trên nhiều Tour.
    """

    name = models.CharField(
        max_length=150,
        verbose_name=_("Tên điểm đến"),
    )
    country = models.CharField(
        max_length=100,
        default="Việt Nam",
        verbose_name=_("Quốc gia"),
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Vùng / Miền"),
        help_text=_("Ví dụ: Miền Bắc, Miền Trung"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Mô tả điểm đến"),
    )
    highlight = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Điểm nổi bật"),
        help_text=_("Một câu mô tả ngắn gọn, hấp dẫn"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        MultiFieldPanel(
            [FieldPanel("name"), FieldPanel("country"), FieldPanel("region")],
            heading="Thông tin địa lý",
        ),
        FieldPanel("description"),
        FieldPanel("highlight"),
    ]

    class Meta:
        verbose_name = _("Điểm đến")
        verbose_name_plural = _("Điểm đến")
        ordering = ["country", "name"]

    def __str__(self) -> str:
        return f"{self.name}, {self.country}"


class ItineraryDayBlock(StructBlock):
    """Block mô tả lịch trình một ngày trong tour."""

    day_number = CharBlock(label=_("Ngày thứ"), max_length=10)
    title = CharBlock(label=_("Tiêu đề ngày"), max_length=200)
    description = RichTextBlock(label=_("Nội dung chi tiết"))
    meals = CharBlock(
        label=_("Bữa ăn"),
        max_length=100,
        required=False,
        help_text=_("Ví dụ: Sáng, Trưa, Tối"),
    )
    accommodation = CharBlock(
        label=_("Chỗ ở"),
        max_length=200,
        required=False,
    )
    thumbnail = ImageChooserBlock(label=_("Hình ảnh ngày"), required=False)

    class Meta:
        icon = "date"
        label = _("Ngày trong lịch trình")


class TourItineraryBlock(StreamBlock):
    """StreamBlock tổng hợp lịch trình nhiều ngày."""

    day = ItineraryDayBlock()

    class Meta:
        label = _("Lịch trình Tour")


class TourPage(Page):
    """
    Trang chi tiết Tour du lịch — kế thừa Wagtail Page.
    Mỗi TourPage đại diện cho một sản phẩm tour được đăng trên website.
    """

    # --- Thông tin cơ bản ---
    tagline = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Slogan / Tagline"),
        help_text=_("Câu mô tả ngắn xuất hiện ở card tour"),
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tour_pages",
        verbose_name=_("Danh mục"),
    )
    destination = models.ForeignKey(
        Destination,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tour_pages",
        verbose_name=_("Điểm đến chính"),
    )
    duration_days = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Số ngày"),
    )
    duration_nights = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Số đêm"),
    )

    # --- Nội dung phong phú ---
    overview = RichTextField(
        blank=True,
        verbose_name=_("Tổng quan chương trình"),
    )
    highlights = RichTextField(
        blank=True,
        verbose_name=_("Điểm nổi bật"),
    )
    includes = RichTextField(
        blank=True,
        verbose_name=_("Dịch vụ bao gồm"),
    )
    excludes = RichTextField(
        blank=True,
        verbose_name=_("Dịch vụ không bao gồm"),
    )
    notes = RichTextField(
        blank=True,
        verbose_name=_("Lưu ý"),
    )

    # --- Lịch trình StreamField ---
    itinerary = StreamField(
        TourItineraryBlock(),
        blank=True,
        use_json_field=True,
        verbose_name=_("Lịch trình chi tiết"),
    )

    # --- SEO & Search ---
    search_fields = Page.search_fields + [
        index.SearchField("tagline"),
        index.SearchField("overview"),
        index.FilterField("category"),
        index.FilterField("destination"),
    ]

    # --- Wagtail Admin Panels ---
    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("tagline"),
                FieldPanel("category"),
                FieldPanel("destination"),
                FieldPanel("duration_days"),
                FieldPanel("duration_nights"),
            ],
            heading="Thông tin chung",
        ),
        MultiFieldPanel(
            [
                FieldPanel("overview"),
                FieldPanel("highlights"),
                FieldPanel("includes"),
                FieldPanel("excludes"),
                FieldPanel("notes"),
            ],
            heading="Nội dung chương trình",
        ),
        FieldPanel("itinerary"),
    ]

    class Meta:
        verbose_name = _("Trang Tour")
        verbose_name_plural = _("Trang Tour Du lịch")

    def __str__(self) -> str:
        duration = f"{self.duration_days}N{self.duration_nights}Đ"
        return f"{self.title} ({duration})"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        # Truyền các lịch khởi hành còn chỗ vào context
        context["available_departures"] = (
            self.product.departures.filter(
                status=TourDeparture.DepartureStatus.OPEN,
                available_seats__gt=0,
                start_date__gte=timezone.now().date(),
            ).order_by("start_date")
            if hasattr(self, "product")
            else []
        )
        return context


# ===========================================================================
# PHÂN HỆ ERP — Enterprise Resource Planning
# ===========================================================================


class TourProduct(models.Model):
    """
    Sản phẩm thương mại liên kết 1-1 với TourPage.
    Chứa thông tin kinh doanh: giá, mã SKU, trạng thái kinh doanh.
    Tách biệt khỏi TourPage để nội dung CMS và dữ liệu ERP độc lập nhau.
    """

    class ProductStatus(models.TextChoices):
        ACTIVE = "ACTIVE", _("Đang kinh doanh")
        INACTIVE = "INACTIVE", _("Tạm dừng")
        DISCONTINUED = "DISCONTINUED", _("Ngừng kinh doanh")

    tour_page = models.OneToOneField(
        TourPage,
        on_delete=models.CASCADE,
        related_name="product",
        verbose_name=_("Trang Tour"),
    )
    sku_code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_("Mã SKU"),
        help_text=_("Ví dụ: TOUR-HN-2025-001"),
    )
    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Giá gốc (VNĐ)"),
        help_text=_("Giá cơ sở trên mỗi người lớn"),
    )
    child_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Giá trẻ em (VNĐ)"),
    )
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        verbose_name=_("Trạng thái"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sản phẩm Tour")
        verbose_name_plural = _("Sản phẩm Tour (ERP)")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.sku_code}] {self.tour_page.title}"


    def get_tour_name(self) -> str:
        return self.tour_page.title
    get_tour_name.short_description = "Tên Tour"
    get_tour_name.admin_order_field = "tour_page__title"

    def base_price_fmt(self) -> str:
        return format_html(
            "<strong>{}</strong> đ",
            f"{self.base_price:,.0f}" if self.base_price else "0",
        )
    base_price_fmt.short_description = "Giá người lớn"
    base_price_fmt.admin_order_field = "base_price"

    def child_price_fmt(self) -> str:
        if self.child_price:
            return format_html("<em>{}</em> đ", f"{self.child_price:,.0f}")
        return format_html('<span style="color:#aaa">—</span>')
    child_price_fmt.short_description = "Giá trẻ em"

    def product_status_badge(self) -> str:
        return render_status_badge(self.status)
    product_status_badge.short_description = "Trạng thái"

    def get_departure_count(self) -> str:
        total = self.departures.count()
        open_ = self.departures.filter(status="OPEN").count()
        return format_html(
            '<span title="Tổng / Đang mở">'
            '<strong>{}</strong> <small style="color:#aaa">/ {} chuyến</small>'
            "</span>",
            open_, total,
        )
    get_departure_count.short_description = "Chuyến mở / Tổng"

class TourDeparture(models.Model):
    """
    Lịch khởi hành cụ thể của một TourProduct.
    Một TourProduct có thể có nhiều TourDeparture (nhiều chuyến đi trong năm).
    Tự động quản lý số ghế trống và trạng thái mở/đóng.
    """

    class DepartureStatus(models.TextChoices):
        OPEN = "OPEN", _("Đang mở đặt")
        FULL = "FULL", _("Hết chỗ")
        CLOSED = "CLOSED", _("Đã đóng")
        CANCELLED = "CANCELLED", _("Đã hủy")
        COMPLETED = "COMPLETED", _("Đã hoàn thành")

    tour_product = models.ForeignKey(
        TourProduct,
        on_delete=models.CASCADE,
        related_name="departures",
        verbose_name=_("Sản phẩm Tour"),
    )
    departure_code = models.CharField(
        max_length=40,
        unique=True,
        verbose_name=_("Mã chuyến"),
        help_text=_("Ví dụ: TOUR-HN-2025-001-DEP-01"),
    )
    start_date = models.DateField(
        verbose_name=_("Ngày khởi hành"),
    )
    end_date = models.DateField(
        verbose_name=_("Ngày về"),
    )
    departure_point = models.CharField(
        max_length=200,
        verbose_name=_("Điểm khởi hành"),
        help_text=_("Ví dụ: Sân bay Tân Sơn Nhất - 06:00"),
    )
    total_seats = models.PositiveSmallIntegerField(
        verbose_name=_("Tổng số chỗ"),
    )
    available_seats = models.PositiveSmallIntegerField(
        verbose_name=_("Số chỗ còn lại"),
    )
    price_override = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Giá riêng chuyến này"),
        help_text=_("Để trống nếu dùng giá gốc từ TourProduct"),
    )
    guide_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Tên hướng dẫn viên"),
    )
    status = models.CharField(
        max_length=20,
        choices=DepartureStatus.choices,
        default=DepartureStatus.OPEN,
        verbose_name=_("Trạng thái chuyến"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Ghi chú nội bộ"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Lịch khởi hành")
        verbose_name_plural = _("Lịch khởi hành")
        ordering = ["start_date"]

    def __str__(self) -> str:
        return (
            f"{self.tour_product.sku_code} | "
            f"{self.start_date.strftime('%d/%m/%Y')} | "
            f"Còn {self.available_seats}/{self.total_seats} chỗ"
        )

    @property
    def effective_price(self) -> models.DecimalField:
        """Trả về giá thực tế: ưu tiên giá riêng, sau đó giá gốc."""
        return self.price_override or self.tour_product.base_price

    @property
    def is_available(self) -> bool:
        """Kiểm tra chuyến còn chỗ và đang mở đặt."""
        return (
            self.status == self.DepartureStatus.OPEN
            and self.available_seats > 0
            and self.start_date >= timezone.now().date()
        )

    def save(self, *args, **kwargs):
        """Tự động cập nhật trạng thái FULL khi hết chỗ."""
        if self.available_seats == 0 and self.status == self.DepartureStatus.OPEN:
            self.status = self.DepartureStatus.FULL
        super().save(*args, **kwargs)


# ===========================================================================
# PHÂN HỆ CRM — Customer Relationship Management
# ===========================================================================


    def get_tour_name(self) -> str:
        return self.tour_product.tour_page.title
    get_tour_name.short_description = "Tên Tour"
    get_tour_name.admin_order_field = "tour_product__tour_page__title"

    def seats_display(self) -> str:
        pct = (self.available_seats / self.total_seats * 100) if self.total_seats else 0
        bar_color = (
            "#22c55e" if pct > 50
            else "#f59e0b" if pct > 20
            else "#ef4444"
        )
        return format_html(
            """
            <div style="min-width:100px">
              <div style="display:flex;justify-content:space-between;
                          font-size:0.82em;margin-bottom:3px">
                <strong>{avail}</strong>
                <span style="color:#999">/ {total} chỗ</span>
              </div>
              <div style="background:#e5e7eb;border-radius:4px;height:6px;overflow:hidden">
                <div style="width:{pct}%;height:100%;
                            background:{color};border-radius:4px;
                            transition:width 0.3s"></div>
              </div>
            </div>
            """,
            avail=self.available_seats,
            total=self.total_seats,
            pct=f"{pct:.0f}",
            color=bar_color,
        )
    seats_display.short_description = "Chỗ còn / Tổng"
    seats_display.admin_order_field = "available_seats"

    def effective_price_fmt(self) -> str:
        price = self.effective_price
        if self.price_override:
            return format_html(
                '<span style="color:#f59e0b;font-weight:600">'
                "{} đ ✦</span>",
                f"{price:,.0f}" if price else "0",
            )
        return format_html("{} đ", f"{price:,.0f}" if price else "0")
    effective_price_fmt.short_description = "Giá/người"

    def departure_status_badge(self) -> str:
        return render_status_badge(self.status)
    departure_status_badge.short_description = "Trạng thái"

class Customer(models.Model):
    """
    Hồ sơ khách hàng — liên kết 1-1 với Django User.
    Mở rộng thông tin cá nhân và phân hạng thành viên.
    """

    class MembershipTier(models.TextChoices):
        STANDARD = "STANDARD", _("Thành viên thường")
        SILVER = "SILVER", _("Thành viên Bạc")
        GOLD = "GOLD", _("Thành viên Vàng")
        VIP = "VIP", _("Thành viên VIP")
        DIAMOND = "DIAMOND", _("Thành viên Kim cương")

    class GenderChoices(models.TextChoices):
        MALE = "M", _("Nam")
        FEMALE = "F", _("Nữ")
        OTHER = "O", _("Khác")

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile",
        verbose_name=_("Tài khoản người dùng"),
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_("Số điện thoại"),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Ngày sinh"),
    )
    gender = models.CharField(
        max_length=1,
        choices=GenderChoices.choices,
        blank=True,
        verbose_name=_("Giới tính"),
    )
    address = models.TextField(
        blank=True,
        verbose_name=_("Địa chỉ"),
    )
    id_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("CCCD / Hộ chiếu"),
    )
    membership_tier = models.CharField(
        max_length=10,
        choices=MembershipTier.choices,
        default=MembershipTier.STANDARD,
        verbose_name=_("Hạng thành viên"),
    )
    total_spent = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name=_("Tổng chi tiêu (VNĐ)"),
        help_text=_("Tự động cập nhật khi thanh toán thành công"),
    )
    loyalty_points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Điểm tích lũy"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Ghi chú CRM"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Khách hàng")
        verbose_name_plural = _("Khách hàng (CRM)")
        ordering = ["-total_spent"]

    def __str__(self) -> str:
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} [{self.get_membership_tier_display()}]"

    def update_membership_tier(self) -> None:
        """
        Cập nhật hạng thành viên dựa trên tổng chi tiêu.
        Gọi sau mỗi lần thanh toán thành công.
        """
        spent = self.total_spent
        if spent >= 100_000_000:
            self.membership_tier = self.MembershipTier.DIAMOND
        elif spent >= 50_000_000:
            self.membership_tier = self.MembershipTier.VIP
        elif spent >= 20_000_000:
            self.membership_tier = self.MembershipTier.GOLD
        elif spent >= 5_000_000:
            self.membership_tier = self.MembershipTier.SILVER
        else:
            self.membership_tier = self.MembershipTier.STANDARD
        self.save(update_fields=["membership_tier"])


# ===========================================================================
# PHÂN HỆ GIAO DỊCH — Booking & Payment
# ===========================================================================


    def get_full_name(self) -> str:
        return self.user.get_full_name() or self.user.username
    get_full_name.short_description = "Họ và tên"
    get_full_name.admin_order_field = "user__last_name"

    def get_email(self) -> str:
        return self.user.email
    get_email.short_description = "Email"

    def membership_tier_badge(self) -> str:
        return render_status_badge(self.membership_tier)
    membership_tier_badge.short_description = "Hạng thành viên"

    def total_spent_fmt(self) -> str:
        return format_html(
            "<strong>{}</strong> <small>VNĐ</small>",
            f"{self.total_spent:,.0f}" if self.total_spent else "0",
        )
    total_spent_fmt.short_description = "Tổng chi tiêu"
    total_spent_fmt.admin_order_field = "total_spent"

class Booking(models.Model):
    """
    Đơn đặt tour — trung tâm của phân hệ giao dịch.
    Ghi nhận thông tin đặt chỗ của khách hàng cho một lịch khởi hành.
    """

    class BookingStatus(models.TextChoices):
        PENDING = "PENDING", _("Chờ xác nhận")
        CONFIRMED = "CONFIRMED", _("Đã xác nhận")
        PAID = "PAID", _("Đã thanh toán")
        CANCELLED = "CANCELLED", _("Đã hủy")
        COMPLETED = "COMPLETED", _("Hoàn thành")
        REFUNDED = "REFUNDED", _("Đã hoàn tiền")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Khách hàng"),
    )
    departure = models.ForeignKey(
        TourDeparture,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("Lịch khởi hành"),
    )
    booking_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Mã đặt tour"),
        help_text=_("Tự động sinh, ví dụ: BK20250101001"),
    )
    booking_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Ngày đặt"),
    )
    num_adults = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Số người lớn"),
    )
    num_children = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Số trẻ em"),
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("Tổng tiền (VNĐ)"),
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Số tiền giảm giá"),
    )
    final_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("Thành tiền sau giảm giá"),
    )
    status = models.CharField(
        max_length=15,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        verbose_name=_("Trạng thái đơn"),
    )
    special_request = models.TextField(
        blank=True,
        verbose_name=_("Yêu cầu đặc biệt"),
        help_text=_("Phòng riêng, ăn chay, hỗ trợ xe lăn..."),
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Thời điểm hủy"),
    )
    cancel_reason = models.TextField(
        blank=True,
        verbose_name=_("Lý do hủy"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Đơn đặt tour")
        verbose_name_plural = _("Đơn đặt tour")
        ordering = ["-booking_date"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["booking_date"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.booking_code}] "
            f"{self.customer} — "
            f"{self.departure.tour_product.tour_page.title}"
        )

    @property
    def num_passengers(self) -> int:
        """Tổng số hành khách trong đơn."""
        return self.num_adults + self.num_children

    def save(self, *args, **kwargs):
        """Tự động tính final_amount nếu chưa có."""
        if not self.final_amount:
            self.final_amount = self.total_amount - self.discount_amount
        super().save(*args, **kwargs)


    def get_customer_name(self) -> str:
        name = self.customer.user.get_full_name() or self.customer.user.username
        tier = self.customer.membership_tier
        tier_icons = {
            "VIP": "💎", "DIAMOND": "💠", "GOLD": "🥇",
            "SILVER": "🥈", "STANDARD": "",
        }
        icon = tier_icons.get(tier, "")
        return format_html(
            "{} <strong>{}</strong>",
            icon, name,
        )
    get_customer_name.short_description = "Khách hàng"
    get_customer_name.admin_order_field = "customer__user__last_name"

    def get_tour_name(self) -> str:
        return self.departure.tour_product.tour_page.title
    get_tour_name.short_description = "Tour"
    get_tour_name.admin_order_field = "departure__tour_product__tour_page__title"

    def get_departure_date(self) -> str:
        return format_html(
            '<span style="white-space:nowrap">{}</span>',
            self.departure.start_date.strftime("%d/%m/%Y"),
        )
    get_departure_date.short_description = "Ngày khởi hành"
    get_departure_date.admin_order_field = "departure__start_date"

    def num_passengers_fmt(self) -> str:
        return format_html(
            "{}🧑 + {}👶 = <strong>{}</strong>",
            self.num_adults,
            self.num_children,
            self.num_passengers,
        )
    num_passengers_fmt.short_description = "Hành khách"

    def final_amount_fmt(self) -> str:
        return format_html(
            '<strong style="color:#059669">{}</strong> đ',
            f"{self.final_amount:,.0f}" if self.final_amount else "0",
        )
    final_amount_fmt.short_description = "Thành tiền"
    final_amount_fmt.admin_order_field = "final_amount"

    def booking_status_badge(self) -> str:
        return render_status_badge(self.status)
    booking_status_badge.short_description = "Trạng thái"

    def get_payment_status(self) -> str:
        last_payment = self.payments.order_by("-created_at").first()
        if not last_payment:
            return format_html('<span style="color:#aaa">—</span>')
        return render_status_badge(last_payment.status)
    get_payment_status.short_description = "TT Thanh toán"

class Passenger(models.Model):
    """
    Thông tin từng hành khách trong một đơn đặt tour.
    Một Booking có thể có nhiều Passenger.
    """

    class PassengerType(models.TextChoices):
        ADULT = "ADULT", _("Người lớn")
        CHILD = "CHILD", _("Trẻ em (2–11 tuổi)")
        INFANT = "INFANT", _("Em bé (dưới 2 tuổi)")

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="passengers",
        verbose_name=_("Đơn đặt tour"),
    )
    full_name = models.CharField(
        max_length=200,
        verbose_name=_("Họ và tên"),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Ngày sinh"),
    )
    id_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("CCCD / Hộ chiếu"),
    )
    passenger_type = models.CharField(
        max_length=10,
        choices=PassengerType.choices,
        default=PassengerType.ADULT,
        verbose_name=_("Loại hành khách"),
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_("Số điện thoại"),
    )
    is_lead = models.BooleanField(
        default=False,
        verbose_name=_("Là người đại diện đoàn"),
    )

    class Meta:
        verbose_name = _("Hành khách")
        verbose_name_plural = _("Danh sách hành khách")
        ordering = ["-is_lead", "full_name"]

    def __str__(self) -> str:
        lead_label = " [Đại diện]" if self.is_lead else ""
        return f"{self.full_name}{lead_label} — {self.booking.booking_code}"


class Payment(models.Model):
    """
    Giao dịch thanh toán cho một đơn đặt tour.
    Một Booking có thể có nhiều Payment (đặt cọc, thanh toán nốt...).
    """

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "BANK_TRANSFER", _("Chuyển khoản ngân hàng")
        CASH = "CASH", _("Tiền mặt")
        CREDIT_CARD = "CREDIT_CARD", _("Thẻ tín dụng")
        MOMO = "MOMO", _("Ví MoMo")
        VNPAY = "VNPAY", _("VNPay")
        ZALOPAY = "ZALOPAY", _("ZaloPay")

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Chờ xác nhận")
        SUCCESS = "SUCCESS", _("Thành công")
        FAILED = "FAILED", _("Thất bại")
        REFUNDED = "REFUNDED", _("Đã hoàn tiền")

    booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("Đơn đặt tour"),
    )
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_("Mã giao dịch"),
        help_text=_("Mã do cổng thanh toán hoặc ngân hàng trả về"),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("Số tiền thanh toán"),
    )
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name=_("Phương thức thanh toán"),
    )
    status = models.CharField(
        max_length=15,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_("Trạng thái giao dịch"),
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Thời điểm thanh toán"),
    )
    note = models.TextField(
        blank=True,
        verbose_name=_("Ghi chú giao dịch"),
    )
    receipt_image = models.ImageField(
        upload_to="receipts/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("Ảnh biên lai / chứng từ"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Thanh toán")
        verbose_name_plural = _("Lịch sử thanh toán")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"TT-{self.booking.booking_code} | "
            f"{self.get_method_display()} | "
            f"{self.amount:,.0f} VNĐ | "
            f"{self.get_status_display()}"
        )

    def save(self, *args, **kwargs):
        """
        Sau khi thanh toán thành công, cập nhật:
        - Trạng thái Booking → PAID
        - Tổng chi tiêu của Customer
        - Hạng thành viên Customer
        """
        super().save(*args, **kwargs)

        if self.status == self.PaymentStatus.SUCCESS:
            booking = self.booking
            # Cập nhật trạng thái đơn hàng
            if booking.status != Booking.BookingStatus.PAID:
                booking.status = Booking.BookingStatus.PAID
                booking.save(update_fields=["status"])

            # Cập nhật tổng chi tiêu của khách hàng
            customer = booking.customer
            customer.total_spent += self.amount
            customer.save(update_fields=["total_spent"])

            # Tự động nâng hạng thành viên
            customer.update_membership_tier()

    def get_transaction_id(self) -> str:
        if self.transaction_id:
            return format_html(
                '<code style="font-size:0.8em">{}</code>',
                self.transaction_id[:20],
            )
        return format_html('<span style="color:#aaa">Chưa có</span>')
    get_transaction_id.short_description = "Mã giao dịch"

    def get_booking_code(self) -> str:
        return format_html(
            '<strong>{}</strong>', self.booking.booking_code
        )
    get_booking_code.short_description = "Mã đặt tour"
    get_booking_code.admin_order_field = "booking__booking_code"

    def get_customer_name(self) -> str:
        return self.booking.customer.user.get_full_name()
    get_customer_name.short_description = "Khách hàng"

    def amount_fmt(self) -> str:
        return format_html(
            '<strong style="color:#059669">{}</strong> đ',
            f"{self.amount:,.0f}" if self.amount else "0",
        )
    amount_fmt.short_description = "Số tiền"
    amount_fmt.admin_order_field = "amount"

    def method_badge(self) -> str:
        icons = {
            "BANK_TRANSFER": "🏦",
            "CASH": "💵",
            "CREDIT_CARD": "💳",
            "MOMO": "🟣",
            "VNPAY": "🔵",
            "ZALOPAY": "🟢",
        }
        icon = icons.get(self.method, "💳")
        return format_html(
            "{} {}",
            icon,
            self.get_method_display(),
        )
    method_badge.short_description = "Phương thức"

    def payment_status_badge(self) -> str:
        return render_status_badge(self.status)
    payment_status_badge.short_description = "Trạng thái TT"
