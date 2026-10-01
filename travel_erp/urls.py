from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from core import views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('admin/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),

    # Frontend pages
    path('', views.home, name='home'),
    path('tours/', views.tour_list, name='tour_list'),
    path('tours/<slug:slug>/', views.tour_detail, name='tour_detail'),
    path('booking/<int:departure_id>/', views.booking_create, name='booking_create'),
    path('booking/success/<str:booking_code>/', views.booking_success, name='booking_success'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # API
    path('api/tours/', views.api_tours, name='api_tours'),
    path('api/stats/', views.api_stats, name='api_stats'),

    path('', include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
