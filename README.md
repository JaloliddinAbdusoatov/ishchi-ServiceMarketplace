# ISHCHI marketplace

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

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
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

### Lokal o‘rnatish (PowerShell)

Python 3.14 va Node.js 24 LTS kerak. Klonlangan loyiha papkasida PowerShell ochib,
quyidagi buyruqlarni bajaring:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
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

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if (!(Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (!(Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
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
