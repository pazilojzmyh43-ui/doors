from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import Category, News, Order, OrderItem, Product, Profile, WorkVideo

BASE = Path(__file__).resolve().parents[3]
PRODUCTS_DIR = BASE / 'seed_media' / 'products'
VIDEOS_DIR = BASE / 'seed_media' / 'videos'


class Command(BaseCommand):
    help = 'Заполняет базу учебными категориями, дверями, новостями, видео и пользователями.'

    def handle(self, *args, **options):
        self._users()
        categories = self._categories()
        self._products(categories)
        self._news()
        self._videos()
        self._sample_order()
        self.stdout.write(self.style.SUCCESS('База «Портал» заполнена.'))

    def _users(self):
        accounts = [
            ('admin', 'AdminPortal!26', 'Администратор', 'Портал', 'admin@portal-doors.ru', Profile.ROLE_ADMIN, True),
            ('manager', 'ManagerPortal!26', 'Мария', 'Соколова', 'manager@portal-doors.ru', Profile.ROLE_MANAGER, False),
            ('client', 'ClientPortal!26', 'Иван', 'Петров', 'client@portal-doors.ru', Profile.ROLE_CLIENT, False),
        ]
        for username, password, first, last, email, role, is_admin in accounts:
            user, _created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': first, 'last_name': last},
            )
            user.email = email
            user.first_name = first
            user.last_name = last
            user.is_staff = is_admin
            user.is_superuser = is_admin
            user.set_password(password)
            user.save()
            profile = user.profile
            profile.role = role
            profile.save(update_fields=['role'])

    def _categories(self):
        data = [
            ('Входные', 'vhodnye', 1, 'Квартирные входные двери: сталь, панели МДФ, замки и уплотнители.'),
            ('Межкомнатные', 'mezhkomnatnye', 2, 'Двери между комнатами: эмаль, шпон, скрытый монтаж, стекло и раздвижные полотна.'),
            ('Для частных домов', 'dlya-chastnyh-domov', 3, 'Входные двери для загородных домов: терморазрыв, двустворчатые полотна, ковка и усиленные конструкции.'),
        ]
        result = {}
        for name, slug, position, description in data:
            category, _created = Category.objects.get_or_create(
                name=name,
                defaults={'slug': slug, 'position': position, 'description': description},
            )
            category.slug = slug
            category.position = position
            category.description = description
            category.save()
            result[name] = category
        return result

    def _products(self, categories):
        rows = [
            ('Входные', 'Норд', '54800', 'Сталь с терморазрывом', '960×2050 мм', '01-nord.jpg', True,
             'Глухая стальная дверь с узкой стеклянной вставкой. Два контура уплотнения и замок с ночной задвижкой.'),
            ('Входные', 'Графит Зеркало', '61200', 'Сталь и тонированное стекло', '960×2050 мм', '02-graphite.jpg', True,
             'Тёмное полотно с зеркальной вставкой со стороны квартиры. Удобно в узкой прихожей.'),
            ('Входные', 'Орех Классика', '47600', 'МДФ, шпон ореха', '860×2050 мм', '03-walnut.jpg', True,
             'Классические филёнки тёплого ореха и латунная ручка. Заявленная шумоизоляция — 32 дБ.'),
            ('Входные', 'Лофт Чёрный', '58900', 'Сталь, матовая эмаль', '960×2050 мм', '04-loft.jpg', True,
             'Чёрная дверь с горизонтальным членением и длинной тягой. Для лофта и современных холлов.'),
            ('Входные', 'Сканди Белая', '45300', 'Сталь, тёплая эмаль', '860×2050 мм', '05-scandi.jpg', True,
             'Светлая входная дверь с дубовой ручкой. Мягко смотрится в светлой отделке подъезда.'),
            ('Межкомнатные', 'Эмаль Белая', '12900', 'МДФ под эмалью', '800×2000 мм', '06-enamel.jpg', True,
             'Классическое белое полотно. Тихий притвор, короб и наличник можно заказать вместе.'),
            ('Межкомнатные', 'Дуб Стекло', '18400', 'Шпон дуба, стекло', '800×2000 мм', '07-oak.jpg', True,
             'Натуральный дуб и матовая вставка. Свет проходит, обзор из коридора закрыт.'),
            ('Межкомнатные', 'Скрытая', '21400', 'Грунт под покраску', '800×2100 мм', '08-hidden.jpg', True,
             'Полотно без наличника ставится в одной плоскости со стеной. Алюминиевая кромка.'),
            ('Межкомнатные', 'Ясень Купе', '24600', 'Массив ясеня', '800×2100 мм', '09-ash.jpg', True,
             'Раздвижное полотно на амбарном подвесе. Экономит место у кладовой и гардеробной.'),
            ('Межкомнатные', 'Сатин', '19800', 'Стекло сатин, алюминий', '800×2100 мм', '10-satin.jpg', False,
             'Цельностеклянное матовое полотно в тонкой раме. Делаем под размер проёма, срок около трёх недель.'),
            ('Для частных домов', 'Усадьба', '168000', 'Массив дуба', '1400×2300 мм', '11-estate.jpg', True,
             'Двустворчатая дубовая дверь с резьбой. Для парадного входа загородного дома.'),
            ('Для частных домов', 'Термо Ковка', '124000', 'Сталь, ковка, стеклопакет', '980×2100 мм', '12-thermo.jpg', True,
             'Тёплая дверь с кованой накладкой и стеклопакетом. Терморазрыв рассчитан на зимний тамбур.'),
            ('Для частных домов', 'Альпийская', '98000', 'Лиственница', '900×2100 мм', '13-alps.jpg', True,
             'Массив лиственницы, накладные петли и засов. Хорошо стоит на влажном фасаде.'),
            ('Для частных домов', 'Витраж', '112000', 'Дерево, декоративное стекло', '980×2100 мм', '14-stained.jpg', True,
             'Зелёное полотно с геометрическим остеклением. Даёт свет в тамбур и не раскрывает дом.'),
            ('Для частных домов', 'Крепость', '143000', 'Сталь 2 мм', '980×2100 мм', '15-fortress.jpg', True,
             'Усиленная дверь с тремя петлями и многозапорным замком. Для домов без постоянного проживания.'),
        ]
        for category_name, name, price, material, size, filename, in_stock, description in rows:
            product, _created = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': categories[category_name],
                    'price': Decimal(price),
                    'material': material,
                    'size': size,
                    'in_stock': in_stock,
                    'description': description,
                },
            )
            product.category = categories[category_name]
            product.price = Decimal(price)
            product.material = material
            product.size = size
            product.in_stock = in_stock
            product.description = description
            product.save()
            path = PRODUCTS_DIR / filename
            if path.exists() and not product.image:
                with path.open('rb') as handle:
                    product.image.save(filename, File(handle), save=True)

    def _news(self):
        today = timezone.now()
        rows = [
            ('Открыли шоурум на Металлистов', 2,
             'На улице Металлистов, 12 можно посмотреть входные и межкомнатные полотна вживую. '
             'Замер по Пскову в будни бесплатный, если заказ оформляется у нас.'),
            ('Термодвери для частных домов — зимняя партия', 6,
             'В категорию «Для частных домов» пришли модели с терморазрывом: «Термо Ковка» и «Крепость». '
             'Монтаж до устойчивого снега записываем на ближайшие недели.'),
            ('Эмаль «Белая»: тихий притвор в стандартный проём', 12,
             'На межкомнатных эмалях обновили фурнитуру. Магнитный замок и скрытые петли входят в цену полотна шириной 800 мм.'),
            ('Как ставим двери в уже жилой квартире', 20,
             'Закрываем пол и выносим пыль пылесосом. Средний монтаж входной двери занимает день, межкомнатной — около двух часов.'),
            ('Паспорта на стальные полотна', 30,
             '«Норд», «Лофт Чёрный» и «Крепость» идут с паспортом изделия. Гарантия на полотно — 3 года, на фурнитуру — 1 год.'),
        ]
        for title, days, text in rows:
            News.objects.update_or_create(
                title=title,
                defaults={'text': text, 'published_at': today - timedelta(days=days)},
            )

    def _videos(self):
        rows = [
            ('Монтаж «Норд» в кирпичный дом', 'Печоры, частный дом', date(2026, 9, 12), 'install.mp4',
             'Поставили тёмную входную дверь в кирпичный фасад. На ролике — установка коробки и навеска полотна.'),
            ('Межкомнатные «Эмаль Белая» в квартире', 'Псков, Рижский проспект', date(2026, 8, 3), 'interior.mp4',
             'Белые эмали после монтажа: полотно открывается в светлую комнату без щелей по притвору.'),
            ('«Усадьба» на загородном участке', 'Пушкиногорский район', date(2026, 7, 18), 'estate.mp4',
             'Двустворчатая дубовая дверь в день сдачи дома у сосен.'),
        ]
        for title, place, shot_at, filename, description in rows:
            video, _created = WorkVideo.objects.get_or_create(
                title=title,
                defaults={'place': place, 'shot_at': shot_at, 'description': description, 'video': ''},
            )
            video.place = place
            video.shot_at = shot_at
            video.description = description
            path = VIDEOS_DIR / filename
            if path.exists() and not video.video:
                with path.open('rb') as handle:
                    video.video.save(filename, File(handle), save=False)
            video.save()

    def _sample_order(self):
        client = User.objects.get(username='client')
        if Order.objects.filter(user=client).exists():
            return
        nord = Product.objects.get(name='Норд')
        enamel = Product.objects.get(name='Эмаль Белая')
        order = Order.objects.create(
            user=client,
            status=Order.STATUS_WORK,
            address='г. Псков, Рижский проспект, д. 18, кв. 7',
            phone='+7 (911) 200-15-15',
            comment='Домофон 18, замер уже сделан.',
            total=nord.price + enamel.price * 2,
        )
        OrderItem.objects.create(order=order, product=nord, product_name=nord.name, quantity=1, price=nord.price)
        OrderItem.objects.create(order=order, product=enamel, product_name=enamel.name, quantity=2, price=enamel.price)
