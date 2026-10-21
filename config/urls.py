from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

admin.site.site_header = 'Портал — администрирование'
admin.site.site_title = 'Портал'
admin.site.index_title = 'Данные магазина'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('shop.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
