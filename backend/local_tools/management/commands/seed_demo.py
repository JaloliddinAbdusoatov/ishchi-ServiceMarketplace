from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AccountStatus, User, UserRole
from apps.applications.models import ApplicationStatus, OrderApplication
from apps.categories.models import Category, WorkerCategory
from apps.chat.models import Conversation, Message
from apps.favorites.models import FavoriteOrder, FavoriteWorker
from apps.invitations.models import InvitationStatus, OrderInvitation
from apps.notifications.models import Notification, NotificationEventType
from apps.orders.models import BudgetType, OrderStatus, ServiceOrder, WorkType
from apps.profiles.models import (
    EmployerProfile,
    EmployerType,
    PricingPreference,
    VerificationStatus,
    WorkerPortfolioItem,
    WorkerProfile,
)
from apps.reports.models import Report, ReportReason, ReportStatus, ReportTargetType
from apps.reviews.models import Review, ReviewDirection


class Command(BaseCommand):
    help = "Seeds realistic Uzbek demonstration data for ISHCHI Teacher Demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe existing demo domain records before re-seeding.",
        )

    def handle(self, *args, **options):
        if getattr(settings, "IS_PRODUCTION", False) or not settings.DEBUG or not getattr(settings, "LOCAL_DEVELOPMENT", False) or settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Synthetic data is restricted to explicit local SQLite development.")
        return self._seed(*args, **options)

    @transaction.atomic
    def _seed(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Resetting existing demo data..."))
            Report.objects.all().delete()
            FavoriteOrder.objects.all().delete()
            FavoriteWorker.objects.all().delete()
            Notification.objects.all().delete()
            Review.objects.all().delete()
            Message.objects.all().delete()
            Conversation.objects.all().delete()
            OrderInvitation.objects.all().delete()
            OrderApplication.objects.all().delete()
            ServiceOrder.objects.all().delete()
            WorkerCategory.objects.all().delete()
            WorkerPortfolioItem.objects.all().delete()
            Category.objects.all().delete()
            WorkerProfile.objects.all().delete()
            EmployerProfile.objects.all().delete()
            User.objects.all().delete()

        if User.objects.filter(phone_number="+998900000001").exists():
            self.stdout.write(self.style.SUCCESS("Demo data already seeded. Use --reset to re-seed."))
            return

        now = timezone.now()

        # 1. Admin Account
        admin_user = User.objects.create_superuser(
            phone_number="+998900000001",
            password="DemoAdmin2026!",
            full_name="Rustamjon Qodirov (Admin)",
            email="admin@ishchi-demo.uz",
        )

        # 2. Categories (Hierarchical: 4 parents + 12 children)
        cat_specs = [
            (
                "qurilish-tamirlash",
                "Qurilish va ta'mirlash",
                "Строительство и ремонт",
                "Construction & Repair",
                "Uy, ofis va tijorat binolarini qurish hamda ta'mirlash xizmatlari",
                [
                    ("santexnika", "Santexnika ishlari", "Сантехника", "Plumbing"),
                    ("elektr-ishlari", "Elektr montaj ishlari", "Электромонтаж", "Electrical Works"),
                    ("boyoqchilik", "Bo'yoqchilik va suvoq", "Малярные работы", "Painting & Plastering"),
                ],
            ),
            (
                "uy-xizmatlari",
                "Uy va maishiy xizmatlar",
                "Бытовые услуги",
                "Home Services",
                "Xonadon va ofislar uchun kundalik maishiy xizmatlar",
                [
                    ("tozalash", "Klining va tozalash", "Клининг и уборка", "Cleaning Services"),
                    ("mebel-yigish", "Mebel yig'ish va ta'mirlash", "Сборка мебели", "Furniture Assembly"),
                    ("konditsioner", "Konditsioner o'rnatish", "Установка кондиционеров", "AC Installation"),
                ],
            ),
            (
                "it-raqamli",
                "IT va raqamli xizmatlar",
                "IT и цифровые услуги",
                "IT & Digital Services",
                "Veb-saytlar, mobil ilovalar va dizayn xizmatlari",
                [
                    ("veb-dasturlash", "Veb-dasturlash", "Веб-разработка", "Web Development"),
                    ("grafik-dizayn", "Grafik dizayn", "Графический дизайн", "Graphic Design"),
                    ("smm-marketing", "SMM va raqamli marketing", "SMM и маркетинг", "SMM & Marketing"),
                ],
            ),
            (
                "avto-xizmatlar",
                "Avto va texnika xizmatlari",
                "Автоуслуги",
                "Auto & Technical Services",
                "Avtomobillar va texnikalarni ta'mirlash xizmatlari",
                [
                    ("avtoelektrik", "Avtoelektrik", "Автоэлектрик", "Auto Electrician"),
                    ("avto-diagnostika", "Kompyuter diagnostikasi", "Диагностика авто", "Auto Diagnostics"),
                    ("yuk-tashish", "Yuk tashish xizmati", "Грузоперевозки", "Cargo & Moving"),
                ],
            ),
        ]

        subcategories = {}
        order_idx = 1
        for slug, uz, ru, en, desc, children in cat_specs:
            parent = Category.objects.create(
                slug=slug,
                name=uz,
                name_uz=uz,
                name_ru=ru,
                name_en=en,
                description=desc,
                is_active=True,
                display_order=order_idx,
            )
            order_idx += 1
            for c_idx, (c_slug, c_uz, c_ru, c_en) in enumerate(children, start=1):
                sub = Category.objects.create(
                    parent=parent,
                    slug=c_slug,
                    name=c_uz,
                    name_uz=c_uz,
                    name_ru=c_ru,
                    name_en=c_en,
                    description=f"{c_uz} bo'yicha professional xizmatlar",
                    is_active=True,
                    display_order=c_idx,
                )
                subcategories[c_slug] = sub

        # 3. 3 Employers
        employers_spec = [
            (
                "+998901000001",
                "Azizbek Karimov",
                "azizbek@ishchi-demo.uz",
                EmployerType.INDIVIDUAL,
                "",
                "Toshkent",
                "Chilonzor",
                "Chilonzor 9-mavze, 14-uy",
                "Shaxsiy uy ta'miri va maishiy xizmatlar buyurtmachisi.",
            ),
            (
                "+998901000002",
                "Malika Tursunova",
                "malika@qurilish-demo.uz",
                EmployerType.COMPANY,
                "O'zbekiston Qurilish MChJ",
                "Toshkent",
                "Yunusobod",
                "Amir Temur shoh ko'chasi, 108-uy",
                "Tijorat va turar-joy obyektlarini qurish va ta'mirlash kompaniyasi.",
            ),
            (
                "+998901000003",
                "Sherzod Mahmudov",
                "sherzod@texnika-demo.uz",
                EmployerType.COMPANY,
                "Toshkent Texnika Servis",
                "Samarqand",
                "Registon",
                "Mirzo Ulug'bek ko'chasi, 45-uy",
                "IT yechimlar, ofis texnikasi va servis xizmatlari markazi.",
            ),
        ]

        employers = []
        for phone, name, email, etype, comp, loc, dist, addr, bio in employers_spec:
            u = User.objects.create_user(
                phone_number=phone,
                password="DemoPass2026!",
                full_name=name,
                email=email,
                role=UserRole.EMPLOYER,
                has_employer_role=True,
                has_worker_role=False,
                is_phone_verified=True,
                account_status=AccountStatus.ACTIVE,
            )
            ep = EmployerProfile.objects.create(
                user=u,
                employer_type=etype,
                full_name=name,
                company_name=comp,
                bio=bio,
                phone_number=phone,
                email=email,
                location=loc,
                district=dist,
                address=addr,
            )
            employers.append(ep)

        # 4. 10 Workers (7 Verified, 3 Unverified)
        workers_spec = [
            ("+998902000001", "Jasur Toshmatov", "Toshkent", "Chilonzor", 7, PricingPreference.FIXED, None, Decimal("350000"), True, VerificationStatus.VERIFIED, ["Santexnika", "Isitish tizimi", "Quvur montaji"], ["santexnika", "elektr-ishlari"]),
            ("+998902000002", "Dilshod Rahimov", "Toshkent", "Yunusobod", 9, PricingPreference.HOURLY, Decimal("95000"), None, True, VerificationStatus.VERIFIED, ["Elektr montaj", "Shit yig'ish", "Yoritish"], ["elektr-ishlari", "konditsioner"]),
            ("+998902000003", "Sardor Alimov", "Toshkent", "Mirzo Ulug'bek", 5, PricingPreference.FIXED, None, Decimal("450000"), True, VerificationStatus.VERIFIED, ["Bo'yoqchilik", "Gipsokarton", "Oboy yopishtirish"], ["boyoqchilik", "mebel-yigish"]),
            ("+998902000004", "Nodira Yusupova", "Toshkent", "Shayxontohur", 4, PricingPreference.HOURLY, Decimal("70000"), None, True, VerificationStatus.VERIFIED, ["General klining", "Ofis tozalash", "Deraza yuvish"], ["tozalash"]),
            ("+998902000005", "Bobur Ismoilov", "Toshkent", "Yakkasaroy", 6, PricingPreference.FIXED, None, Decimal("300000"), True, VerificationStatus.VERIFIED, ["Mebel yig'ish", "Oshxona mebeli", "Shkaf-kupe"], ["mebel-yigish", "boyoqchilik"]),
            ("+998902000006", "Kamoliddin Sobirov", "Samarqand", "Registon", 5, PricingPreference.HOURLY, Decimal("150000"), None, True, VerificationStatus.VERIFIED, ["Django", "React", "PostgreSQL", "REST API"], ["veb-dasturlash", "grafik-dizayn"]),
            ("+998902000007", "Madina Akbarova", "Toshkent", "Mirobod", 3, PricingPreference.FIXED, None, Decimal("500000"), True, VerificationStatus.VERIFIED, ["Figma", "Logotip", "Brending", "SMM dizayn"], ["grafik-dizayn", "smm-marketing"]),
            # 3 Unverified workers (2 PENDING, 1 UNSUBMITTED)
            ("+998902000008", "Umidjon Xolmatov", "Toshkent", "Sergeli", 4, PricingPreference.NEGOTIABLE, None, None, False, VerificationStatus.PENDING, ["Avtoelektrik", "Signalizatsiya"], ["avtoelektrik", "avto-diagnostika"]),
            ("+998902000009", "Farrux Nazarov", "Buxoro", "Markaz", 2, PricingPreference.FIXED, None, Decimal("250000"), False, VerificationStatus.PENDING, ["Konditsioner tozalash", "Freon quyish"], ["konditsioner"]),
            ("+998902000010", "Otabek Ergashev", "Farg'ona", "Markaz", 1, PricingPreference.HOURLY, Decimal("60000"), None, False, VerificationStatus.UNSUBMITTED, ["Yuk tashish", "Kuryer"], ["yuk-tashish"]),
        ]

        workers = []
        for idx, (phone, name, loc, dist, exp, ptype, hrate, frate, is_ver, vstatus, skills, cat_slugs) in enumerate(workers_spec, start=1):
            u = User.objects.create_user(
                phone_number=phone,
                password="DemoPass2026!",
                full_name=name,
                email=f"worker{idx}@ishchi-demo.uz",
                role=UserRole.WORKER,
                has_worker_role=True,
                has_employer_role=False,
                is_phone_verified=True,
                account_status=AccountStatus.ACTIVE,
            )
            wp = WorkerProfile.objects.create(
                user=u,
                full_name=name,
                bio=f"{exp} yillik tajribaga ega malakali mutaxassis ({loc}, {dist}).",
                phone_number=phone,
                location=loc,
                district=dist,
                skills=skills,
                experience_years=exp,
                experience_description=f"{exp} yil davomida 50+ muvaffaqiyatli loyiha.",
                pricing_type=ptype,
                hourly_rate=hrate,
                fixed_rate_from=frate,
                is_available=True,
                verification_status=vstatus,
                is_verified=is_ver,
                verified_by=admin_user if is_ver else None,
                verified_at=now if is_ver else None,
                verification_notes="Demo seeding verification" if is_ver else "",
            )
            for c_i, slug in enumerate(cat_slugs):
                WorkerCategory.objects.create(
                    worker=wp,
                    category=subcategories[slug],
                    is_primary=(c_i == 0),
                    experience_years=exp,
                )
            WorkerPortfolioItem.objects.create(
                worker=wp,
                title=f"{skills[0]} — namuna loyiha",
                description=f"{loc} shahrida bajarilgan sifatli ish namunasi.",
                completed_year=2025,
            )
            workers.append(wp)

        # 5. 18 Realistic Service Orders across all statuses
        orders_spec = [
            # Completed orders (4) -> will have reviews & ratings
            (employers[0], "santexnika", "Hammom va oshxona quvurlarini almashtirish", "Chilonzordagi 3 xonali kvartirada eski quvurlarni yangi plastik quvurlarga almashtirish.", Decimal("1200000"), BudgetType.FIXED, "Toshkent", "Chilonzor", WorkType.ONSITE, OrderStatus.COMPLETED, workers[0]),
            (employers[1], "elektr-ishlari", "Ofis elektr tarmog'ini to'liq yangilash", "Yunusoboddagi 200 kv.m ofis binosida rozetka va yoritish tizimini montaj qilish.", Decimal("4500000"), BudgetType.FIXED, "Toshkent", "Yunusobod", WorkType.ONSITE, OrderStatus.COMPLETED, workers[1]),
            (employers[2], "veb-dasturlash", "Kompaniya uchun korporativ veb-sayt yaratish", "Django va React asosida zamonaviy boshqaruv paneli bilan sayt ishlab chiqish.", Decimal("8000000"), BudgetType.FIXED, "Samarqand", "Registon", WorkType.REMOTE, OrderStatus.COMPLETED, workers[5]),
            (employers[0], "tozalash", "Ta'mirdan keyingi umumiy tozalash", "95 kv.m xonadonni ta'mirdan so'ng to'liq tozalash va derazalarni yuvish.", Decimal("750000"), BudgetType.FIXED, "Toshkent", "Chilonzor", WorkType.ONSITE, OrderStatus.COMPLETED, workers[3]),
            # In Progress orders (3)
            (employers[1], "boyoqchilik", "Yangi turar-joy pod'ezdlarini bo'yash", "3 qavatli bino devorlarini sifatli akril bo'yoq bilan bo'yash.", Decimal("3200000"), BudgetType.FIXED, "Toshkent", "Yunusobod", WorkType.ONSITE, OrderStatus.IN_PROGRESS, workers[2]),
            (employers[0], "mebel-yigish", "Yotoqxona va oshxona mebelini yig'ish", "Buyurtma qilingan MDF mebellarni joyida yig'ish va o'rnatish.", Decimal("900000"), BudgetType.FIXED, "Toshkent", "Yakkasaroy", WorkType.ONSITE, OrderStatus.IN_PROGRESS, workers[4]),
            (employers[2], "grafik-dizayn", "Kompaniya brendbuk va logotipini ishlab chiqish", "Toshkent Texnika Servis uchun zamonaviy logotip va tashrif qog'ozlari dizayni.", Decimal("1800000"), BudgetType.FIXED, "Toshkent", "Mirobod", WorkType.REMOTE, OrderStatus.IN_PROGRESS, workers[6]),
            # Published orders (7) -> open for applications & invitations
            (employers[0], "santexnika", "Isitish qozonini (katyol) o'rnatish va sozlash", "Xususiy uyga ikki konturli gaz qozoni o'rnatish kerak.", Decimal("1500000"), BudgetType.FIXED, "Toshkent", "Chilonzor", WorkType.ONSITE, OrderStatus.PUBLISHED, None),
            (employers[1], "elektr-ishlari", "Ko'p qavatli uy uchun elektr shit yig'ish", "3 fazali asosiy taqsimlash shitini yig'ish va tekshirish.", Decimal("2800000"), BudgetType.FIXED, "Toshkent", "Mirzo Ulug'bek", WorkType.ONSITE, OrderStatus.PUBLISHED, None),
            (employers[1], "konditsioner", "Ofisga 4 dona inverter konditsioner o'rnatish", "18-lik konditsionerlarni o'rnatish va mis trubka tortish.", Decimal("2000000"), BudgetType.FIXED, "Toshkent", "Yunusobod", WorkType.ONSITE, OrderStatus.PUBLISHED, None),
            (employers[2], "veb-dasturlash", "Telegram bot va CRM integratsiyasi", "Buyurtmalarni qabul qiluvchi Telegram bot yaratish.", Decimal("5000000"), BudgetType.FIXED, "Samarqand", "Registon", WorkType.REMOTE, OrderStatus.PUBLISHED, None),
            (employers[2], "smm-marketing", "Instagram sahifani 1 oylik yuritish", "Kontent reja, reels montaj va target reklama sozlash.", Decimal("3000000"), BudgetType.NEGOTIABLE, "Toshkent", "Mirobod", WorkType.HYBRID, OrderStatus.PUBLISHED, None),
            (employers[0], "mebel-yigish", "Bolalar xonasi shkafini yig'ish", "Ikki qavatli krovat va shkafni yig'ib berish.", Decimal("450000"), BudgetType.FIXED, "Toshkent", "Chilonzor", WorkType.ONSITE, OrderStatus.PUBLISHED, None),
            (employers[1], "tozalash", "Biznes markaz oynalarini yuvish", "Tashqi va ichki oynalarni maxsus vositalar bilan yuvish.", Decimal("110000"), BudgetType.HOURLY, "Toshkent", "Shayxontohur", WorkType.ONSITE, OrderStatus.PUBLISHED, None),
            # Draft, Paused, Cancelled, Closed (4)
            (employers[0], "boyoqchilik", "Balkonni ta'mirlash va bo'yash (qoralama)", "Balkon devorlarini shpaklyovka va bo'yoq qilish.", Decimal("600000"), BudgetType.FIXED, "Toshkent", "Chilonzor", WorkType.ONSITE, OrderStatus.DRAFT, None),
            (employers[1], "yuk-tashish", "Qurilish materiallarini obyektga tashish", "Sement va g'ishtlarni Chilonzordan Yunusobodga yetkazish.", Decimal("850000"), BudgetType.FIXED, "Toshkent", "Yunusobod", WorkType.ONSITE, OrderStatus.PAUSED, None),
            (employers[2], "avto-diagnostika", "Xizmat avtomobillarini diagnostika qilish", "3 dona Cobalt avtomobilini kompyuter diagnostikasidan o'tkazish.", Decimal("400000"), BudgetType.FIXED, "Samarqand", "Registon", WorkType.ONSITE, OrderStatus.CANCELLED, None),
            (employers[0], "elektr-ishlari", "Hovli yoritish chiroqlarini o'rnatish", "Datchikli tashqi yoritish chiroqlarini o'rnatish.", Decimal("550000"), BudgetType.FIXED, "Toshkent", "Chilonzor", WorkType.ONSITE, OrderStatus.CLOSED, None),
        ]

        orders = []
        for idx, (emp, cat_slug, title, desc, budget, btype, loc, dist, wtype, st, assigned_w) in enumerate(orders_spec, start=1):
            o = ServiceOrder.objects.create(
                employer=emp,
                category=subcategories[cat_slug],
                assigned_worker=assigned_w,
                title=title,
                description=desc,
                budget=budget,
                budget_type=btype,
                location=loc,
                district=dist,
                work_type=wtype,
                start_date=date.today() + timedelta(days=idx),
                deadline=now + timedelta(days=14 + idx),
                status=st,
                published_at=now - timedelta(days=10) if st != OrderStatus.DRAFT else None,
                completed_at=now - timedelta(days=2) if st == OrderStatus.COMPLETED else None,
            )
            orders.append(o)

        for emp in employers:
            emp.posted_orders_count = ServiceOrder.objects.filter(employer=emp).count()
            emp.completed_orders_count = ServiceOrder.objects.filter(employer=emp, status=OrderStatus.COMPLETED).count()
            emp.save(update_fields=["posted_orders_count", "completed_orders_count"])

        for wp in workers:
            wp.completed_orders_count = ServiceOrder.objects.filter(assigned_worker=wp, status=OrderStatus.COMPLETED).count()
            wp.save(update_fields=["completed_orders_count"])

        # 6. Applications (ACCEPTED on completed/in-progress orders, PENDING/REJECTED/WITHDRAWN on published orders)
        for o in orders[:7]:
            OrderApplication.objects.create(
                order=o,
                worker=o.assigned_worker,
                cover_message="Salom! Ushbu ishni belgilangan muddatda va sifatli bajarib beraman.",
                proposed_price=o.budget,
                status=ApplicationStatus.ACCEPTED,
                responded_at=now - timedelta(days=5),
            )

        app_p1 = OrderApplication.objects.create(
            order=orders[7],
            worker=workers[0],
            cover_message="Gaz qozonlarini o'rnatishda 7 yillik tajribam bor, barcha asboblarim mavjud.",
            proposed_price=Decimal("1400000"),
            status=ApplicationStatus.PENDING,
        )
        OrderApplication.objects.create(
            order=orders[8],
            worker=workers[1],
            cover_message="3 fazali elektr shitlarni loyiha asosida yig'ib beraman.",
            proposed_price=Decimal("2700000"),
            status=ApplicationStatus.PENDING,
        )
        OrderApplication.objects.create(
            order=orders[10],
            worker=workers[5],
            cover_message="Python/Django va Aiogram yordamida tezkor bot yaratib beraman.",
            proposed_price=Decimal("4800000"),
            status=ApplicationStatus.PENDING,
        )
        OrderApplication.objects.create(
            order=orders[11],
            worker=workers[6],
            cover_message="SMM dizayn va reels montaj bo'yicha portfoliomni ko'rishingiz mumkin.",
            proposed_price=Decimal("2900000"),
            status=ApplicationStatus.WITHDRAWN,
            responded_at=now - timedelta(days=1),
        )
        OrderApplication.objects.create(
            order=orders[0],
            worker=workers[1],
            cover_message="Qo'shimcha elektr ishlarida ham yordam berishim mumkin.",
            proposed_price=Decimal("1250000"),
            status=ApplicationStatus.REJECTED,
            rejection_reason="Boshqa mutaxassis tanlandi.",
            responded_at=now - timedelta(days=6),
        )

        # 7. Invitations (PENDING, REJECTED, EXPIRED)
        OrderInvitation.objects.create(
            order=orders[9],
            employer=employers[1],
            worker=workers[1],
            message="Konditsioner elektr ulash ishlariga sizni taklif qilamiz.",
            proposed_budget=Decimal("2000000"),
            status=InvitationStatus.PENDING,
            expires_at=now + timedelta(days=5),
        )
        OrderInvitation.objects.create(
            order=orders[12],
            employer=employers[0],
            worker=workers[4],
            message="Shkaf yig'ishga sizni taklif qilaman.",
            proposed_budget=Decimal("450000"),
            status=InvitationStatus.PENDING,
            expires_at=now + timedelta(days=6),
        )
        OrderInvitation.objects.create(
            order=orders[13],
            employer=employers[1],
            worker=workers[3],
            message="Oynalarni yuvish bo'yicha taklif.",
            proposed_budget=Decimal("110000"),
            status=InvitationStatus.EXPIRED,
            expires_at=now - timedelta(days=1),
        )

        # 8. Conversations & Messages
        conv1 = Conversation.objects.create(
            order=orders[4],
            employer=employers[1],
            worker=workers[2],
            last_message_at=now - timedelta(hours=2),
        )
        Message.objects.create(
            conversation=conv1,
            sender=employers[1].user,
            content="Assalomu alaykum Sardor, ertaga soat 09:00 da boshlay olasizmi?",
            is_read=True,
            read_at=now - timedelta(hours=3),
        )
        Message.objects.create(
            conversation=conv1,
            sender=workers[2].user,
            content="Vaalaykum assalom! Ha, albatta. Barcha materiallar tayyor bo'lsa 09:00 da yetib boraman.",
            is_read=False,
        )

        conv2 = Conversation.objects.create(
            order=orders[7],
            employer=employers[0],
            worker=workers[0],
            last_message_at=now - timedelta(hours=1),
        )
        Message.objects.create(
            conversation=conv2,
            sender=workers[0].user,
            content="Salom Azizbek aka, arizamni ko'rib chiqdingizmi? Qozon modeli qanday?",
            is_read=False,
        )

        # 9. Reviews on Completed Orders + recalculate ratings
        reviews_data = [
            (orders[0], employers[0].user, workers[0].user, ReviewDirection.EMPLOYER_TO_WORKER, 5, "Juda tez va toza ishladilar, tavsiya qilaman!"),
            (orders[0], workers[0].user, employers[0].user, ReviewDirection.WORKER_TO_EMPLOYER, 5, "Ajoyib buyurtmachi, to'lov o'z vaqtida amalga oshirildi."),
            (orders[1], employers[1].user, workers[1].user, ReviewDirection.EMPLOYER_TO_WORKER, 5, "Elektr montaj ishlari standart asosida bajarildi."),
            (orders[2], employers[2].user, workers[5].user, ReviewDirection.EMPLOYER_TO_WORKER, 5, "Sayt juda chiroyli va tezkor chiqdi."),
            (orders[3], employers[0].user, workers[3].user, ReviewDirection.EMPLOYER_TO_WORKER, 4, "Yaxshi tozalashdi, rahmat."),
        ]
        for o, rev_u, ree_u, dir_val, rat, comm in reviews_data:
            Review.objects.create(
                order=o,
                reviewer=rev_u,
                reviewee=ree_u,
                direction=dir_val,
                rating=rat,
                comment=comm,
            )

        workers[0].rating_avg = Decimal("5.00"); workers[0].review_count = 1; workers[0].save(update_fields=["rating_avg", "review_count"])
        workers[1].rating_avg = Decimal("5.00"); workers[1].review_count = 1; workers[1].save(update_fields=["rating_avg", "review_count"])
        workers[5].rating_avg = Decimal("5.00"); workers[5].review_count = 1; workers[5].save(update_fields=["rating_avg", "review_count"])
        workers[3].rating_avg = Decimal("4.00"); workers[3].review_count = 1; workers[3].save(update_fields=["rating_avg", "review_count"])
        employers[0].rating_avg = Decimal("5.00"); employers[0].review_count = 1; employers[0].save(update_fields=["rating_avg", "review_count"])

        # 10. Notifications
        Notification.objects.create(
            recipient=employers[0].user,
            event_type=NotificationEventType.NEW_APPLICATION,
            title="Yangi ariza keldi",
            message=f"{workers[0].full_name} '{orders[7].title}' buyurtmasiga ariza topshirdi.",
            data={"order_id": str(orders[7].id), "application_id": str(app_p1.id)},
        )
        Notification.objects.create(
            recipient=workers[1].user,
            event_type=NotificationEventType.NEW_INVITATION,
            title="Yangi taklifnoma",
            message=f"{employers[1].company_name} sizni '{orders[9].title}' buyurtmasiga taklif qildi.",
            data={"order_id": str(orders[9].id)},
        )
        Notification.objects.create(
            recipient=workers[0].user,
            event_type=NotificationEventType.NEW_REVIEW,
            title="Yangi baho oldingiz",
            message="Azizbek Karimov sizga 5/5 baho qo'ydi.",
            data={"order_id": str(orders[0].id)},
            is_read=True,
            read_at=now,
        )

        # 11. Favorites & Sample Report
        FavoriteWorker.objects.create(user=employers[0].user, worker=workers[0])
        FavoriteWorker.objects.create(user=employers[1].user, worker=workers[1])
        FavoriteOrder.objects.create(user=workers[0].user, order=orders[7])

        Report.objects.create(
            reporter=employers[0].user,
            target_type=ReportTargetType.ORDER,
            target_order=orders[16],
            reason=ReportReason.OTHER,
            description="Buyurtma tafsilotlari tekshirilishi kerak (demo report).",
            status=ReportStatus.PENDING,
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded ISHCHI Teacher Demo database!"))
        self.stdout.write("  Admin:    +998900000001 / DemoAdmin2026!")
        self.stdout.write("  Employer: +998901000001..+998901000003 / DemoPass2026!")
        self.stdout.write("  Worker:   +998902000001..+998902000010 / DemoPass2026! (1-7 verified, 8-10 unverified)")
