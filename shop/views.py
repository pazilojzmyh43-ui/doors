from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import (
    CategoryForm,
    CheckoutForm,
    LoginForm,
    ManagerCreateForm,
    NewsForm,
    OrderEditForm,
    ProductForm,
    RegisterForm,
    VideoForm,
)
from .models import (
    Cart,
    CartItem,
    Category,
    News,
    Order,
    OrderItem,
    Product,
    Profile,
    WorkVideo,
)


def home(request):
    categories = Category.objects.prefetch_related('products')
    return render(request, 'shop/home.html', {
        'news_list': News.objects.all()[:3],
        'categories': categories,
    })


def news_list(request):
    return render(request, 'shop/news_list.html', {'news_list': News.objects.all()})


def news_detail(request, pk):
    item = get_object_or_404(News, pk=pk)
    return render(request, 'shop/news_detail.html', {'item': item})


def contacts(request):
    return render(request, 'shop/contacts.html')


def catalog(request, slug=None):
    current = None
    categories = Category.objects.prefetch_related(
        Prefetch('products', queryset=Product.objects.order_by('name'))
    )
    if slug:
        current = get_object_or_404(Category, slug=slug)
        categories = categories.filter(pk=current.pk)
    return render(request, 'shop/catalog.html', {
        'categories': categories,
        'current': current,
        'all_categories': Category.objects.all(),
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
    related = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:4]
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related': related,
    })


def videos(request):
    return render(request, 'shop/videos.html', {'videos': WorkVideo.objects.all()})


def _client_cart(user):
    cart, _created = Cart.objects.get_or_create(user=user)
    return cart


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if not request.user.is_authenticated:
        messages.info(request, 'Чтобы положить дверь в корзину, войдите или зарегистрируйтесь как клиент.')
        nxt = reverse('product_detail', args=[pk])
        return redirect(f"{reverse('login')}?next={nxt}")
    profile = getattr(request.user, 'profile', None)
    if profile is None or profile.role != Profile.ROLE_CLIENT:
        messages.error(request, 'Корзина доступна только клиенту.')
        return redirect('product_detail', pk=pk)
    cart = _client_cart(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save(update_fields=['quantity'])
    messages.success(request, f'«{product.name}» добавлена в корзину.')
    return redirect('cart')


@role_required(Profile.ROLE_CLIENT)
def cart_view(request):
    cart = _client_cart(request.user)
    items = cart.items.select_related('product', 'product__category')
    return render(request, 'shop/cart.html', {'cart': cart, 'items': items})


@role_required(Profile.ROLE_CLIENT)
@require_POST
def cart_update(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    try:
        quantity = int(request.POST.get('quantity', '1'))
    except ValueError:
        quantity = 1
    if quantity <= 0:
        item.delete()
        messages.info(request, 'Позиция удалена из корзины.')
    else:
        item.quantity = min(quantity, 20)
        item.save(update_fields=['quantity'])
    return redirect('cart')


@role_required(Profile.ROLE_CLIENT)
@require_POST
def cart_remove(request, pk):
    item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
    item.delete()
    messages.info(request, 'Позиция удалена из корзины.')
    return redirect('cart')


@role_required(Profile.ROLE_CLIENT)
def checkout(request):
    cart = _client_cart(request.user)
    items = list(cart.items.select_related('product'))
    if not items:
        messages.error(request, 'Корзина пуста.')
        return redirect('cart')
    initial = {}
    profile = request.user.profile
    if profile.phone:
        initial['phone'] = profile.phone
    form = CheckoutForm(request.POST or None, initial=None if request.method == 'POST' else initial)
    if request.method == 'POST' and form.is_valid():
        total = sum((item.line_total for item in items), Decimal('0'))
        order = Order.objects.create(
            user=request.user,
            total=total,
            address=form.cleaned_data['address'],
            phone=form.cleaned_data['phone'],
            comment=form.cleaned_data['comment'],
        )
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                price=item.product.price,
            )
            for item in items
        ])
        cart.items.all().delete()
        if not profile.phone:
            profile.phone = form.cleaned_data['phone']
            profile.save(update_fields=['phone'])
        messages.success(request, f'Заказ №{order.pk} оформлен. Менеджер увидит его в списке заказов.')
        return redirect('my_orders')
    return render(request, 'shop/checkout.html', {'form': form, 'cart': cart, 'items': items})


@role_required(Profile.ROLE_CLIENT)
def my_orders(request):
    orders = request.user.orders.prefetch_related('items')
    return render(request, 'shop/my_orders.html', {'orders': orders})


@role_required(Profile.ROLE_CLIENT)
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if not order.client_can_change():
        messages.error(request, 'Этот заказ уже нельзя изменить.')
        return redirect('my_orders')
    form = OrderEditForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Заказ №{order.pk} обновлён.')
        return redirect('my_orders')
    return render(request, 'shop/order_form.html', {'form': form, 'order': order})


@role_required(Profile.ROLE_CLIENT)
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if not order.client_can_change():
        messages.error(request, 'Выполненный или отменённый заказ удалить нельзя.')
        return redirect('my_orders')
    if request.method == 'POST':
        number = order.pk
        order.delete()
        messages.success(request, f'Заказ №{number} удалён.')
        return redirect('my_orders')
    return render(request, 'shop/confirm_delete.html', {
        'title': f'Удалить заказ №{order.pk}?',
        'text': 'Заказ и его позиции будут удалены без восстановления.',
        'cancel_url': 'my_orders',
    })


@role_required(Profile.ROLE_MANAGER)
def manager_orders(request):
    orders = Order.objects.select_related('user').prefetch_related('items')
    return render(request, 'shop/manager_orders.html', {
        'orders': orders,
        'statuses': Order.STATUS_CHOICES,
    })


@role_required(Profile.ROLE_MANAGER)
@require_POST
def manager_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get('status', '')
    allowed = {code for code, _label in Order.STATUS_CHOICES}
    if status not in allowed:
        messages.error(request, 'Неизвестный статус.')
    else:
        order.status = status
        order.save(update_fields=['status'])
        messages.success(request, f'Статус заказа №{order.pk}: {order.get_status_display()}.')
    return redirect('manager_orders')


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        profile = user.profile
        profile.role = Profile.ROLE_CLIENT
        profile.phone = form.cleaned_data.get('phone', '')
        profile.save()
        login(request, user)
        messages.success(request, 'Регистрация выполнена. Вы вошли как клиент и можете оформлять заказы.')
        return redirect('catalog')
    return render(request, 'shop/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, f'Здравствуйте, {request.user.first_name or request.user.username}.')
        nxt = request.POST.get('next') or request.GET.get('next')
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)
        return redirect('home')
    return render(request, 'shop/login.html', {'form': form, 'next': request.GET.get('next', '')})


@require_POST
def user_logout(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('home')


def _form_page(request, form, title, back, multipart=False):
    return render(request, 'shop/panel/form.html', {
        'form': form,
        'title': title,
        'back': back,
        'multipart': multipart,
    })


@role_required(Profile.ROLE_ADMIN)
def panel(request):
    return render(request, 'shop/panel/dashboard.html', {
        'counts': {
            'categories': Category.objects.count(),
            'products': Product.objects.count(),
            'news': News.objects.count(),
            'videos': WorkVideo.objects.count(),
            'clients': Profile.objects.filter(role=Profile.ROLE_CLIENT).count(),
            'managers': Profile.objects.filter(role=Profile.ROLE_MANAGER).count(),
        }
    })


@role_required(Profile.ROLE_ADMIN)
def panel_categories(request):
    return render(request, 'shop/panel/categories.html', {
        'categories': Category.objects.all(),
    })


@role_required(Profile.ROLE_ADMIN)
def category_add(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        category = form.save()
        messages.success(request, f'Категория «{category.name}» добавлена.')
        return redirect('panel_categories')
    return _form_page(request, form, 'Новая категория', 'panel_categories')


@role_required(Profile.ROLE_ADMIN)
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Категория сохранена.')
        return redirect('panel_categories')
    return _form_page(request, form, f'Категория «{category.name}»', 'panel_categories')


@role_required(Profile.ROLE_ADMIN)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.error(
            request,
            'Нельзя удалить категорию, пока в ней есть двери. Сначала удалите или перенесите товары.',
        )
        return redirect('panel_categories')
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Категория «{name}» удалена.')
        return redirect('panel_categories')
    return render(request, 'shop/confirm_delete.html', {
        'title': f'Удалить категорию «{category.name}»?',
        'text': 'Категория пустая и будет удалена.',
        'cancel_url': 'panel_categories',
    })


@role_required(Profile.ROLE_ADMIN)
def panel_products(request):
    return render(request, 'shop/panel/products.html', {
        'products': Product.objects.select_related('category'),
    })


@role_required(Profile.ROLE_ADMIN)
def product_add(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f'«{product.name}» добавлена в каталог.')
        return redirect('panel_products')
    return _form_page(request, form, 'Новая дверь', 'panel_products', multipart=True)


@role_required(Profile.ROLE_ADMIN)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Карточка двери сохранена.')
        return redirect('panel_products')
    return _form_page(request, form, product.name, 'panel_products', multipart=True)


@role_required(Profile.ROLE_ADMIN)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'«{name}» удалена из каталога.')
        return redirect('panel_products')
    return render(request, 'shop/confirm_delete.html', {
        'title': f'Удалить «{product.name}»?',
        'text': 'Карточка исчезнет из каталога. В уже оформленных заказах останется название и цена.',
        'cancel_url': 'panel_products',
    })


@role_required(Profile.ROLE_ADMIN)
def panel_news(request):
    return render(request, 'shop/panel/news.html', {'news_list': News.objects.all()})


@role_required(Profile.ROLE_ADMIN)
def news_add(request):
    form = NewsForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Новость опубликована.')
        return redirect('panel_news')
    return _form_page(request, form, 'Новая новость', 'panel_news')


@role_required(Profile.ROLE_ADMIN)
def news_edit(request, pk):
    item = get_object_or_404(News, pk=pk)
    form = NewsForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Новость сохранена.')
        return redirect('panel_news')
    return _form_page(request, form, item.title, 'panel_news')


@role_required(Profile.ROLE_ADMIN)
def news_delete(request, pk):
    item = get_object_or_404(News, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Новость удалена.')
        return redirect('panel_news')
    return render(request, 'shop/confirm_delete.html', {
        'title': f'Удалить новость «{item.title}»?',
        'text': 'Текст пропадёт с главной и со страницы новостей.',
        'cancel_url': 'panel_news',
    })


@role_required(Profile.ROLE_ADMIN)
def panel_videos(request):
    return render(request, 'shop/panel/videos.html', {'videos': WorkVideo.objects.all()})


@role_required(Profile.ROLE_ADMIN)
def video_add(request):
    form = VideoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Видео добавлено на страницу работ.')
        return redirect('panel_videos')
    return _form_page(request, form, 'Новое видео', 'panel_videos', multipart=True)


@role_required(Profile.ROLE_ADMIN)
def video_edit(request, pk):
    item = get_object_or_404(WorkVideo, pk=pk)
    form = VideoForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Видео сохранено.')
        return redirect('panel_videos')
    return _form_page(request, form, item.title, 'panel_videos', multipart=True)


@role_required(Profile.ROLE_ADMIN)
def video_delete(request, pk):
    item = get_object_or_404(WorkVideo, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Видео удалено.')
        return redirect('panel_videos')
    return render(request, 'shop/confirm_delete.html', {
        'title': f'Удалить видео «{item.title}»?',
        'text': 'Ролик пропадёт со страницы «Наши работы».',
        'cancel_url': 'panel_videos',
    })


@role_required(Profile.ROLE_ADMIN)
def panel_users(request):
    form = ManagerCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        profile = user.profile
        profile.role = Profile.ROLE_MANAGER
        profile.phone = form.cleaned_data.get('phone', '')
        profile.save()
        messages.success(request, f'Менеджер {user.username} зарегистрирован.')
        return redirect('panel_users')
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'shop/panel/users.html', {'form': form, 'users': users})


@role_required(Profile.ROLE_ADMIN)
def user_delete(request, pk):
    user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    profile = getattr(user, 'profile', None)
    if user == request.user or profile is None or profile.role == Profile.ROLE_ADMIN:
        messages.error(request, 'Администратора удалить нельзя.')
        return redirect('panel_users')
    if profile.role not in (Profile.ROLE_CLIENT, Profile.ROLE_MANAGER):
        messages.error(request, 'Можно удалять только клиентов и менеджеров.')
        return redirect('panel_users')
    if request.method == 'POST':
        username = user.username
        role = profile.get_role_display().lower()
        user.delete()
        messages.success(request, f'{role.capitalize()} {username} удалён.')
        return redirect('panel_users')
    return render(request, 'shop/confirm_delete.html', {
        'title': f'Удалить {profile.get_role_display().lower()}а {user.username}?',
        'text': 'Учётная запись и связанные с ней заказы будут удалены.',
        'cancel_url': 'panel_users',
    })
