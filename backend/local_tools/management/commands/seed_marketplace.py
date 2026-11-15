"""Add fictional marketplace content to local SQLite, without admin accounts."""
import json
from pathlib import Path
import random
import secrets
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.applications.models import OrderApplication
from apps.applications.services import ApplicationService
from apps.categories.models import Category
from apps.categories.services import CategoryService
from apps.chat.models import Conversation, Message
from apps.chat.services import ChatService
from apps.favorites.models import FavoriteOrder, FavoriteWorker
from apps.invitations.models import OrderInvitation
from apps.invitations.services import InvitationService
from apps.notifications.models import Notification
from apps.orders.models import OrderStatus, ServiceOrder
from apps.orders.services import OrderService
from apps.profiles.models import EmployerProfile, WorkerPortfolioItem, WorkerProfile
from apps.reviews.models import Review
from apps.reviews.services import ReviewService


CATEGORY_GROUPS = [
    ("qurilish", "Qurilish va ta'mirlash", "Строительство и ремонт", "Construction & Repairs", [
        ("santexnika", "Santexnika", "Сантехника", "Plumbing", "Hammom quvurlarini almashtirish"),
        ("elektr", "Elektr ishlari", "Электромонтаж", "Electrical Work", "Xonadon elektr tarmog'ini yangilash"),
        ("boyoq", "Bo'yoqchilik", "Малярные работы", "Painting", "Xonalar devorini bo'yash"),
    ]),
    ("maishiy", "Uy va maishiy xizmatlar", "Бытовые услуги", "Home Services", [
        ("klining", "Tozalash", "Уборка", "Cleaning", "Ta'mirdan keyin xonadonni tozalash"),
        ("mebel", "Mebel yig'ish", "Сборка мебели", "Furniture Assembly", "Oshxona mebellarini yig'ish"),
        ("konditsioner", "Konditsioner xizmati", "Кондиционеры", "Air Conditioning", "Konditsionerni o'rnatish va sozlash"),
    ]),
    ("raqamli", "IT va dizayn", "IT и дизайн", "IT & Design", [
        ("web", "Veb-dasturlash", "Веб-разработка", "Web Development", "Kompaniya uchun veb-sayt yaratish"),
        ("dizayn", "Grafik dizayn", "Графический дизайн", "Graphic Design", "Brend logotipi va tashrif qog'ozi dizayni"),
        ("smm", "SMM va marketing", "SMM и маркетинг", "SMM & Marketing", "Biznes uchun ijtimoiy tarmoq sahifasini yuritish"),
    ]),
    ("transport", "Transport xizmatlari", "Транспортные услуги", "Transport Services", [
        ("yuk", "Yuk tashish", "Грузоперевозки", "Cargo Transport", "Ko'chish uchun yuk tashish xizmati"),
        ("avto", "Avtomobil ta'miri", "Ремонт автомобилей", "Car Repairs", "Avtomobilni diagnostika qilish"),
        ("kuryer", "Yetkazib berish", "Доставка", "Delivery", "Shahar bo'ylab mahsulot yetkazib berish"),
    ]),
    ("talim", "Ta'lim va tarjima", "Обучение и переводы", "Education & Translation", [
        ("ingliz", "Ingliz tili", "Английский язык", "English Lessons", "Ingliz tilidan individual darslar"),
        ("matematika", "Matematika", "Математика", "Mathematics", "Matematikadan imtihonga tayyorlash"),
        ("tarjima", "Tarjima xizmati", "Переводы", "Translation", "Hujjatlarni o'zbek va rus tillariga tarjima qilish"),
    ]),
    ("tadbir", "Tadbir va ijod", "Мероприятия и творчество", "Events & Creative Services", [
        ("foto", "Fotosurat", "Фотосъёмка", "Photography", "Oilaviy tadbirni suratga olish"),
        ("video", "Video montaj", "Видеомонтаж", "Video Editing", "Qisqa reklama videosini montaj qilish"),
        ("dekor", "Tadbir bezagi", "Оформление мероприятий", "Event Decoration", "Tadbir uchun zalni bezash"),
    ]),
]
FIRST_NAMES = ["Azizbek", "Jasur", "Sardor", "Dilshod", "Bobur", "Kamol", "Alisher", "Umid", "Otabek", "Farrux", "Madina", "Nodira", "Malika", "Dildora", "Sevara", "Shahnoza", "Gulnoza", "Zilola"]
LAST_NAMES = ["Karimov", "Rahimov", "Tursunov", "Aliyev", "Sobirov", "Nazarov", "Yusupov", "Ergashev", "Ismoilov", "Akbarov"]
LOCATIONS = [("Toshkent", "Chilonzor"), ("Toshkent", "Yunusobod"), ("Samarqand", "Registon"), ("Buxoro", "Markaz"), ("Farg'ona", "Markaz"), ("Andijon", "Markaz"), ("Namangan", "Davlatobod"), ("Nukus", "Markaz")]


def assert_local_target():
    config = settings.DATABASES["default"]
    if (getattr(settings, "IS_PRODUCTION", False) or not settings.DEBUG
            or not getattr(settings, "LOCAL_DEVELOPMENT", False)
            or config["ENGINE"] != "django.db.backends.sqlite3"):
        raise CommandError("Seeding is restricted to explicit local SQLite development.")
    name = str(config["NAME"])
    memory = name == ":memory:" or name.startswith("file:memorydb_")
    local_file = (Path(settings.BASE_DIR) / ".local" / "ishchi.sqlite3").resolve()
    if not memory and Path(name).resolve() != local_file:
        raise CommandError("Only .local/ishchi.sqlite3 or an in-memory test database may be seeded.")


def totals():
    return {"users": User.objects.count(), "categories": Category.objects.count(),
            "orders": ServiceOrder.objects.count(), "applications": OrderApplication.objects.count(),
            "invitations": OrderInvitation.objects.count(), "conversations": Conversation.objects.count(),
            "messages": Message.objects.count(), "reviews": Review.objects.count(),
            "notifications": Notification.objects.count(), "portfolios": WorkerPortfolioItem.objects.count(),
            "favorites": FavoriteWorker.objects.count() + FavoriteOrder.objects.count()}


class Command(BaseCommand):
    help = "Append random local marketplace data; never creates admins or replaces existing records."

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=30)
        parser.add_argument("--employers", type=int, default=10)
        parser.add_argument("--orders", type=int, default=60)

    def handle(self, *args, **options):
        # Check before any database query or transaction is opened.
        assert_local_target()
        workers, employers, orders = (options[k] for k in ("workers", "employers", "orders"))
        if not (4 <= workers <= 200 and 1 <= employers <= 100 and 1 <= orders <= 500):
            raise CommandError("Use 4..200 workers, 1..100 employers and 1..500 orders.")
        result = self.populate(workers, employers, orders)
        self.stdout.write(json.dumps(result, ensure_ascii=False))

    @transaction.atomic
    def populate(self, worker_count, employer_count, order_count):
        rng = random.Random(secrets.randbits(64))
        batch = uuid4().hex[:12]
        before = totals()
        admin_filter = Q(role=UserRole.ADMIN) | Q(is_staff=True) | Q(is_superuser=True)
        admin_before = set(User.objects.filter(admin_filter).values_list("pk", flat=True))
        categories = []
        for group_slug, uz, ru, en, children in CATEGORY_GROUPS:
            parent, _ = Category.objects.get_or_create(slug=f"local-{group_slug}", defaults={
                "name": uz, "name_uz": uz, "name_ru": ru, "name_en": en,
                "description": "Mahalliy sinov uchun xizmatlar kategoriyasi.", "is_active": True,
            })
            if not parent.is_active:
                continue
            for slug, child_uz, child_ru, child_en, title in children:
                category, _ = Category.objects.get_or_create(slug=f"local-{group_slug}-{slug}", defaults={
                    "parent": parent, "name": child_uz, "name_uz": child_uz,
                    "name_ru": child_ru, "name_en": child_en, "is_active": True,
                    "description": "Mahalliy sinov ma'lumoti: " + child_uz,
                })
                if category.is_active:
                    categories.append((category, title))
        if not categories:
            raise CommandError("No active fixture categories are available; existing categories were not changed.")

        def make_user(role, index):
            while True:
                phone = f"+99899{rng.randrange(10_000_000):07d}"
                if not User.objects.filter(phone_number=phone).exists():
                    break
            return User.objects.create_user(phone_number=phone, password=None,
                full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                email=f"fixture.{batch}.{index}@example.invalid", role=role,
                is_staff=False, is_superuser=False, is_active=True, is_phone_verified=False)

        workers = []
        for index in range(worker_count):
            user = make_user(UserRole.WORKER, index)
            city, district = rng.choice(LOCATIONS)
            assigned = rng.sample(categories, rng.randint(1, min(3, len(categories))))
            worker = WorkerProfile.objects.create(user=user, full_name=user.full_name,
                phone_number=user.phone_number, location=city, district=district,
                bio="Mahalliy sinov profili. " + assigned[0][0].name + " bo'yicha xizmatlar.",
                skills=[item[0].name for item in assigned], experience_years=rng.randint(1, 12),
                hourly_rate=Decimal(rng.randrange(5, 26) * 10000), pricing_type="HOURLY",
                is_available=True)
            CategoryService.update_worker_categories(worker, [{"category_id": category.pk,
                "is_primary": i == 0, "experience_years": worker.experience_years}
                for i, (category, _) in enumerate(assigned)])
            WorkerPortfolioItem.objects.create(worker=worker, title=assigned[0][0].name + " loyihasi",
                description="Mahalliy sinov uchun bajarilgan ish tavsifi.", completed_year=timezone.localdate().year)
            workers.append(worker)

        employers = []
        for index in range(employer_count):
            user = make_user(UserRole.EMPLOYER, worker_count + index)
            city, district = rng.choice(LOCATIONS)
            employer = EmployerProfile.objects.create(user=user, full_name=user.full_name,
                phone_number=user.phone_number, email=user.email, location=city, district=district,
                employer_type="COMPANY" if index % 3 == 0 else "INDIVIDUAL",
                company_name=f"{rng.choice(['Baraka', 'Ravnaq', 'Ziyo', 'Nuron'])} Servis {index + 1}" if index % 3 == 0 else "",
                bio="Mahalliy sinov uchun buyurtmachi profili.")
            employers.append(employer)

        for index in range(order_count):
            employer = employers[index % len(employers)]
            category, title = categories[index % len(categories)]
            stage = index % 10
            capacity = 2 if stage in (1, 3) else 3 if stage == 6 else 1
            order = OrderService.create_order(employer, {
                "category": category, "title": f"{title} — {employer.location}, {index + 1}",
                "description": f"{title}. Ish hajmi va muddatini kelishib olamiz. Mahalliy sinov uchun yaratilgan e'lon.",
                "budget": Decimal(rng.randrange(10, 151) * 50000), "budget_type": "FIXED",
                "location": employer.location, "district": employer.district,
                "work_type": "REMOTE" if category.parent.slug in ("local-raqamli", "local-talim") else "ONSITE",
                "deadline": timezone.now() + timedelta(days=rng.randint(3, 30)),
                "capacity": capacity, "status": OrderStatus.DRAFT if stage == 4 else OrderStatus.PUBLISHED,
            })
            if stage == 4:
                continue
            participants = rng.sample(workers, 4)
            applications = [ApplicationService.submit_application(worker, order.pk,
                "Ishni belgilangan muddatda bajarishga tayyorman.", order.budget) for worker in participants[:3]]
            invited = participants[0] if stage == 3 else participants[3]
            invitation = InvitationService.send_invitation(employer, order.pk, invited.pk,
                message="Ushbu ish bo'yicha hamkorlik qilishni taklif qilamiz.", proposed_budget=order.budget)
            if stage in (0, 1, 2, 3, 6):
                if stage == 3:
                    InvitationService.accept_invitation(invitation.pk, participants[0])
                else:
                    ApplicationService.accept_application(applications[0].pk, employer)
                if capacity == 2:
                    ApplicationService.accept_application(applications[1].pk, employer)
            if stage == 5:
                OrderService.pause_order(order.pk, employer)
            conversation, _ = ChatService.get_or_create_conversation(participants[0].user, order.pk)
            ChatService.send_message(conversation, employer.user, "Assalomu alaykum! Ish tafsilotlarini kelishib olamizmi?")
            ChatService.send_message(conversation, participants[0].user, "Va alaykum assalom! Qulay vaqt va ish hajmini yozib yuboring.")
            if stage in (0, 1):
                order = OrderService.complete_order(order.pk, employer)
                for worker in order.get_hired_workers():
                    ReviewService.create_review(employer.user, order.pk, rng.randint(4, 5),
                        "Ish sifatli va o'z vaqtida bajarildi.", reviewee_id=worker.user_id)
                    ReviewService.create_review(worker.user, order.pk, rng.randint(4, 5), "Hamkorlik uchun rahmat.")
            FavoriteWorker.objects.get_or_create(user=employer.user, worker=participants[0])
            FavoriteOrder.objects.get_or_create(user=participants[3].user, order=order)

        if set(User.objects.filter(admin_filter).values_list("pk", flat=True)) != admin_before:
            raise CommandError("Administrator boundary changed; transaction rolled back.")
        after = totals()
        return {"batch": batch, "created": {key: after[key] - before[key] for key in after},
                "workers_created": worker_count, "employers_created": employer_count,
                "admins_created": 0}
