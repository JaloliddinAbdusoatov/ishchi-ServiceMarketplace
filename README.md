# ISHCHI service marketplace

ISHCHI — ishchilar va buyurtmachilarni bog‘laydigan xizmatlar platformasi.
Yangi foydalanuvchilar uchun [o‘zbekcha o‘rnatish yo‘riqnomasi](#uzbek).

**Ishga tushirish usulini tanlang:** yangi klon uchun quyidagi SQLite + Vite
yo‘riqnomasi yetarli (Docker/PostgreSQL/Redis talab qilinmaydi). Docker’dagi lokal
PostgreSQL/Redis muhiti uchun [operator yo‘riqnomasi](deploy/LOCAL.md) mavjud;
undagi kompyuterga xos yo‘llar va avvalgi ruxsatlar yangi foydalanuvchiga
ko‘chmaydi. Production chiqarish talablari: [runbook](deploy/RUNBOOK.md).
Ommaviy serverga deploy bajarilmagan.

[O‘zbekcha](#uzbek) | [Русский](#russian) | [English](#english)

<a id="english"></a>

## English

The Django backend and React frontend are in `backend/` and `frontend/`.
See [current run instructions](PRODUCTION_MVP.md) for local startup and configuration.

Registration activates an account immediately without sending SMS.
The local frontend is at http://127.0.0.1:5173; the API is at http://127.0.0.1:8001.

This directory can be moved or copied as a standalone project. Its runtime and
tests do not require the parent repository. Keep `backend/`, `frontend/`, `deploy/`,
`.gitignore` and `PRODUCTION_MVP.md` together.

Local `.env`, databases, media, virtual environments and installed packages are
Git-ignored. For local data continuity, copy `backend/.local/` and any uploaded
media separately; keep those private. The Git repository root is this directory.

### Local setup (PowerShell)

Use Python 3.14 and Node.js 24 LTS. Open PowerShell in the cloned project
directory, then run:

First clone the repository with Git (the private repository requires access):

```powershell
git clone https://github.com/JaloliddinAbdusoatov/ishchi-marketplace.git
Set-Location ishchi-marketplace
```

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from django.core.management.utils import get_random_secret_key; p=Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY='+get_random_secret_key()+'\n'), encoding='utf-8')"
Set-Location frontend
npm ci
```

After moving the project, remove the copied `backend/.venv` before running setup,
then reinstall packages at the new location. A fresh clone also
needs migrations; an existing database keeps its accounts and marketplace data.
Local development uses SQLite and an in-process cache, without PostgreSQL or Redis.

Start the API in one terminal:

```powershell
# From the cloned project directory:
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

Start the frontend in another terminal:

```powershell
# From the cloned project directory:
Set-Location frontend
npm run dev
```

Open http://127.0.0.1:5173. API and media requests use Vite's proxy to port 8001.
The admin UI is at http://127.0.0.1:8001/django-admin/; create your own administrator
with `manage.py createsuperuser` if needed.

Fresh clones contain no accounts, categories or jobs. Register an employer and
worker yourself; create service categories in Django admin before publishing jobs.
There is no shared default login. Registration activates immediately; phone
verification and KYC are optional. SMS verification/password reset need a real
provider; SMS is disabled by default. Payments are disabled.

For fictional content in your own local SQLite database only, optionally run
`manage.py seed_marketplace --settings=config.settings.development` from the backend
virtual environment. It adds sample categories, profiles and jobs; generated users
have no usable passwords. Register your own accounts for interactive testing.

### Checks

From the project directory, run the backend checks against an isolated in-memory
SQLite database; no PostgreSQL or Redis service is needed:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.testing
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.testing
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

In a separate terminal, from the project directory:

```powershell
Set-Location frontend
npm ci
npm test
npm run build
npm audit
```

GitHub Actions runs these checks on pushes and pull requests. A successful local
test run covers SQLite development behavior; production integration and deployment
checks still require the release gates in `PRODUCTION_MVP.md`.

### Before publishing to GitHub

Publish this `ishchi/` directory. Review `git status --short` and `git diff --cached`
before committing. Keep `.env.example` and `.env.production.example` in Git;
keep actual `.env` files, `.local/`, media and credentials private. Frontend `VITE_`
variables are public and must never contain secrets.

Publishing source code does not deploy the application. Production variables and
the outstanding database/deployment gates are documented in
[PRODUCTION_MVP.md](PRODUCTION_MVP.md).

<a id="uzbek"></a>

## O‘zbekcha

ISHCHI — ishchilar va ish beruvchilar uchun xizmatlar platformasi.
Django backend `backend/`, React frontend esa `frontend/` papkasida joylashgan.
Lokal ishga tushirish, sozlash va production talablari
[PRODUCTION_MVP.md](PRODUCTION_MVP.md) hujjatida keltirilgan.

Ro‘yxatdan o‘tishda SMS yuborilmaydi, akkaunt darhol faollashadi.
Lokal frontend manzili: http://127.0.0.1:5173; API manzili:
http://127.0.0.1:8001.

Loyiha mustaqil papka sifatida ko‘chirilishi yoki nusxalanishi mumkin. Uni ishga
tushirish va testlash uchun ota repozitoriy talab qilinmaydi. `backend/`,
`frontend/`, `deploy/`, `.gitignore` va `PRODUCTION_MVP.md` fayllarini birga saqlang.

Lokal `.env`, ma’lumotlar bazalari, media, virtual muhit va o‘rnatilgan paketlar
Git tomonidan e’tiborga olinmaydi. Mavjud lokal ma’lumotlarni saqlash uchun
`backend/.local/` va yuklangan media fayllarini alohida, maxfiy tarzda ko‘chiring.
Git repozitoriysining ildizi — ushbu loyiha papkasi.

### Imkoniyatlar va loyiha tuzilishi

- Buyurtmachi: ish e’lon qilish, arizalarni ko‘rish, ishchini tanlash va ishni yakunlash.
- Ishchi: profil, xizmat kategoriyalari va portfolio; ishlarga ariza berish.
- Ishtirokchilar uchun chat va fayllar, bildirishnomalar, baholar va sharhlar.
- Administrator uchun foydalanuvchilar, kategoriyalar va shikoyatlarni boshqarish.
- O‘zbekcha, ruscha va inglizcha interfeys; telefon/parol orqali kirish, ixtiyoriy KYC.

`backend/` — Django REST API va testlar; `frontend/` — React/TypeScript/Vite
interfeysi va testlar; `deploy/` — Docker, lokal operatsiyalar va production
yo‘riqnomalari; `.github/workflows/` — avtomatik tekshiruvlar.

Ro‘yxatdan o‘tish uchun SMS shart emas. SMS orqali parol tiklash va telefonni
tasdiqlash uchun haqiqiy SMS provayderini sozlash kerak; standart sozlamada u
o‘chirilgan. To‘lov funksiyasi o‘chirilgan.

### Lokal o‘rnatish (PowerShell)

Python 3.14 va Node.js 24 LTS kerak. Klonlangan loyiha papkasida PowerShell ochib,
quyidagi buyruqlarni bajaring:

Avval Git orqali loyihani yuklab oling. Repozitoriy private bo‘lsa, egasidan
kirish huquqini olish va GitHub’da autentifikatsiya qilish kerak:

```powershell
git clone https://github.com/JaloliddinAbdusoatov/ishchi-marketplace.git
Set-Location ishchi-marketplace
```

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from django.core.management.utils import get_random_secret_key; p=Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY='+get_random_secret_key()+'\n'), encoding='utf-8')"
Set-Location frontend
npm ci
```

Loyihani boshqa joyga ko‘chirganda, ko‘chirilgan `backend/.venv` papkasini o‘chirib,
virtual muhitni yangi manzilda qayta yarating va paketlarni qayta o‘rnating.
Yangi klonda migratsiyalarni bajarish kerak; mavjud baza o‘z akkauntlari va
platforma ma’lumotlarini saqlaydi. Lokal ishlab chiqishda SQLite va jarayon
ichidagi kesh ishlatiladi; PostgreSQL yoki Redis kerak emas.

API’ni alohida terminalda ishga tushiring:

```powershell
# Klonlangan loyiha papkasidan:
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

Frontend’ni boshqa terminalda ishga tushiring:

```powershell
# Klonlangan loyiha papkasidan:
Set-Location frontend
npm run dev
```

Brauzerda http://127.0.0.1:5173 manzilini oching. API va media so‘rovlari Vite
proksisi orqali 8001-portga yuboriladi. Administrator paneli:
http://127.0.0.1:8001/django-admin/. Zarur bo‘lsa, backend papkasida o‘z
administrator akkauntingizni yarating:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.settings.development
```

### Birinchi foydalanish

1. Yangi klonda foydalanuvchi, kategoriya va buyurtmalar bo‘lmaydi. Yuqoridagi
   buyruq bilan administrator yarating, `/django-admin/` panelida xizmat
   kategoriyalarini qo‘shing.
2. Saytda buyurtmachi sifatida ro‘yxatdan o‘ting va ish e’lon qiling. Akkaunt SMS’siz
   darhol faollashadi.
3. Boshqa brauzer yoki maxfiy oynada ishchi akkauntini yarating. Profil va xizmat
   kategoriyalarini to‘ldiring, e’longa ariza yuboring.
4. Buyurtmachi arizani qabul qilgach, ishtirokchilar chatdan foydalanadi. Ish
   tugagach, yakunlash va sharh qoldirish jarayonini tekshiring.

Umumiy standart login/parol yo‘q. O‘z akkauntlaringizni yarating. Faqat o‘zingizning
lokal SQLite bazangizni misollar bilan to‘ldirish kerak bo‘lsa, backend papkasida
quyidagi **ixtiyoriy** buyruqni bajaring:

```powershell
.\.venv\Scripts\python.exe manage.py seed_marketplace --settings=config.settings.development
```

Bu buyruq sun’iy kategoriyalar, profillar va ishlarni qo‘shadi; yaratilgan
foydalanuvchilarda kirish uchun yaroqli parol bo‘lmaydi. Saytda o‘z akkauntingizni
alohida yarating. Bu usul Docker’dagi PostgreSQL muhiti uchun mo‘ljallanmagan.

### Qayta ishga tushirish va tez-tez uchraydigan muammolar

- To‘xtatish: backend va frontend terminallarida `Ctrl+C`. Qayta ochishda faqat
  ikkala serverni ishga tushiring; paketlarni qayta o‘rnatish yoki seed qilish shart emas.
- `python` yoki `npm` topilmasa, kerakli versiyalarni o‘rnating va terminalni qayta oching.
- `npm ci` uchun Node.js 24 ishlating. Python buyruqlarida `backend/.venv` ichidagi
  interpreterdan foydalaning; virtual muhitni aktivlashtirish majburiy emas.
- API bilan aloqa bo‘lmasa, backend `127.0.0.1:8001` da ishlayotganini tekshiring.
  Frontend uchun `http://127.0.0.1:5173` ni oching va ikkala terminalni ochiq qoldiring.
- `no such table` xatosida SQLite uchun yuqoridagi `migrate` buyrug‘ini bajaring.
- Kategoriyalar bo‘sh bo‘lsa, administrator orqali qo‘shing yoki o‘z lokal
  SQLite bazangizda ixtiyoriy namunaviy ma’lumot buyrug‘idan foydalaning.
- `backend/.local/` ichida baza va media saqlanadi; uni o‘chirish lokal
  ma’lumotlarni yo‘qotadi. `.env` va shaxsiy fayllarni GitHub’ga yuklamang.

### Docker va qo‘shimcha hujjatlar

Yuqoridagi SQLite muhiti bilan Docker’dagi `http://127.0.0.1:8080` muhiti
alohida bazalardan foydalanadi; akkauntlar avtomatik ko‘chmaydi. Docker operatori
o‘z maxfiy sozlamalari va aniq xizmat ruxsatlarini tayyorlashi kerak. GitHub’dan
klonlash mavjud operator ruxsatlarini bermaydi.

- [Docker lokal muhiti](deploy/LOCAL.md), [kundalik foydalanish](deploy/DAILY_USE.md).
- [Lokal xavfsizlik holati](deploy/LOCAL_SAFETY.md), [backup va recovery](deploy/LOCAL_OPERATIONS.md).
- [Production konfiguratsiyasi](PRODUCTION_MVP.md), [deploy runbook](deploy/RUNBOOK.md).
- [Bajarilgan ishlar hisoboti](DEMO_TO_PRODUCTION_MVP_REPORT_UZ.md) va
  [Sprint 1](SPRINT_1.md), [Sprint 2](SPRINT_2.md), [Sprint 3](SPRINT_3.md).

Tarixiy hisobotlardagi test sonlari va sanalar o‘sha tekshiruvlarga tegishli;
eng so‘nggi natijani GitHub Actions’da tekshiring. GitHub’ga push qilish serverga
deploy qilmaydi; production TLS, hosting va tashqi integratsiyalar alohida tekshiriladi.

### Tekshiruvlar

Loyiha papkasidan backend tekshiruvlarini bajaring. Testlar xotiradagi alohida
SQLite bazasida ishlaydi; PostgreSQL va Redis xizmatlari talab qilinmaydi:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.testing
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.testing
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

Boshqa terminalda loyiha papkasidan frontend tekshiruvlarini bajaring:

```powershell
Set-Location frontend
npm ci
npm test
npm run build
npm audit
```

GitHub Actions bu tekshiruvlarni push va pull request vaqtida avtomatik bajaradi.
Lokal testlar SQLite bilan ishlashni tekshiradi. Production integratsiyasi va
deploy tekshiruvlari uchun `PRODUCTION_MVP.md` dagi chiqarish shartlarini
bajarish kerak.

### GitHub’ga chiqarish

Ushbu `ishchi/` papkasini repozitoriy sifatida yuklang. Commit qilishdan oldin
`git status --short` va `git diff --cached` natijalarini ko‘rib chiqing.
`.env.example` va `.env.production.example` shablonlarini Git’da saqlang.
Haqiqiy `.env`, `.local/`, media va kirish ma’lumotlarini maxfiy saqlang.
Frontend’dagi `VITE_` o‘zgaruvchilari foydalanuvchiga ko‘rinadi; ularga maxfiy
kalitlarni yozmang.

Kodni GitHub’ga yuklash ilovani serverga deploy qilmaydi. Production
o‘zgaruvchilari hamda ma’lumotlar bazasi va deploy bo‘yicha qolgan talablar
[PRODUCTION_MVP.md](PRODUCTION_MVP.md) hujjatida yozilgan.

<a id="russian"></a>

## Русский

ISHCHI — платформа услуг для работников и работодателей.
Серверная часть на Django находится в `backend/`, клиентская часть на React —
в `frontend/`. Инструкции по локальному запуску, настройке и требованиям
к production приведены в [PRODUCTION_MVP.md](PRODUCTION_MVP.md).

При регистрации аккаунт активируется сразу, без отправки SMS.
Локальный адрес фронтенда: http://127.0.0.1:5173; адрес API:
http://127.0.0.1:8001.

Проект можно переносить или копировать как самостоятельную папку. Для запуска
и тестирования родительский репозиторий не требуется. Сохраняйте вместе
`backend/`, `frontend/`, `deploy/`, `.gitignore` и `PRODUCTION_MVP.md`.

Локальные `.env`, базы данных, медиафайлы, виртуальные окружения и установленные
пакеты исключены из Git. Чтобы сохранить локальные данные при переносе,
скопируйте `backend/.local/` и загруженные медиафайлы отдельно и храните их
конфиденциально. Корень Git-репозитория — текущая папка проекта.

### Локальная установка (PowerShell)

Нужны Python 3.14 и Node.js 24 LTS. Откройте PowerShell в папке клонированного
проекта и выполните:

Сначала клонируйте проект (для private-репозитория нужен доступ):

```powershell
git clone https://github.com/JaloliddinAbdusoatov/ishchi-marketplace.git
Set-Location ishchi-marketplace
```

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
.\backend\.venv\Scripts\python.exe -c "from pathlib import Path; from django.core.management.utils import get_random_secret_key; p=Path('backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY='+get_random_secret_key()+'\n'), encoding='utf-8')"
Set-Location frontend
npm ci
```

После переноса проекта удалите скопированную папку `backend/.venv`, создайте
виртуальное окружение по новому пути и установите пакеты заново. Для нового
клона необходимо выполнить миграции; существующая база сохраняет аккаунты
и данные платформы. Локальная разработка использует SQLite и кеш внутри
процесса, без PostgreSQL и Redis.

Запустите API в отдельном терминале:

```powershell
# Из папки клонированного проекта:
Set-Location backend
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings.development
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001 --settings=config.settings.development
```

Запустите фронтенд в другом терминале:

```powershell
# Из папки клонированного проекта:
Set-Location frontend
npm run dev
```

Откройте http://127.0.0.1:5173 в браузере. Запросы к API и медиафайлам
перенаправляются прокси Vite на порт 8001. Панель администратора доступна по
адресу http://127.0.0.1:8001/django-admin/. При необходимости создайте собственный
аккаунт администратора из папки backend:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.settings.development
```

### Первое использование

В новом клоне нет пользователей, категорий и заказов. Создайте категории через
Django admin и зарегистрируйте собственные аккаунты заказчика и работника.
Общего логина/пароля нет. Регистрация активирует аккаунт сразу; проверка телефона
и KYC необязательны. SMS по умолчанию отключены; восстановление пароля через SMS
требует настоящего провайдера. Платежи отключены. Docker-инструкции для отдельной
локальной среды: [LOCAL.md](deploy/LOCAL.md); настройки и разрешения прежнего
оператора не переносятся в новый клон.

### Проверки

Из папки проекта выполните проверки backend. Тесты используют отдельную базу
SQLite в памяти; сервисы PostgreSQL и Redis не нужны:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.testing
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.testing
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.testing
```

В другом терминале, из папки проекта, выполните проверки frontend:

```powershell
Set-Location frontend
npm ci
npm test
npm run build
npm audit
```

GitHub Actions автоматически выполняет эти проверки при push и pull request.
Локальные тесты проверяют работу с SQLite. Для production-интеграции и deploy
необходимо выполнить условия выпуска, описанные в `PRODUCTION_MVP.md`.

### Публикация на GitHub

Публикуйте текущую папку `ishchi/` как репозиторий. Перед коммитом просмотрите
результаты `git status --short` и `git diff --cached`. Храните шаблоны
`.env.example` и `.env.production.example` в Git. Настоящие `.env`, `.local/`,
медиафайлы и учётные данные должны оставаться конфиденциальными.
Переменные frontend с префиксом `VITE_` доступны пользователям; они не должны
содержать секретные ключи.

Публикация исходного кода на GitHub не развёртывает приложение на сервере.
Production-переменные и оставшиеся требования к базе данных и развёртыванию
описаны в [PRODUCTION_MVP.md](PRODUCTION_MVP.md).
