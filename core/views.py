"""
views.py — Core app
Giao diện frontend cho website bán vé du lịch
"""

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import Booking, Customer, TourDeparture, TourProduct


# ── Helpers ────────────────────────────────────────────────────────────────

def get_or_create_customer(user):
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={'membership_tier': 'STANDARD', 'total_spent': Decimal('0')},
    )
    return customer


# ── Public pages ───────────────────────────────────────────────────────────

def home(request):
    """Trang chủ — hero + tour nổi bật + thống kê."""
    featured_products = TourProduct.objects.filter(
        status='ACTIVE'
    ).select_related('tour_page', 'tour_page__category', 'tour_page__destination')[:6]

    upcoming_departures = TourDeparture.objects.filter(
        status='OPEN',
        available_seats__gt=0,
        start_date__gte=timezone.now().date(),
    ).select_related(
        'tour_product', 'tour_product__tour_page'
    ).order_by('start_date')[:8]

    stats = {
        'total_tours':     TourProduct.objects.filter(status='ACTIVE').count(),
        'total_bookings':  Booking.objects.filter(status__in=['PAID', 'COMPLETED']).count(),
        'total_customers': Customer.objects.count(),
        'total_revenue':   Booking.objects.filter(
            status__in=['PAID', 'COMPLETED']
        ).aggregate(t=Sum('final_amount'))['t'] or 0,
    }

    return render(request, 'core/home.html', {
        'featured_products':  featured_products,
        'upcoming_departures': upcoming_departures,
        'stats': stats,
    })


def tour_list(request):
    """Danh sách tất cả tour."""
    products = TourProduct.objects.filter(
        status='ACTIVE'
    ).select_related(
        'tour_page', 'tour_page__category', 'tour_page__destination'
    ).annotate(
        departure_count=Count('departures', filter=__import__(
            'django.db.models', fromlist=['Q']
        ).Q(departures__status='OPEN')),
    ).order_by('base_price')

    # Filter
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if category:
        products = products.filter(tour_page__category__slug=category)
    if min_price:
        products = products.filter(base_price__gte=min_price)
    if max_price:
        products = products.filter(base_price__lte=max_price)

    from .models import Category
    categories = Category.objects.all()

    return render(request, 'core/tour_list.html', {
        'products':   products,
        'categories': categories,
        'current_category': category,
    })


def tour_detail(request, slug):
    """Chi tiết 1 tour + danh sách lịch khởi hành."""
    from wagtail.models import Page
    page = get_object_or_404(Page, slug=slug)

    try:
        product = page.tourpage.product
    except Exception:
        return redirect('tour_list')

    departures = TourDeparture.objects.filter(
        tour_product=product,
        start_date__gte=timezone.now().date(),
    ).order_by('start_date')

    return render(request, 'core/tour_detail.html', {
        'page':       page,
        'product':    product,
        'departures': departures,
    })


# ── Booking ────────────────────────────────────────────────────────────────

@login_required
def booking_create(request, departure_id):
    """Form đặt tour."""
    departure = get_object_or_404(TourDeparture, pk=departure_id, status='OPEN')
    customer  = get_or_create_customer(request.user)

    if request.method == 'POST':
        try:
            num_adults   = int(request.POST.get('num_adults', 1))
            num_children = int(request.POST.get('num_children', 0))
            special_req  = request.POST.get('special_request', '')

            num_pax = num_adults + num_children
            if num_pax > departure.available_seats:
                messages.error(request, f'Chỉ còn {departure.available_seats} chỗ trống!')
                return redirect('booking_create', departure_id=departure_id)

            price       = departure.effective_price
            child_price = departure.tour_product.child_price or price * Decimal('0.7')
            total       = price * num_adults + child_price * num_children

            import random, string
            code = 'BK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            booking = Booking.objects.create(
                customer=customer,
                departure=departure,
                booking_code=code,
                num_adults=num_adults,
                num_children=num_children,
                total_amount=total,
                discount_amount=Decimal('0'),
                final_amount=total,
                status='PENDING',
                special_request=special_req,
            )

            # Giảm số ghế
            departure.available_seats -= num_pax
            if departure.available_seats <= 0:
                departure.status = 'FULL'
            departure.save(update_fields=['available_seats', 'status'])

            messages.success(request, f'Đặt tour thành công! Mã đặt: {code}')
            return redirect('booking_success', booking_code=code)

        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra: {str(e)}')

    return render(request, 'core/booking_form.html', {
        'departure': departure,
        'customer':  customer,
    })


@login_required
def booking_success(request, booking_code):
    booking = get_object_or_404(Booking, booking_code=booking_code)
    return render(request, 'core/booking_success.html', {'booking': booking})


@login_required
def my_bookings(request):
    customer = get_or_create_customer(request.user)
    bookings = Booking.objects.filter(
        customer=customer
    ).select_related(
        'departure', 'departure__tour_product', 'departure__tour_product__tour_page'
    ).order_by('-booking_date')
    return render(request, 'core/my_bookings.html', {
        'bookings': bookings,
        'customer': customer,
    })


# ── Auth ────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.method == 'POST':
        username  = request.POST.get('username')
        email     = request.POST.get('email')
        password  = request.POST.get('password')
        full_name = request.POST.get('full_name', '')
        phone     = request.POST.get('phone', '')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã tồn tại!')
            return render(request, 'core/register.html')

        parts = full_name.strip().split(' ', 1)
        first = parts[0] if parts else ''
        last  = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=username, email=email,
            password=password,
            first_name=first, last_name=last,
        )
        Customer.objects.create(
            user=user,
            phone=phone,
            membership_tier='STANDARD',
            total_spent=Decimal('0'),
        )
        login(request, user)
        messages.success(request, f'Chào mừng {full_name}! Đăng ký thành công.')
        return redirect('home')

    return render(request, 'core/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.POST.get('next') or 'home'
            return redirect(next_url)
        messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu!')
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


# ── API endpoints ──────────────────────────────────────────────────────────

@require_GET
def api_tours(request):
    products = TourProduct.objects.filter(status='ACTIVE').select_related('tour_page')
    data = [
        {
            'id':    p.pk,
            'name':  p.tour_page.title,
            'sku':   p.sku_code,
            'price': float(p.base_price),
            'days':  p.tour_page.duration_days,
        }
        for p in products
    ]
    return JsonResponse({'tours': data, 'count': len(data)})


@require_GET
def api_stats(request):
    stats = {
        'total_revenue': float(
            Booking.objects.filter(
                status__in=['PAID', 'COMPLETED']
            ).aggregate(t=Sum('final_amount'))['t'] or 0
        ),
        'total_bookings':  Booking.objects.count(),
        'paid_bookings':   Booking.objects.filter(status__in=['PAID', 'COMPLETED']).count(),
        'total_customers': Customer.objects.count(),
        'vip_customers':   Customer.objects.filter(membership_tier__in=['VIP', 'DIAMOND']).count(),
        'open_departures': TourDeparture.objects.filter(status='OPEN').count(),
        'revenue_by_month': list(
            Booking.objects.filter(status__in=['PAID', 'COMPLETED'])
            .extra(select={'month': "DATE_TRUNC('month', booking_date)"})
            .values('month')
            .annotate(total=Sum('final_amount'), count=Count('id'))
            .order_by('month')
            .values('month', 'total', 'count')
        ),
    }
    return JsonResponse(stats, default=str)
