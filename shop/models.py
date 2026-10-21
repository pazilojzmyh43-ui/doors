from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def format_price(value):
    if value is None:
        return '0'
    return f'{int(Decimal(value)):,}'.replace(',', ' ')


class Category(models.Model):
    name = models.CharField('Название', max_length=120)
    name_key = models.CharField('Ключ названия', max_length=120, unique=True, editable=False)
    slug = models.SlugField('Адрес', max_length=140, unique=True)
    description = models.TextField('Описание', blank=True)
    position = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['position', 'name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.name = ' '.join((self.name or '').split())
        self.name_key = self.name.casefold()
        if not self.name:
            return
        clash = Category.objects.filter(name_key=self.name_key)
        if self.pk:
            clash = clash.exclude(pk=self.pk)
        if clash.exists():
            raise ValidationError({'name': 'Категория с таким названием уже существует.'})

    def save(self, *args, **kwargs):
        self.name = ' '.join((self.name or '').split())
        self.name_key = self.name.casefold()
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория',
    )
    name = models.CharField('Название', max_length=200)
    price = models.DecimalField('Цена, ₽', max_digits=10, decimal_places=2)
    description = models.TextField('Описание')
    material = models.CharField('Материал', max_length=160, blank=True)
    size = models.CharField('Размер', max_length=80, default='860×2050 мм')
    image = models.ImageField('Изображение', upload_to='products/', blank=True)
    in_stock = models.BooleanField('В наличии', default=True)
    created_at = models.DateTimeField('Добавлена', auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Дверь'
        verbose_name_plural = 'Двери'

    def __str__(self):
        return self.name

    @property
    def price_label(self):
        return format_price(self.price)


class News(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст')
    published_at = models.DateTimeField('Дата публикации', default=timezone.now)

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return self.title


class Profile(models.Model):
    ROLE_CLIENT = 'client'
    ROLE_MANAGER = 'manager'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_CLIENT, 'Клиент'),
        (ROLE_MANAGER, 'Менеджер'),
        (ROLE_ADMIN, 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    phone = models.CharField('Телефон', max_length=20, blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def total_price(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0'))

    @property
    def total_label(self):
        return format_price(self.total_price())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        unique_together = ('cart', 'product')
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'

    @property
    def line_total(self):
        return self.product.price * self.quantity

    @property
    def line_label(self):
        return format_price(self.line_total)


class Order(models.Model):
    STATUS_NEW = 'new'
    STATUS_WORK = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_WORK, 'В работе'),
        (STATUS_DONE, 'Выполнен'),
        (STATUS_CANCELLED, 'Отменён'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Клиент')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    total = models.DecimalField('Сумма', max_digits=12, decimal_places=2)
    address = models.TextField('Адрес')
    phone = models.CharField('Телефон', max_length=20)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ №{self.pk}'

    def client_can_change(self):
        return self.status in (self.STATUS_NEW, self.STATUS_WORK)

    @property
    def total_label(self):
        return format_price(self.total)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
    )
    product_name = models.CharField('Название', max_length=200)
    quantity = models.PositiveIntegerField('Количество')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    @property
    def line_total(self):
        return self.price * self.quantity

    @property
    def line_label(self):
        return format_price(self.line_total)

    @property
    def price_label(self):
        return format_price(self.price)


class WorkVideo(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание')
    place = models.CharField('Объект', max_length=200, blank=True)
    shot_at = models.DateField('Дата съёмки', null=True, blank=True)
    video = models.FileField('Видеофайл', upload_to='videos/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-shot_at', '-id']
        verbose_name = 'Видео работ'
        verbose_name_plural = 'Видео работ'

    def __str__(self):
        return self.title
