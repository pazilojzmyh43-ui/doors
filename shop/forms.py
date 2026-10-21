from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Category, News, Order, Product, WorkVideo

RU = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
    'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def slugify_ru(value):
    chars = []
    for ch in (value or '').strip().lower():
        if ch in RU:
            chars.append(RU[ch])
        elif ch.isascii() and ch.isalnum():
            chars.append(ch.lower())
        else:
            chars.append('-')
    slug = ''.join(chars)
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-') or 'category'


def style_fields(form):
    for field in form.fields.values():
        widget = field.widget
        if widget.__class__.__name__ == 'CheckboxInput':
            widget.attrs.setdefault('class', 'check')
            continue
        css = widget.attrs.get('class', '')
        widget.attrs['class'] = (css + ' field').strip()


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_name(self):
        name = ' '.join((self.cleaned_data.get('name') or '').split())
        if not name:
            raise forms.ValidationError('Укажите название категории.')
        clash = Category.objects.filter(name_key=name.casefold())
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError('Категория с таким названием уже существует.')
        return name

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.name = self.cleaned_data['name']
        obj.name_key = obj.name.casefold()
        if not obj.slug:
            base = slugify_ru(obj.name)
            slug = base
            number = 2
            while Category.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f'{base}-{number}'
                number += 1
            obj.slug = slug
        if commit:
            obj.save()
        return obj


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'material', 'size', 'description', 'image', 'in_stock']
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Цена должна быть больше нуля.')
        return price


class NewsForm(forms.ModelForm):
    published_at = forms.DateTimeField(
        label='Дата публикации',
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'],
    )

    class Meta:
        model = News
        fields = ['title', 'text', 'published_at']
        widgets = {'text': forms.Textarea(attrs={'rows': 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.published_at:
            local = timezone.localtime(self.instance.published_at)
            self.initial['published_at'] = local.strftime('%Y-%m-%dT%H:%M')
        style_fields(self)

    def clean_published_at(self):
        return self.cleaned_data.get('published_at') or timezone.now()


class VideoForm(forms.ModelForm):
    class Meta:
        model = WorkVideo
        fields = ['title', 'place', 'shot_at', 'description', 'video']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'shot_at': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['video'].required = False
        style_fields(self)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label='Электронная почта')
    first_name = forms.CharField(label='Имя', max_length=150)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    phone = forms.CharField(label='Телефон', max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        style_fields(self)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с такой почтой уже зарегистрирован.')
        return email


class ManagerCreateForm(UserCreationForm):
    email = forms.EmailField(label='Электронная почта')
    first_name = forms.CharField(label='Имя', max_length=150)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    phone = forms.CharField(label='Телефон', max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин менеджера'
        style_fields(self)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с такой почтой уже зарегистрирован.')
        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Логин'
        self.fields['password'].label = 'Пароль'
        style_fields(self)


class CheckoutForm(forms.Form):
    address = forms.CharField(
        label='Адрес доставки и монтажа',
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    phone = forms.CharField(label='Телефон', max_length=20)
    comment = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if len(phone) < 6:
            raise forms.ValidationError('Укажите телефон полностью.')
        return phone


class OrderEditForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['address', 'phone', 'comment']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if len(phone) < 6:
            raise forms.ValidationError('Укажите телефон полностью.')
        return phone
