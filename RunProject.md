# ISHCHI — loyihani ishga tushirish / Running the project / Запуск проекта

[O‘zbekcha](#uzbek) | [English](#english) | [Русский](#russian)

<a id="uzbek"></a>

## O‘zbekcha — loyihani ishga tushirish

Buyruqlar Windows PowerShell uchun. Har bir terminalni loyiha ildizidan oching:

```powershell
Set-Location D:\Project\ishchi
```

Loyiha boshqa papkada bo‘lsa, o‘sha papkaning yo‘lini yozing. Quyidagi buyruqlar
yo‘riqnoma sifatida berilgan; hujjat yaratilayotganda ular bajarilmadi.

### 1. Qaysi usulni tanlash kerak?

1. **Docker’siz: Django + SQLite + Vite.** Kod yozish, interfeysni o‘zgartirish va
   tez sinash uchun. Python 3.14, Node.js 24 va ikkita terminal kerak. Sayt:
   **http://127.0.0.1:5173**; backend: **http://127.0.0.1:8001**.
2. **Docker bilan: PostgreSQL + Redis + Django/Gunicorn + Nginx.** Tayyorlangan
   lokal Docker muhitida kundalik foydalanish uchun. Docker Desktop kerak.
   Sayt va API: **http://127.0.0.1:8080**.
3. **Faqat backend yoki faqat frontend.** Quyidagi tegishli server buyrug‘ini
   alohida bajarish mumkin. Frontend’dagi ma’lumotlar va login ishlashi uchun
   backend ham ishlashi kerak.
4. **Frontend build’ini ko‘rish.** `npm run build` va `npm run preview` tayyor
   frontend build’ini tekshiradi; API uchun backend’ni alohida ishga tushiring.
5. **Production.** Hozir tayyor ommaviy ishga tushirish usuli emas; alohida
   infratuzilma, TLS va release talablari bor. [Runbook](deploy/RUNBOOK.md)ga qarang.

**SQLite va PostgreSQL — alohida bazalar.** Birida yaratgan akkaunt, parol,
buyurtma yoki chat ikkinchisiga avtomatik ko‘chmaydi. Ikkala muhitni parallel
ishlatish mumkin, lekin qaysi portga kirganingizni tekshiring.

### 2. Docker’siz ishga tushirish — SQLite

#### 2.1. Birinchi marta tayyorlash

Python 3.14 va Node.js 24 o‘rnatilgan bo‘lishi kerak. Loyiha ildizida:

```powershell
python --version
node --version
npm --version

python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
```

Shablondagi bo‘sh `DJANGO_SECRET_KEY` uchun lokal kalit yarating. Quyidagi buyruq
faqat bo‘sh qiymatni to‘ldiradi, mavjud kalitni almashtirmaydi va kalitni ekranga
chiqarmaydi:

```powershell
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from django.core.management.utils import get_random_secret_key; p=Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY='+get_random_secret_key()+'\n'), encoding='utf-8')"
```

Frontend paketlarini o‘rnating:

```powershell
Set-Location frontend
npm ci
```

#### 2.2. Birinchi terminal — backend

Loyiha ildizidan:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

`migrate` yangi SQLite bazasida jadvallarni yaratadi yoki mavjud sxemani yangilaydi.
Oddiy qayta startda, yangi migratsiya bo‘lmasa, faqat `runserver` yetarli.
Bu aniq development sozlamasi PostgreSQL/Redis targetlaridan foydalanmaydi.

#### 2.3. Ikkinchi terminal — frontend

Yangi terminalda loyiha ildizidan:

```powershell
Set-Location frontend
npm run dev
```

Brauzerda **http://127.0.0.1:5173** ni oching. Vite `/api/` va `/media/`
so‘rovlarini `127.0.0.1:8001` dagi backend’ga yuboradi. Ikkala terminal ochiq tursin.

#### 2.4. SQLite’da administrator yaratish

Backend ishlayotgan terminalni band qilmaslik uchun uchinchi terminalda,
loyiha ildizidan bajaring:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py createsuperuser --settings=config.settings.development
```

Telefonni `+998XXXXXXXXX` formatida va o‘zingiz tanlagan parolni kiriting.
Parol yozilganda terminalda ko‘rinmasligi odatiy holat. Admin panel:
**http://127.0.0.1:8001/django-admin/**.

Mavjud telefon bilan yangi akkaunt yaratmang. Bu buyruq mavjud admin parolini
almashtirmaydi va Docker bazasiga admin qo‘shmaydi.

#### 2.5. Yangi bo‘sh bazadan foydalanish

Standart umumiy login/parol yo‘q. Admin panelda xizmat kategoriyalarini yarating,
saytda buyurtmachi va ishchi sifatida alohida ro‘yxatdan o‘ting. Ro‘yxatdan o‘tish
SMS’siz akkauntni faollashtiradi. KYC ixtiyoriy; SMS orqali tasdiqlash/parol
tiklash haqiqiy provayderni talab qiladi. To‘lovlar o‘chirilgan.

Faqat o‘zingizning lokal SQLite bazangizga sun’iy kategoriyalar, profillar va
buyurtmalar qo‘shish kerak bo‘lsa, loyiha ildizidan ixtiyoriy buyruq:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py seed_marketplace --settings=config.settings.development
```

Sun’iy foydalanuvchilarning kirish uchun yaroqli paroli bo‘lmaydi. Sayt orqali
o‘z akkauntingizni yarating. Oddiy startda seed qilish kerak emas.

#### 2.6. To‘xtatish va keyingi safar ochish

Backend va frontend terminallarida `Ctrl+C` bosing. Keyingi safar 2.2-bo‘limdagi
`runserver` va 2.3-bo‘limdagi `npm run dev` buyruqlarini bajaring.
Paketlarni qayta o‘rnatish, admin yaratish yoki seed qilish shart emas.

Baza: `backend/.local/ishchi.sqlite3`; media: `backend/.local/media/`.
`.local/` papkasini o‘chirish shu muhit ma’lumotlarini yo‘qotadi.

### 3. Docker bilan ishga tushirish — PostgreSQL va Redis

#### 3.1. Old shartlar

- Docker Desktop ishga tushgan, Linux konteynerlari tanlangan bo‘lsin.
- `deploy/.env.local`, xususiy secret fayllari va mos amaldagi DB/Redis
  ruxsatlari tayyor bo‘lishi kerak. Yangi klon uchun to‘liq tayyorlash tartibi:
  [deploy/LOCAL.md](deploy/LOCAL.md#uzbek).
- Mavjud ishchi volume’lar va migratsiyalar tayyor bo‘lishi kerak. Oddiy start
  migratsiya, seed yoki admin yaratishni bajarmaydi.

Docker Desktop’ni ochish bazalar ishga tushganini anglatishi mumkin, lekin
backend va gateway ham alohida ishlashi kerak. Faqat PostgreSQL/Redis ishlasa,
sayt ochilmaydi.

Ilovaning o‘zi uchun hostda Python/Node.js shart emas. `local.py` kabi yordamchi
host skriptlari uchun esa Python virtual muhiti kerak. Mavjud muhitda secret’larni
qayta yaratmang va `.env.local` ni shablon bilan ustidan yozmang.

#### 3.2. Har bir yangi terminalda Compose buyrug‘ini belgilash

Loyiha ildizidan PowerShell’da:

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker --context desktop-linux info --format '{{.ServerVersion}}'
docker @dc config --quiet
```

`config --quiet` konfiguratsiyani secret qiymatlarini chiqarmasdan tekshiradi.
Bu tekshiruv baza sxemasi yoki ruxsat muddati to‘g‘riligini tasdiqlamaydi.

#### 3.3. Image yaratish yoki kod yangilanganda qayta build qilish

```powershell
docker @dc build backend gateway
```

Har bir oddiy startda build shart emas. Backend kodi yoki frontend build’i
o‘zgarganda kerak; konteynerlarda Vite/Django hot reload yo‘q.

#### 3.4. Ishchi muhitni ishga tushirish

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
docker @dc --profile work ps
```

Ochish:

- Sayt: **http://127.0.0.1:8080**.
- Admin: **http://127.0.0.1:8080/django-admin/**.
- Readiness: **http://127.0.0.1:8080/api/v1/health/ready/** — 200 qaytarishi kerak.

Bu muhitda sayt va API bitta `8080` port orqali ishlaydi. Alohida `npm run dev`
yoki `manage.py runserver` bajarish kerak emas. Barcha admin va foydalanuvchi
akkauntlari shu muhitning PostgreSQL bazasidan olinadi.

#### 3.5. Docker’dagi PostgreSQL uchun yangi admin

Bu mavjud, ishlayotgan backend konteynerida interaktiv admin yaratadi.
Faqat shu bazada yangi administrator kerak bo‘lganda bajaring:

```powershell
docker @dc exec backend python manage.py createsuperuser
```

Docker backend konfiguratsiyasi `config.settings.local_postgres` ni tanlaydi.
Shuning uchun bu buyruq SQLite’ga yozmaydi. Telefon va parolni interaktiv kiriting;
parolni buyruq argumentiga yoki Git fayliga yozmang. Mavjud akkaunt bo‘lsa,
yangisini yaratishga urinmang. SQLite’dagi akkaunt avtomatik ko‘chirilmaydi.

#### 3.6. Holat, restart va loglar

```powershell
docker @dc --profile work ps
docker @dc logs --tail 100 backend gateway
docker @dc restart backend gateway
```

Loglarda shaxsiy ma’lumotlar bo‘lishi mumkin; ulashishdan oldin tekshiring.
`restart` yangilangan image’ni qo‘llamaydi. Build’dan keyin image’ni qo‘llash uchun:

```powershell
docker @dc --profile work up -d backend gateway
```

#### 3.7. To‘xtatish va qayta ishga tushirish

To‘xtatish:

```powershell
docker @dc --profile work stop
```

Keyingi safar (avval `$dc` ni 3.2-bo‘limdagidek belgilang):

```powershell
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

Ma’lumotlar Docker volume’larida saqlanadi: ishchi PostgreSQL uchun
`ishchi-local_pg-work`, Redis uchun `ishchi-local_redis-work`, media uchun
`ishchi-local_media`. **`down -v`, volume prune, ishchi bazani reset yoki reseed
qilmang.** Oddiy stop/start volume’larni o‘chirmaydi.

#### 3.8. Ruxsatlar va migratsiyalar

Qayd etilgan kundalik ishchi PG/Redis ruxsati **2026-11-24, 23:59 Asia/Tashkent**
gacha. Bu test, migratsiya, backup yoki restore ruxsatini anglatmaydi; boshqa
kompyuterga ham ko‘chmaydi. Ruxsat tugasa, yangi haqiqiy tasdiq talab qilinadi,
fayldagi sanani o‘zboshimchalik bilan o‘zgartirmang.

Runtime login bilan migratsiya taqiqlangan. Maxsus migrator va
`deploy/compose.local-roles.yml` overlay’i talab qilinadi. Oddiy run yo‘riqnomasida
migratsiyani avtomatik bajarmang. Tafsilotlar:
[LOCAL_SAFETY.md](deploy/LOCAL_SAFETY.md), [LOCAL.md](deploy/LOCAL.md#uzbek).

### 4. Faqat frontend build’ini ko‘rish

Loyiha ildizidan:

```powershell
Set-Location frontend
npm run build
npm run preview -- --host 127.0.0.1
```

Terminal ko‘rsatgan manzilni oching; odatiy port `4173`. `Ctrl+C` bilan to‘xtating.
Bu frontend build preview’i; o‘zgarishlar ko‘rinishi uchun yana build qilish kerak.
O‘rnatilgan Vite versiyasida preview `/api/` va `/media/` uchun server proxy
sozlamalarini meros oladi: so‘rovlar `127.0.0.1:8001` ga yuboriladi. API/login’ni
sinash uchun 2.2-bo‘limdagi SQLite backend’ni ham ishga tushiring. Preview
production hosting o‘rnini bosmaydi; kundalik kod yozish uchun `npm run dev` qulay.

### 5. Test va tekshiruvlar — server ishga tushirishdan alohida

Quyidagi backend testlari xotiradagi SQLite’dan foydalanadi va ishchi
PostgreSQL/Redis’ni talab qilmaydi. Loyiha ildizidan:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py check --settings=config.settings.testing
Set-Location backend
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

Frontend uchun boshqa terminalda loyiha ildizidan:

```powershell
Set-Location frontend
npm test
npm run build
```

PostgreSQL/Redis integratsion testlari oddiy startning qismi emas. Ular alohida
test bazasi, volume va tegishli ruxsatlarni talab qiladi; ishchi bazada bajarmang.
Buyruqlar va cheklovlar: [LOCAL.md](deploy/LOCAL.md#uzbek).

### 6. Muammo bo‘lsa

- **Docker daemon/pipe topilmadi:** Docker Desktop’ni oching, ishga tushishini
  kuting va `desktop-linux` konteksti mavjudligini tekshiring.
- **8080 ochilmayapti:** `docker @dc --profile work ps` orqali backend va gateway
  ham ishlayotganini tekshiring; keyin readiness va loglarni ko‘ring.
- **5173 da API ishlamayapti:** Django `127.0.0.1:8001` da ishlashi kerak.
  Docker’dagi `8080` backend bu Vite konfiguratsiyasiga avtomatik ulanmaydi.
- **Admin paroli ishlamayapti:** avval port/bazani tekshiring: `8001` — SQLite,
  `8080` — Docker PostgreSQL. Bir xil telefon ikki bazada bo‘lsa ham paroli
  va huquqlari mustaqil. Takroriy xato login vaqtinchalik blokka olib kelishi mumkin.
- **SQLite’da `no such table`:** 2.2-bo‘limdagi development `migrate` ni bajaring.
- **Kategoriya/buyurtmalar yo‘q:** yangi klon bo‘sh bo‘ladi yoki boshqa bazani
  ochgansiz. Mavjud ishchi bazani to‘ldirish uchun reset/seed qilmang.
- **Ruxsat muddati yoki operator xatosi:** [LOCAL_SAFETY.md](deploy/LOCAL_SAFETY.md)
  bo‘yicha mos ruxsatni tekshiring; himoyani chetlab o‘tmang.

`.env`, bazalar, parollar va media GitHub orqali tarqatilmaydi. Kodni push qilish
ilovani ishga tushirmaydi va bir bazadagi akkauntlarni boshqasiga ko‘chirmaydi.

Qo‘shimcha hujjatlar: [README](README.md), [lokal Docker](deploy/LOCAL.md#uzbek),
[kundalik foydalanish](deploy/DAILY_USE.md),
[backup/recovery](deploy/LOCAL_OPERATIONS.md), [production](deploy/RUNBOOK.md).

---

<a id="english"></a>

## English — running ISHCHI

Commands use Windows PowerShell. Open each terminal at the project root:

```powershell
Set-Location D:\Project\ishchi
```

Replace the path if your checkout is elsewhere. These are instructions; the
commands were not executed while writing this document.

### 1. Choose a startup method

1. **Without Docker: Django + SQLite + Vite.** For development, UI changes and
   quick checks. Requires Python 3.14, Node.js 24 and two terminals. Website:
   **http://127.0.0.1:5173**; backend: **http://127.0.0.1:8001**.
2. **With Docker: PostgreSQL + Redis + Django/Gunicorn + Nginx.** For daily use
   in the prepared local Docker environment. Requires Docker Desktop. Website
   and API: **http://127.0.0.1:8080**.
3. **Backend or frontend only.** Run the relevant server command separately.
   The frontend still needs the backend for data and login.
4. **Frontend build preview.** Build and preview the compiled frontend; start
   the backend separately for API requests.
5. **Production.** Public startup is not currently a ready-to-use path. Separate
   infrastructure, TLS and release requirements apply: [runbook](deploy/RUNBOOK.md).

**SQLite and PostgreSQL are separate databases.** Accounts, passwords, jobs and
chat do not transfer automatically. Both environments can run at the same time;
check the port you are opening.

### 2. Run without Docker — SQLite

#### 2.1. First-time setup

Install Python 3.14 and Node.js 24. From the project root:

```powershell
python --version
node --version
npm --version

python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
```

Generate a local key for the template's empty `DJANGO_SECRET_KEY`. This fills
only an empty value, preserves an existing key and does not print it:

```powershell
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from django.core.management.utils import get_random_secret_key; p=Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY='+get_random_secret_key()+'\n'), encoding='utf-8')"
```

Install frontend dependencies:

```powershell
Set-Location frontend
npm ci
```

#### 2.2. First terminal — backend

From the project root:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

`migrate` creates tables in a fresh SQLite database or updates the existing
schema. On later starts, use only `runserver` if no new migrations are pending.
These explicit development settings do not use PostgreSQL or Redis targets.

#### 2.3. Second terminal — frontend

Open another terminal at the project root:

```powershell
Set-Location frontend
npm run dev
```

Open **http://127.0.0.1:5173**. Vite proxies `/api/` and `/media/` to the backend
at `127.0.0.1:8001`. Keep both terminals running.

#### 2.4. Create a SQLite administrator

In a third terminal, from the project root:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py createsuperuser --settings=config.settings.development
```

Enter a phone number in `+998XXXXXXXXX` format and your own password. Password
input is hidden in the terminal. Admin: **http://127.0.0.1:8001/django-admin/**.
Do not create another account with an existing phone number. This command neither
changes an existing administrator's password nor creates a Docker database user.

#### 2.5. Use a fresh database

There is no shared default login/password. Create service categories in Django
admin, then register employer and worker accounts on the website. Registration
activates accounts without SMS. KYC is optional. SMS verification/password reset
requires a real provider. Payments are disabled.

Optionally add fictional categories, profiles and jobs to your own local SQLite
database, from the project root:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py seed_marketplace --settings=config.settings.development
```

Generated users have no usable passwords. Register your own accounts on the
website. Seeding is not required for normal startup.

#### 2.6. Stop and start again

Press `Ctrl+C` in both server terminals. Next time, run `runserver` from section
2.2 and `npm run dev` from section 2.3. No dependency reinstall, administrator
creation or seeding is required for ordinary restarts.

Database: `backend/.local/ishchi.sqlite3`; media: `backend/.local/media/`.
Deleting `.local/` deletes this environment's local data.

### 3. Run with Docker — PostgreSQL and Redis

#### 3.1. Prerequisites

- Start Docker Desktop with Linux containers selected.
- Prepare `deploy/.env.local`, private secret files and matching valid DB/Redis
  authorizations. Full setup for a new clone: [LOCAL.md](deploy/LOCAL.md#english).
- Working volumes and migrations must already be prepared. Ordinary startup
  does not run migrations, seed data or create an administrator.

Opening Docker Desktop may start databases, but backend and gateway must also
be running. PostgreSQL/Redis alone do not serve the website.

The application itself does not require host Python/Node.js. Host helper scripts
such as `local.py` require a Python virtual environment. In an existing setup,
do not regenerate secrets or overwrite `.env.local` with its template.

#### 3.2. Define Compose arguments in each new terminal

From the project root in PowerShell:

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker --context desktop-linux info --format '{{.ServerVersion}}'
docker @dc config --quiet
```

`config --quiet` checks configuration without printing secret values. It does
not verify the database schema or authorization expiry.

#### 3.3. Build images initially or after code changes

```powershell
docker @dc build backend gateway
```

A build is not needed on every start. Rebuild after backend or frontend code
changes; containers do not provide Vite/Django hot reload.

#### 3.4. Start the working environment

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
docker @dc --profile work ps
```

Open:

- Website: **http://127.0.0.1:8080**.
- Admin: **http://127.0.0.1:8080/django-admin/**.
- Readiness: **http://127.0.0.1:8080/api/v1/health/ready/** — should return 200.

Website and API share port `8080`. Do not run a separate Vite or Django development
server for this method. Accounts come from this environment's PostgreSQL database.

#### 3.5. Create a new administrator in Docker PostgreSQL

Use only when a new administrator is needed in this database. The backend
container must already be running:

```powershell
docker @dc exec backend python manage.py createsuperuser
```

The Docker backend selects `config.settings.local_postgres`, so this does not
write to SQLite. Enter the phone/password interactively. Do not put passwords
in arguments or Git files. Do not recreate an existing account. SQLite accounts
are not copied automatically.

#### 3.6. Status, restart and logs

```powershell
docker @dc --profile work ps
docker @dc logs --tail 100 backend gateway
docker @dc restart backend gateway
```

Logs may contain personal data; review before sharing. `restart` does not apply
a newly built image. After building, apply the updated image with:

```powershell
docker @dc --profile work up -d backend gateway
```

#### 3.7. Stop and start again

Stop:

```powershell
docker @dc --profile work stop
```

Next time, first define `$dc` as shown in section 3.2, then run:

```powershell
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

Data remains in Docker volumes: PostgreSQL `ishchi-local_pg-work`, Redis
`ishchi-local_redis-work`, media `ishchi-local_media`. **Do not use `down -v`,
volume prune, reset or reseed the working database.** Ordinary stop/start
preserves volumes.

#### 3.8. Authorizations and migrations

The recorded daily working PG/Redis authorization lasts through **2026-11-24,
23:59 Asia/Tashkent**. It does not authorize tests, migrations, backup or restore,
and does not transfer to another computer. Expiry requires genuine renewed
approval; do not edit dates on your own.

Runtime-login migrations are prohibited. They require a dedicated migrator and
`deploy/compose.local-roles.yml`. Do not add automatic migrations to normal
startup. Details: [LOCAL_SAFETY.md](deploy/LOCAL_SAFETY.md),
[LOCAL.md](deploy/LOCAL.md#english).

### 4. Preview the compiled frontend

From the project root:

```powershell
Set-Location frontend
npm run build
npm run preview -- --host 127.0.0.1
```

Open the address printed by the terminal, normally port `4173`. Stop with
`Ctrl+C`. Rebuild to see source changes. In the installed Vite version, preview
inherits server proxy settings for `/api/` and `/media/`, forwarding to
`127.0.0.1:8001`. Start the SQLite backend from section 2.2 for API/login checks.
Preview is not production hosting; use `npm run dev` for everyday development.

### 5. Tests and checks — separate from startup

These backend tests use in-memory SQLite and do not require working
PostgreSQL/Redis. From the project root:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py check --settings=config.settings.testing
Set-Location backend
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

For the frontend, open another terminal at the project root:

```powershell
Set-Location frontend
npm test
npm run build
```

PostgreSQL/Redis integration tests are separate from normal startup. They require
dedicated test databases, volumes and authorizations. Do not run against the
working database. Instructions: [LOCAL.md](deploy/LOCAL.md#english).

### 6. Troubleshooting

- **Docker daemon/pipe not found:** start Docker Desktop, wait until ready and
  check that the `desktop-linux` context exists.
- **8080 does not open:** use `docker @dc --profile work ps` to check backend
  and gateway, then inspect readiness and logs.
- **API fails on 5173:** Django must run at `127.0.0.1:8001`. Docker's backend
  on `8080` is not automatically used by this Vite configuration.
- **Administrator password fails:** check the database/port first: `8001` means
  SQLite; `8080` means Docker PostgreSQL. The same phone can have independent
  passwords and permissions in each. Repeated failed logins can cause a temporary lock.
- **SQLite reports `no such table`:** run the development migration in section 2.2.
- **No categories/jobs:** a fresh clone is empty, or you opened another database.
  Do not reset/seed the existing working database to fill it.
- **Expired authorization/operator error:** follow
  [LOCAL_SAFETY.md](deploy/LOCAL_SAFETY.md); do not bypass the guards.

`.env`, databases, passwords and media are not distributed through GitHub.
Pushing code does not start the app or transfer accounts between databases.

More documentation: [README](README.md), [local Docker](deploy/LOCAL.md#english),
[daily use](deploy/DAILY_USE.md), [backup/recovery](deploy/LOCAL_OPERATIONS.md),
[production](deploy/RUNBOOK.md).

---

<a id="russian"></a>

## Русский — запуск ISHCHI

Команды предназначены для Windows PowerShell. Каждый терминал открывайте
в корне проекта:

```powershell
Set-Location D:\Project\ishchi
```

Если проект находится в другой папке, замените путь. Это инструкция: при
создании документа команды не выполнялись.

### 1. Какой способ выбрать?

1. **Без Docker: Django + SQLite + Vite.** Для разработки, изменения интерфейса
   и быстрых проверок. Нужны Python 3.14, Node.js 24 и два терминала. Сайт:
   **http://127.0.0.1:5173**; backend: **http://127.0.0.1:8001**.
2. **С Docker: PostgreSQL + Redis + Django/Gunicorn + Nginx.** Для повседневного
   использования подготовленной локальной среды. Нужен Docker Desktop.
   Сайт и API: **http://127.0.0.1:8080**.
3. **Только backend или frontend.** Можно выполнить соответствующую команду
   сервера отдельно. Для данных и входа frontend всё равно нужен backend.
4. **Просмотр frontend build.** Сборка и preview готового frontend; для API
   backend запускается отдельно.
5. **Production.** Готового публичного запуска пока нет: нужны отдельная
   инфраструктура, TLS и выполнение [требований выпуска](deploy/RUNBOOK.md).

**SQLite и PostgreSQL — отдельные базы.** Аккаунты, пароли, заказы и чат
автоматически не переносятся. Можно запустить обе среды одновременно,
но проверяйте порт открываемого сайта.

### 2. Запуск без Docker — SQLite

#### 2.1. Первая настройка

Установите Python 3.14 и Node.js 24. Из корня проекта:

```powershell
python --version
node --version
npm --version

python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
```

Создайте локальный ключ для пустого `DJANGO_SECRET_KEY` в шаблоне. Команда
заполняет только пустое значение, сохраняет существующий ключ и не выводит его:

```powershell
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from django.core.management.utils import get_random_secret_key; p=Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY='+get_random_secret_key()+'\n'), encoding='utf-8')"
```

Установите зависимости frontend:

```powershell
Set-Location frontend
npm ci
```

#### 2.2. Первый терминал — backend

Из корня проекта:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

`migrate` создаёт таблицы новой SQLite-базы или обновляет существующую схему.
При последующих запусках достаточно `runserver`, если новых миграций нет.
Эти явные development-настройки не используют PostgreSQL/Redis.

#### 2.3. Второй терминал — frontend

Откройте новый терминал в корне проекта:

```powershell
Set-Location frontend
npm run dev
```

Откройте **http://127.0.0.1:5173**. Vite направляет `/api/` и `/media/` на backend
`127.0.0.1:8001`. Оба терминала должны оставаться запущенными.

#### 2.4. Создание администратора SQLite

В третьем терминале из корня проекта:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py createsuperuser --settings=config.settings.development
```

Введите телефон в формате `+998XXXXXXXXX` и собственный пароль. Ввод пароля
в терминале скрыт — это нормально. Admin: **http://127.0.0.1:8001/django-admin/**.
Не создавайте повторный аккаунт с существующим номером. Команда не меняет
пароль существующего администратора и не добавляет его в Docker-базу.

#### 2.5. Работа с новой пустой базой

Общего стандартного логина/пароля нет. Создайте категории услуг через Django
admin, затем зарегистрируйте заказчика и работника на сайте. Регистрация
активирует аккаунт без SMS. KYC необязательна; SMS-проверка/сброс пароля требуют
настоящего провайдера. Платежи отключены.

При необходимости добавьте вымышленные категории, профили и заказы только
в собственную локальную SQLite-базу. Необязательная команда из корня проекта:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py seed_marketplace --settings=config.settings.development
```

У созданных синтетических пользователей нет пригодных для входа паролей.
Зарегистрируйте собственные аккаунты на сайте. При обычном запуске seed не нужен.

#### 2.6. Остановка и следующий запуск

Нажмите `Ctrl+C` в терминалах backend и frontend. В следующий раз выполните
`runserver` из раздела 2.2 и `npm run dev` из раздела 2.3. Переустанавливать
зависимости, создавать администратора и запускать seed не требуется.

База: `backend/.local/ishchi.sqlite3`; медиа: `backend/.local/media/`.
Удаление `.local/` уничтожит локальные данные этой среды.

### 3. Запуск с Docker — PostgreSQL и Redis

#### 3.1. Предварительные условия

- Запустите Docker Desktop и выберите Linux-контейнеры.
- Подготовьте `deploy/.env.local`, приватные секреты и соответствующие действующие
  разрешения DB/Redis. Для нового клона: [LOCAL.md](deploy/LOCAL.md#russian).
- Рабочие volume и миграции должны быть подготовлены заранее. Обычный запуск
  не выполняет миграции, seed и создание администратора.

Docker Desktop может запустить базы, но backend и gateway тоже должны работать.
Одних PostgreSQL/Redis недостаточно для открытия сайта.

Самому приложению Python/Node.js на хосте не нужны. Вспомогательные host-скрипты,
например `local.py`, требуют Python virtual environment. В существующей среде
не генерируйте секреты заново и не перезаписывайте `.env.local` шаблоном.

#### 3.2. Задайте параметры Compose в каждом новом терминале

Из корня проекта в PowerShell:

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker --context desktop-linux info --format '{{.ServerVersion}}'
docker @dc config --quiet
```

`config --quiet` проверяет конфигурацию без вывода секретных значений.
Это не проверка схемы базы или срока разрешения.

#### 3.3. Сборка image впервые или после изменения кода

```powershell
docker @dc build backend gateway
```

При каждом старте сборка не нужна. Пересобирайте после изменений backend или
frontend: в контейнерах нет Vite/Django hot reload.

#### 3.4. Запуск рабочей среды

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
docker @dc --profile work ps
```

Откройте:

- Сайт: **http://127.0.0.1:8080**.
- Admin: **http://127.0.0.1:8080/django-admin/**.
- Readiness: **http://127.0.0.1:8080/api/v1/health/ready/** — должен вернуть 200.

Сайт и API используют один порт `8080`. Отдельные Vite и Django dev server
для этого способа не нужны. Аккаунты берутся из PostgreSQL этой среды.

#### 3.5. Новый администратор в Docker PostgreSQL

Выполняйте только если в этой базе нужен новый администратор. Backend-контейнер
должен быть запущен:

```powershell
docker @dc exec backend python manage.py createsuperuser
```

Docker backend выбирает `config.settings.local_postgres`: запись не попадёт
в SQLite. Введите телефон/пароль интерактивно. Не передавайте пароль аргументом
или через файл в Git. Не создавайте существующий аккаунт заново. SQLite-аккаунты
автоматически не переносятся.

#### 3.6. Состояние, restart и логи

```powershell
docker @dc --profile work ps
docker @dc logs --tail 100 backend gateway
docker @dc restart backend gateway
```

В логах могут быть персональные данные; проверьте перед передачей другим.
`restart` не применяет новый image. После сборки обновите контейнеры так:

```powershell
docker @dc --profile work up -d backend gateway
```

#### 3.7. Остановка и повторный запуск

Остановка:

```powershell
docker @dc --profile work stop
```

В следующий раз сначала задайте `$dc` по разделу 3.2, затем:

```powershell
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

Данные хранятся в Docker volume: PostgreSQL `ishchi-local_pg-work`, Redis
`ishchi-local_redis-work`, медиа `ishchi-local_media`. **Не выполняйте `down -v`,
volume prune, reset или reseed рабочей базы.** Обычный stop/start сохраняет volume.

#### 3.8. Разрешения и миграции

Зафиксированное разрешение на повседневное использование рабочих PG/Redis
действует до **2026-11-24, 23:59 Asia/Tashkent**. Оно не разрешает тесты,
миграции, backup/restore и не переносится на другой компьютер. После истечения
нужно настоящее продление; не меняйте даты самостоятельно.

Миграции под runtime-логином запрещены. Нужны отдельный мигратор и overlay
`deploy/compose.local-roles.yml`. Не добавляйте автоматические миграции к обычному
старту. Подробности: [LOCAL_SAFETY.md](deploy/LOCAL_SAFETY.md),
[LOCAL.md](deploy/LOCAL.md#russian).

### 4. Просмотр собранного frontend

Из корня проекта:

```powershell
Set-Location frontend
npm run build
npm run preview -- --host 127.0.0.1
```

Откройте адрес из терминала, обычно порт `4173`. Остановка — `Ctrl+C`.
Для просмотра изменений нужна повторная сборка. В установленной версии Vite
preview наследует proxy-настройки сервера для `/api/` и `/media/`, направляя
запросы на `127.0.0.1:8001`. Для API/входа запустите SQLite-backend из раздела 2.2.
Preview не заменяет production hosting; для разработки используйте `npm run dev`.

### 5. Тесты и проверки — отдельно от запуска

Эти backend-тесты используют SQLite в памяти и не требуют рабочих PostgreSQL/
Redis. Из корня проекта:

```powershell
.\backend\.venv\Scripts\python.exe backend/manage.py check --settings=config.settings.testing
Set-Location backend
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

Frontend — в другом терминале из корня проекта:

```powershell
Set-Location frontend
npm test
npm run build
```

Интеграционные тесты PostgreSQL/Redis не входят в обычный запуск. Им нужны
отдельные тестовые базы, volume и разрешения. Не запускайте на рабочей базе.
Инструкции: [LOCAL.md](deploy/LOCAL.md#russian).

### 6. Решение проблем

- **Docker daemon/pipe не найден:** откройте Docker Desktop, дождитесь готовности
  и проверьте наличие контекста `desktop-linux`.
- **8080 не открывается:** проверьте backend и gateway командой
  `docker @dc --profile work ps`, затем readiness и логи.
- **API не работает на 5173:** Django должен работать на `127.0.0.1:8001`.
  Эта конфигурация Vite не подключается автоматически к Docker backend на `8080`.
- **Пароль admin не подходит:** сначала проверьте базу/порт: `8001` — SQLite,
  `8080` — Docker PostgreSQL. У одного номера в двух базах могут быть разные
  пароли и права. Повторные неверные попытки могут временно заблокировать вход.
- **SQLite: `no such table`:** выполните development-миграцию из раздела 2.2.
- **Нет категорий/заказов:** новый клон пуст либо открыта другая база. Не
  сбрасывайте и не заполняйте seed существующую рабочую базу.
- **Истёк допуск/ошибка оператора:** проверьте разрешение по
  [LOCAL_SAFETY.md](deploy/LOCAL_SAFETY.md); не обходите защиту.

`.env`, базы, пароли и медиа не распространяются через GitHub. Push кода
не запускает приложение и не переносит аккаунты между базами.

Документация: [README](README.md), [локальный Docker](deploy/LOCAL.md#russian),
[ежедневная работа](deploy/DAILY_USE.md), [backup/recovery](deploy/LOCAL_OPERATIONS.md),
[production](deploy/RUNBOOK.md).
