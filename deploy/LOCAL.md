# Local ISHCHI — running on the owner's computer

[O‘zbekcha](#uzbek) | [Русский](#russian) | [English](#english)

> Historical setup and verification record: dates and test counts describe the
> recorded runs. For later approval, security and recovery updates, see
> [LOCAL_SAFETY.md](LOCAL_SAFETY.md) and [LOCAL_OPERATIONS.md](LOCAL_OPERATIONS.md).
> Machine-specific paths and approvals do not transfer to another clone.

<a id="english"></a>

## English

Status: `LOCAL_MVP_RUNNING_VERIFIED` (2026-11-16).

Owner explicitly approved the exact new test and working targets/operations in
chat, through **2026-11-17 23:59 Asia/Tashkent** (18:59 UTC). New dedicated clusters
were provisioned, current migrations applied and runtime checks passed.
`ishchi_test` and existing unrelated databases/Redis were not accessed. No backup,
restore, working-data reset or real-user deletion ran. Production remains blocked.
Open **http://127.0.0.1:8080**; no public domain/TLS is needed.

**Current safety status:** the synthetic administrator credential is treated as
exposed. Owner-approved password/JWT rotation completed with PASS on November 16;
new login and old-token/session rejection passed. Old-password login rejection
was NOT RUN because the previous password was unknown. File-backed administrator
login/bootstrap in the live verifier
is retired. See [daily data safety procedures and actual checks](LOCAL_SAFETY.md).

Daily working PG/Redis use was explicitly renewed through **2026-11-24 23:59
Asia/Tashkent**; mounted interlocks and readiness passed. Test/migration scopes
retain their original expiry and are not renewed. Role/audit corrections and a
real isolated encrypted-backup restore have now passed under separate one-time
approval through November 17, 23:59. Overall security status is
`LOCAL_SECURITY_PARTIAL`; see the remaining owner actions in LOCAL_SAFETY.md.

## Approved exact targets

- Working PostgreSQL: `127.0.0.1:55432`, DB `ishchi_marketplace_local`, non-superuser
  `ishchi_local_app`; new `ishchi-local_pg-work` volume.
- Disposable PostgreSQL: `127.0.0.1:55433`, DB `ishchi_marketplace_sprint1_local`,
  non-superuser `ishchi_local_test`; separate `ishchi-local_pg-test` volume.
- Working Redis: `127.0.0.1:56379`, DB 0, ACL user `ishchi_local_app`, keys
  `ishchi:local:work:*`; separate persistent AOF volume `ishchi-local_redis-work`.
- Test Redis: `127.0.0.1:56380`, DB 0, ACL user `ishchi_local_test`, keys
  `ishchi-sprint2-*`; separate `ishchi-local_redis-test` volume and network.
- App: `http://127.0.0.1:8080`; nginx serves React/static/public profile images and
  proxies API/admin to private loopback Gunicorn. Order/chat media remains private.

The recorded owner approval specifies these targets, roles, operations and expiry. Provisioning
includes initializing **new dedicated clusters**, creating their bootstrap
superuser `ishchi_bootstrap`, databases/non-superuser roles, and restricting default
postgres/template1 CONNECT privileges inside those new clusters only. Test approval
must also cover migrations, reverse/reapply, synthetic writes/fixture flushing and
temporary test-media deletion. Working approval covers persistent app reads/writes
and separately controlled migrations. Redis approval covers security operations
and test namespace SCAN/DEL cleanup, never FLUSHDB/FLUSHALL. Runtime keys/volumes
are never shared with tests. No legacy DB, role or SQL proposal is imported.

JSON interlocks, generated passwords, names and environment variables are not
approval. These commands were executed only after the explicit owner consent;
future use must stay within its targets/scopes/expiry. Existing project data now
belongs to this approved local app: do not reset/adopt other volumes or targets.
PostgreSQL initialization
scripts run only on empty volumes; they never rotate/reset an existing cluster.

## Initial configuration preparation (already completed; do not regenerate secrets)

From `D:\Project\ishchi`:

```powershell
.\backend\.venv\Scripts\python.exe deploy/local.py check
.\backend\.venv\Scripts\python.exe deploy/local.py init-secrets --directory C:/Users/user/.codex/ishchi-local-private
Copy-Item deploy/.env.local.example deploy/.env.local
```

Set `LOCAL_SECRETS_DIR` in `.env.local` to that absolute directory. Secret generation
refuses overwrites, generates different work/test/bootstrap credentials and a
`local.pgpass`, and writes **blank expired** interlock templates. It does not grant
authority or create databases. Keep the directory private with host ACLs; Windows
chmod is not an ACL guarantee. Mounts must be readable by their container processes
(backend UID 10001); never solve this by publishing secrets. Do not print Compose
configuration/env/credentials or commit `.env.local`/the private directory.

After real approval, an authorized operator records the exact approved target,
scopes and future UTC expiry in the corresponding interlocks. Work DB runtime file
has only `connect`; the separate migration file also needs `local_migrate`. Test DB
requires `connect` + `test_schema` and disposable=true. Work Redis needs `cache`;
test Redis needs `cache` + `cache_test`, disposable=true. Container work targets in
the templates are `postgres-work:5432` / `redis-work:6379`; host test targets are
the loopback endpoints above. Never substitute working credentials into tests.

Local settings deliberately allow plaintext DB/Redis only on these exact loopback/
private Docker endpoints. Host ports bind only 127.0.0.1; separate bridge networks
also default publication to loopback. They allow outbound traffic (not an egress
firewall). Production still requires verified TLS and remains blocked. DEBUG=false,
no seed/demo endpoints, real phone/password/JWT auth, optional KYC and disabled
payments are preserved. SMS is disabled by default; optional verification/reset
requires a separately configured real HTTP provider, never a synthetic OTP.

## Startup/shutdown commands within the approval period

Use this command prefix in PowerShell (selects local Docker Desktop only):

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker @dc config --quiet
docker @dc build backend gateway
```

The following test commands already passed. They are preserved for reproducibility:

```powershell
docker @dc --profile test up -d postgres-test redis-test
.\backend\.venv\Scripts\python.exe deploy/local.py pg-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
.\backend\.venv\Scripts\python.exe deploy/local.py redis-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
```

The launcher clears inherited DB/Redis/libpq targets and selects exact local test
settings. PG tests use process-local cache; Redis tests use in-memory SQLite user
fixtures. PG leaves its schema, so reruns need a separately approved disposable
reset/new target. No automatic reset, cloning, --reuse-db or --create-db is supplied.

Working provisioning/migrations were previously completed. Ordinary startup is:

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
```

Current source prohibits migrations under the runtime login before connection.
Future migrations use the approved dedicated migrator and private secret with
the `deploy/compose.local-roles.yml` overlay. The role/ownership change is applied;
operator migrate-check passed. Its one-time approval/login validity ends November
17 at 23:59 Tashkent; later migration work requires separate genuine renewal.
Do not use the old runtime migrate command or create an administrator on startup.

An explicit one-time synthetic verification administrator was created through
Django's normal manager, not application startup. Treat its original credential
as exposed: do not use the old plaintext file for operational authentication.
Use the separately approved interactive rotation procedure in LOCAL_SAFETY.md.
No administrator is automatically bootstrapped by the verifier anymore.
Open `http://127.0.0.1:8080`, admin `/django-admin/`, and verify
`/api/v1/health/ready/` returns 200. Then check real registration/login, profiles/
categories, publication, applications/invitations, capacity/hiring, authorized chat,
notifications, completion/reviews and payments-disabled behavior. Existing users
and media are retained; never reseed/reset the working target. For future static
asset updates run an explicitly approved `collectstatic` against the static volume.

Normal stop/start preserves data and never removes volumes:

```powershell
docker @dc --profile work stop
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

Do not use `down -v`, volume prune, destructive reseeding or restore on working DB.
Redis AOF uses every-second fsync; keep data volumes and JWT secret stable. After
Redis state loss, keep traffic closed until sessions/revocations are reconciled.

## Backup preparation

`deploy/local.py backup-plan --destination <existing-private-directory> --recipient
<owner-age-public-recipient>` prints an **inert** encrypted pg_dump/age plan for
working localhost:55432 only. Set its PGPASSFILE to the generated private
`local.pgpass`; never put the password in command arguments. Coordinate DB/media
snapshots, stream encryption before persistent output and check both exit codes.
The existing `ops.py plan-media-backup` remains planner-only.

`deploy/local.py restore-plan --archive <encrypted-dump> --identity-file
<owner-private-key>` can only propose `127.0.0.1:55434`, DB
`ishchi_marketplace_restore_local`, role `ishchi_local_restore`. That separate
empty target is **not provisioned** by Compose and needs independent approval.
Never restore over working DB/media. Check archive provenance, data/ACL/application
compatibility and a current independent erasure ledger before traffic; completed
outbox tasks alone cannot identify all previously erased keys. Backup, restore,
media recovery, RPO and RTO remain **NOT VERIFIED**; no backup pipeline ran.

## Actual validation and remaining limits

- PASS: 269 backend tests, including local isolation/production-gate regressions
  and Windows smoke-process cleanup; the latter fixes an observed locked-log
  teardown failure by stopping the owned venv interpreter tree.
- PASS: 18 frontend tests/build; both local Docker images built; local nginx `-t`,
  bootstrap shell syntax checks, existing network-isolated production-guard smoke
  on those images, and SQLite-only loopback HTTP smoke.
- PASS: Compose configuration and local isolation checks; Django/drift/pip checks.
- PASS: **34/34 PostgreSQL integration cases** against the approved disposable
  PostgreSQL 18.6 target; full migrations, `orders/0004`, `common/0001`, reverse/
  reapply, hiring concurrency, commit/audit rollback and media-outbox retry.
- PASS: **8/8 Redis integration cases** against the approved isolated Redis 7.4.12
  target. This deliberate localhost profile uses authenticated plaintext; it is
  not evidence of production TLS. Outage is transport-failure injection, not a
  physical server outage. Namespace cleanup uses SCAN/DEL, never FLUSH.
- PASS: full current migrations on the separate working database; backend,
  gateway and dependencies healthy; readiness reports PostgreSQL/Redis ok.
- PASS: actual HTTP through nginx/React assets: real admin login, registration/
  login for employer and three workers, optional phone/KYC, profiles/categories,
  publication, duplicate/capacity rejection, two-worker hiring, invitations,
  authorized chat/notifications, completion/review uniqueness and revocation.
  Two completed synthetic jobs and their synthetic accounts are retained. No
  fixture flushing/reset occurred in the working database. The Uzbek React
  landing page was also verified visually in a browser with live server metrics.
- Fixed after first runtime attempt: Docker Desktop suppressed host publication
  for `internal` networks, causing initial PG/Redis connection failures. Separate
  loopback-publishing bridges corrected this; both suites then passed in full.
- NOT RUN: backup/restore/recovery and real SMS; no verified RPO/RTO. Production
  trust authority, TLS/hosting, role separation and append-only DB audit ACLs are
  still outside this local verification. No public production readiness claim.
- Approval expires **2026-11-17 23:59 Tashkent**. Existing connection interlocks fail
  closed after expiry; obtain explicit renewal before further access. Do not
  silently extend files or regenerate passwords/JWT keys. Test reruns still need
  an empty separately approved/reset disposable schema; no automatic reset exists.

The reusable live verifier is `deploy/verify_local.py --allow-synthetic-writes`.
It requires separate approval, interactive credentials and creates NEW synthetic
data. Legacy `--credentials` and `--bootstrap-admin` fail before reading files or
accessing the application. It was not rerun during stabilization. Evidence without
passwords/tokens is in `deploy/.local/live-verification.json`; PG output is in
`deploy/.local/postgres-tests.log` (both intentionally ignored by Git).

- Cleanup note: an earlier synthetic smoke directory
  `C:\Users\user\AppData\Local\Temp\ishchi-http-smoke-7u273vj0` remains because
  automatic approval review rejected its recursive deletion ("blocked by policy").
  Subsequent smoke execution passed and removed its own new fixtures.

PostgreSQL 18 volume layout and empty-volume initialization follow the
[official image](https://hub.docker.com/_/postgres). Redis role/key scoping follows
the [Redis ACL documentation](https://redis.io/docs/latest/manual/security/acl/).

---

<a id="uzbek"></a>

## O‘zbekcha — lokal Docker muhitida ishlatish

### Muhit va holat

Bu yo‘riqnoma loyiha egasining kompyuterida tayyorlangan Docker muhiti uchun.
Yangi foydalanuvchilar avval [README](../README.md) bilan tanishsin. Undagi
Docker’siz SQLite muhiti bu yerdagi PostgreSQL muhitidan alohida: akkauntlar va
ma’lumotlar avtomatik ko‘chmaydi. Quyidagi kompyuterga xos yo‘llar va avvalgi
ruxsatlar yangi klon yoki boshqa foydalanuvchiga ko‘chmaydi.

Sayt: **http://127.0.0.1:8080**. Lokal ish uchun ommaviy domen/TLS kerak emas.
Production’ga chiqarish alohida talablar va tekshiruvlarga bog‘liq.

Docker Desktop’ning Linux konteynerlari va `desktop-linux` konteksti ishlatiladi.
Backend/frontend konteynerlarda ishlaydi. Quyidagi Python yordamchi buyruqlari
uchun esa hostdagi `backend/.venv` va README bo‘yicha o‘rnatilgan paketlar kerak.

Asl holat `LOCAL_MVP_RUNNING_VERIFIED` — 2026-11-16. Ushbu hujjatdagi sanalar va
test sonlari o‘sha tekshiruvlarga tegishli; tarjima qo‘shishda xizmatlar qayta
tekshirilmadi. Dastlab yangi ishchi/test targetlari va amallar **2026-11-17,
23:59 Asia/Tashkent** (18:59 UTC) gacha tasdiqlangan. Alohida klasterlar yaratilgan,
migratsiyalar qo‘llangan. `ishchi_test` va aloqasiz bazalar/Redis ishlatilmagan,
ishchi ma’lumotlar reset qilinmagan.

Keyin faqat kundalik ishchi PostgreSQL/Redis ruxsati **2026-11-24, 23:59
Asia/Tashkent** gacha uzaytirilgan. Test/migratsiya scope’lari uzaytirilmagan.
Rol/audit tuzatishlari va shifrlangan backup’ni alohida muhitda tiklash boshqa
bir martalik ruxsat doirasida tekshirilgan. Xavfsizlik holati:
`LOCAL_SECURITY_PARTIAL`. Dolzarb ma’lumotlar [LOCAL_SAFETY.md](LOCAL_SAFETY.md)
va [LOCAL_OPERATIONS.md](LOCAL_OPERATIONS.md) da; pastdagi inglizcha tarixiy
ro‘yxatning backup/restore tekshirilmagan degan bandi keyingi holatni aks ettirmaydi.

Administratorning dastlabki sinov credential’i oshkor bo‘lgan deb hisoblanadi.
Parol/JWT rotatsiyasi, yangi kirish va eski token/session rad etilishi tekshirilgan;
eski parol noma’lum bo‘lgani uchun u bilan kirishni rad etish sinovi bajarilmagan.
Eski ochiq matnli fayldan login qilmang. Verifier’da fayl orqali kirish va
avtomatik admin yaratish bekor qilingan. Rotatsiyani faqat sinovni qaytarish
uchun takrorlamang; [xavfsizlik yo‘riqnomasi](LOCAL_SAFETY.md)ga amal qiling.

### Xizmatlar va ma’lumotlar

- Ishchi PostgreSQL: `127.0.0.1:55432`, baza `ishchi_marketplace_local`, oddiy rol
  `ishchi_local_app`, volume `ishchi-local_pg-work`.
- Test PostgreSQL: `127.0.0.1:55433`, baza `ishchi_marketplace_sprint1_local`,
  oddiy rol `ishchi_local_test`, alohida volume `ishchi-local_pg-test`.
- Ishchi Redis: `127.0.0.1:56379`, DB 0, ACL user `ishchi_local_app`, kalitlar
  `ishchi:local:work:*`, doimiy AOF volume `ishchi-local_redis-work`.
- Test Redis: `127.0.0.1:56380`, DB 0, ACL user `ishchi_local_test`, kalitlar
  `ishchi-sprint2-*`, alohida volume `ishchi-local_redis-test` va tarmoq.
- Nginx React, statik fayllar va ochiq profil rasmlarini beradi; API/admin’ni
  xususiy loopback Gunicorn’ga uzatadi. Buyurtma/chat fayllari yopiq qoladi.

Bootstrap superuser `ishchi_bootstrap`, bazalar va oddiy rollar faqat yangi
ajratilgan klasterlarda yaratilgan; `postgres`/`template1` CONNECT huquqlari ham
faqat shu klasterlarda cheklangan. Eski baza/rol/SQL takliflari import qilinmaydi.
Ishchi va test credential, kalit va volume’larini almashtirmang.

JSON ruxsat fayli, parol yoki env o‘zgaruvchisi o‘z-o‘zidan egasining roziligi
emas. Har bir amal aniq target, scope va muddatga mos bo‘lishi kerak. Test ruxsati
migratsiya, orqaga/qayta qo‘llash, sun’iy yozuvlar, fixture va vaqtinchalik media
tozalashni qamrashi kerak. Redis test tozalashi faqat o‘z namespace’ida SCAN/DEL;
FLUSHDB/FLUSHALL taqiqlangan. Boshqa bazalarni ulab yubormang yoki reset qilmang.
PostgreSQL init skriptlari faqat bo‘sh volume’da ishlaydi, mavjud klasterni
reset qilmaydi va uning parollarini almashtirmaydi.

### Dastlabki tayyorgarlik — mavjud muhitda qayta bajarmang

Quyidagi ishlar mavjud kompyuterda allaqachon bajarilgan. Mavjud kalit/parollarni
qayta yaratmang. Buyruqlar loyiha ildizidan (`D:\Project\ishchi`) bajarilgan:

```powershell
.\backend\.venv\Scripts\python.exe deploy/local.py check
.\backend\.venv\Scripts\python.exe deploy/local.py init-secrets --directory C:/Users/user/.codex/ishchi-local-private
Copy-Item deploy/.env.local.example deploy/.env.local
```

Yangi operator o‘z maxfiy papka yo‘lini tanlaydi; `.env.local` ichidagi
`LOCAL_SECRETS_DIR` shu papkaning absolyut yo‘li bo‘lishi kerak. Generator
mavjud fayllarni ustidan yozmaydi; turli ishchi/test/bootstrap credential’lari,
`local.pgpass` va **bo‘sh, muddati o‘tgan** ruxsat shablonlarini yaratadi. U baza
yaratmaydi yoki ruxsat bermaydi. Maxfiy papkani host ACL bilan himoyalang;
Windows’da `chmod` ACL kafolati emas. Konteyner jarayonlari, jumladan backend UID
10001, kerakli fayllarni o‘qiy olishi kerak. Buning uchun sirlarni ommaga ochmang.
Compose’ning to‘liq konfiguratsiyasi/env/credential’larini chiqarmang;
`.env.local` va maxfiy papkani Git’ga qo‘shmang.

Haqiqiy rozilikdan keyin operator target, scope va kelajak UTC tugash muddatini
ruxsat fayllarida qayd etadi. Ishchi DB runtime: `connect`; alohida migrator:
qo‘shimcha `local_migrate`; test DB: `connect` + `test_schema`, `disposable=true`;
ishchi Redis: `cache`; test Redis: `cache` + `cache_test`, `disposable=true`.
Konteyner ichidagi ishchi manzillar: `postgres-work:5432`, `redis-work:6379`.

Plaintext DB/Redis faqat aniq loopback/xususiy Docker manzillarida ruxsat etilgan;
host portlari `127.0.0.1` ga bog‘langan. Bridge tarmoqlar tashqariga chiqishni
to‘suvchi firewall emas. Production tasdiqlangan TLS talab qiladi. `DEBUG=false`,
haqiqiy telefon/parol/JWT, ixtiyoriy KYC, o‘chirilgan to‘lovlar va seed/demo
endpointlarining yo‘qligi saqlanadi. SMS standart holatda o‘chiq; telefonni
tasdiqlash/parol tiklash uchun haqiqiy HTTP provayder kerak, sun’iy OTP emas.

### Oddiy ishga tushirish va to‘xtatish

Tayyorlangan muhit va amaldagi ruxsat bo‘lishi shart. PowerShell’da loyiha
ildizidan bajaring. Har bir yangi terminalda `$dc` ni qayta belgilang:

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker @dc config --quiet
docker @dc build backend gateway
```

Ishchi baza va migratsiyalar oldindan tayyor bo‘lsa:

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
```

Sayt: **http://127.0.0.1:8080**; admin: **http://127.0.0.1:8080/django-admin/**.
`/api/v1/health/ready/` 200 qaytarishi kerak. Ro‘yxatdan o‘tish/kirish, profil,
kategoriyalar, e’lon, ariza/taklif, sig‘im/ishchini tanlash, chat, bildirishnoma,
yakunlash/sharh va to‘lovlar o‘chirilganini tekshiring.

Ma’lumotlarni saqlagan holda to‘xtatish/qayta ishga tushirish:

```powershell
docker @dc --profile work stop
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

**`down -v`, volume prune, ishchi bazani seed/reset yoki uning ustiga restore
qilmang.** Mavjud foydalanuvchi va media saqlanadi. Volume va JWT kalitini
saqlang. Redis AOF har soniyada fsync qiladi; Redis holati yo‘qolsa,
session/revocation holati muvofiqlashtirilmaguncha trafikni ochmang.

Runtime login orqali migratsiya ulanishdan oldin bloklanadi. Migratsiyalar uchun
alohida tasdiqlangan migrator, xususiy secret va `deploy/compose.local-roles.yml`
overlay’i kerak. Qayd etilgan migrator ruxsati/login muddati 2026-11-17, 23:59
Toshkentda tugaydi; keyingi ish uchun alohida uzaytirish zarur. Start paytida admin
yaratmang. `collectstatic` ham tegishli static volume’da alohida tasdiqlanadi.

### Testlarni qayta bajarish

Oddiy start uchun bu buyruqlar kerak emas. Ular tarixiy testlarni takrorlash uchun;
test scope’i va bo‘sh/alohida target bo‘yicha amaldagi ruxsat talab qilinadi:

```powershell
docker @dc --profile test up -d postgres-test redis-test
.\backend\.venv\Scripts\python.exe deploy/local.py pg-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
.\backend\.venv\Scripts\python.exe deploy/local.py redis-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
```

Launcher meros DB/Redis/libpq targetlarini tozalab, aniq lokal sozlamalarni tanlaydi.
PG testlari jarayon ichidagi keshdan, Redis testlari xotiradagi SQLite fixture’dan
foydalanadi. PG sxemasi qoladi: qayta sinov uchun alohida tasdiqlangan disposable
reset yoki yangi target zarur. Avtomatik reset/klonlash, `--reuse-db`, `--create-db`
yo‘q. Ishchi credential’larni testga bermang.

### Backup va tiklash

`deploy/local.py backup-plan --destination <existing-private-directory> --recipient
<owner-age-public-recipient>` ishchi localhost:55432 uchun pg_dump/age **rejasini
chiqaradi**, backup’ni bajarmaydi. `PGPASSFILE` xususiy `local.pgpass` ga
yo‘naltiriladi; parol argumentga yozilmaydi. DB/media snapshot’lari muvofiqlashtirilib,
diskka saqlashdan oldin oqim shifrlanadi; ikkala exit kod tekshiriladi.
`ops.py plan-media-backup` ham faqat reja beradi.

`deploy/local.py restore-plan --archive <encrypted-dump> --identity-file
<owner-private-key>` faqat `127.0.0.1:55434`, `ishchi_marketplace_restore_local`,
`ishchi_local_restore` targetini taklif qiladi. Compose uni yaratmaydi; alohida
bo‘sh target va mustaqil ruxsat kerak. Ishchi DB/media ustiga tiklamang. Trafikdan
oldin arxiv kelib chiqishi, data/ACL/ilova mosligi va dolzarb mustaqil o‘chirish
reyestrini tekshiring. Tugallangan outbox’ning o‘zi barcha avval o‘chirilgan
fayllarni aniqlamaydi. Keyingi amaliy recovery natijalari:
[LOCAL_OPERATIONS.md](LOCAL_OPERATIONS.md). Avtomatik backup jadvali yoqilgan deb
hisoblamang.

### Tarixiy tekshiruv natijalari va cheklovlar

Asl hisobot: 269 backend, 18 frontend testi/build; ikkala Docker image build’i,
nginx/shell konfiguratsiyasi, tarmoqdan ajratilgan production himoya smoke’i,
SQLite HTTP smoke’i, Compose izolyatsiyasi, Django/drift/pip tekshiruvlari o‘tgan.
PostgreSQL 18.6 da 34/34 test: migratsiyalar, `orders/0004`, `common/0001`,
orqaga/qayta qo‘llash, parallel hiring, commit/audit rollback va media-outbox retry.
Redis 7.4.12 da 8/8 test o‘tgan. Bu plaintext lokal aloqa production TLS isboti
emas; uzilish transport xatosi bilan modellashtirilgan, server o‘chirilmagan.

Ishchi readiness va HTTP oqimlari tekshirilgan: admin, buyurtmachi/uch ishchi,
ixtiyoriy telefon/KYC, profil/kategoriya, e’lon, takroriy/sig‘im cheklovi,
ikki ishchini tanlash, taklif, chat/bildirishnoma, yakunlash/sharh va revocation.
Ikki sun’iy yakunlangan ish va akkauntlar saqlangan, ishchi bazada flush/reset
bo‘lmagan; o‘zbekcha bosh sahifa brauzerda real metrikalar bilan ko‘rilgan.
Dastlab `internal` Docker tarmoqlari host portlarini chiqarmagan; loopback bridge
tarmoqlari bilan tuzatilgach ikkala integratsion suite o‘tgan.

Haqiqiy SMS, public hosting/TLS va production talablari bu lokal tekshiruv bilan
tasdiqlanmaydi. Ruxsat muddati tugaganda kirish bloklanadi; muddatni yashirin
uzaytirmang yoki parol/JWT’ni qayta yaratmang. Keyingi rol/audit/backup holati
uchun yuqoridagi dolzarb hujjatlarga qarang.

`deploy/verify_local.py --allow-synthetic-writes` alohida ruxsat va interaktiv
credential talab qiladi, **yangi** sun’iy yozuvlar yaratadi. `--credentials` va
`--bootstrap-admin` fayl o‘qish/ilovaga kirishdan oldin rad etiladi. Verifier
stabilization vaqtida takrorlanmagan. Lokal dalillar
`deploy/.local/live-verification.json`, `deploy/.local/postgres-tests.log` da;
ikkalasi Git’dan chiqarilgan. Tarixiy cleanup eslatmasida eski vaqtinchalik smoke
papkasini rekursiv o‘chirish avtomatik siyosat tomonidan rad etilgani qayd
etilgan; keyingi smoke o‘z yangi fixture’larini tozalagan.

Manbalar: [PostgreSQL rasmiy image’i](https://hub.docker.com/_/postgres),
[Redis ACL hujjatlari](https://redis.io/docs/latest/manual/security/acl/).

---

<a id="russian"></a>

## Русский — локальный запуск в Docker

### Среда и состояние

Инструкция описывает Docker-среду, подготовленную на компьютере владельца.
Новым пользователям следует сначала прочитать [README](../README.md). Среда
SQLite без Docker использует отдельную базу: аккаунты и данные автоматически
не переносятся в PostgreSQL. Пути и прежние разрешения ниже не переносятся
на новый клон, другого пользователя или компьютер.

Сайт: **http://127.0.0.1:8080**. Для локальной работы публичный домен/TLS не нужен.
Production-развёртывание требует отдельных проверок.

Используются Linux-контейнеры Docker Desktop и контекст `desktop-linux`.
Backend/frontend работают в контейнерах. Для вспомогательных Python-команд ниже
нужны среда `backend/.venv` на хосте и зависимости, установленные по README.

Исходный статус: `LOCAL_MVP_RUNNING_VERIFIED`, 2026-11-16. Даты и количества тестов
относятся к тем проверкам; при добавлении перевода сервисы повторно не проверялись.
Первоначально точные новые рабочие/тестовые цели и операции разрешены до
**2026-11-17, 23:59 Asia/Tashkent** (18:59 UTC). Созданы отдельные кластеры,
применены миграции. `ishchi_test` и посторонние БД/Redis не использовались,
рабочие данные не сбрасывались.

Позже только повседневное использование рабочих PostgreSQL/Redis продлено до
**2026-11-24, 23:59 Asia/Tashkent**. Тестовые/миграционные области не продлены.
Исправления ролей/аудита и изолированное восстановление зашифрованной копии
проверены по отдельному разовому разрешению. Статус безопасности:
`LOCAL_SECURITY_PARTIAL`. Актуальные сведения — в [LOCAL_SAFETY.md](LOCAL_SAFETY.md)
и [LOCAL_OPERATIONS.md](LOCAL_OPERATIONS.md). Исторический английский пункт о
непроверенных backup/restore не отражает последующие результаты.

Начальные данные синтетического администратора считаются раскрытыми. Смена
пароля/JWT, новый вход и отклонение старых токенов/сессии проверены. Проверка
отказа со старым паролем не выполнена: старый пароль неизвестен. Не используйте
прежний файл открытых учётных данных. Вход из файла и автоматическое создание
admin в verifier отключены. Не повторяйте ротацию только ради теста; следуйте
[LOCAL_SAFETY.md](LOCAL_SAFETY.md).

### Сервисы и данные

- Рабочий PostgreSQL: `127.0.0.1:55432`, база `ishchi_marketplace_local`, роль
  без superuser `ishchi_local_app`, volume `ishchi-local_pg-work`.
- Тестовый PostgreSQL: `127.0.0.1:55433`, база `ishchi_marketplace_sprint1_local`,
  роль без superuser `ishchi_local_test`, отдельный volume `ishchi-local_pg-test`.
- Рабочий Redis: `127.0.0.1:56379`, DB 0, ACL user `ishchi_local_app`, ключи
  `ishchi:local:work:*`, постоянный AOF volume `ishchi-local_redis-work`.
- Тестовый Redis: `127.0.0.1:56380`, DB 0, ACL user `ishchi_local_test`, ключи
  `ishchi-sprint2-*`, отдельные volume `ishchi-local_redis-test` и сеть.
- Nginx отдаёт React, статику и публичные изображения профилей; API/admin
  направляет в приватный loopback Gunicorn. Файлы заказов/чата закрыты.

Bootstrap-superuser `ishchi_bootstrap`, базы и обычные роли созданы только
в новых выделенных кластерах; CONNECT к `postgres`/`template1` ограничен только
там. Старые БД/роли/SQL-предложения не импортируются. Рабочие и тестовые
учётные данные, ключи и volume не смешиваются.

JSON-файл допуска, пароль и env-переменная сами по себе не являются согласием
владельца. Операции должны соответствовать точной цели, области и сроку.
Тестовое разрешение должно включать миграции, откат/повтор, синтетические записи,
очистку fixture и временных медиа. Очистка Redis — только SCAN/DEL в тестовом
namespace, без FLUSHDB/FLUSHALL. Не подключайте и не сбрасывайте посторонние базы.
PostgreSQL init-скрипты работают только на пустых volume, не сбрасывают
существующий кластер и не меняют его пароли.

### Начальная подготовка — не повторять в существующей среде

На текущем компьютере эти действия уже выполнены. Не генерируйте заново
имеющиеся ключи/пароли. Команды выполнялись из корня проекта `D:\Project\ishchi`:

```powershell
.\backend\.venv\Scripts\python.exe deploy/local.py check
.\backend\.venv\Scripts\python.exe deploy/local.py init-secrets --directory C:/Users/user/.codex/ishchi-local-private
Copy-Item deploy/.env.local.example deploy/.env.local
```

Новый оператор выбирает собственную приватную папку; `LOCAL_SECRETS_DIR`
в `.env.local` должен содержать её абсолютный путь. Генератор отказывается
перезаписывать файлы; создаёт разные рабочие/тестовые/bootstrap-пароли,
`local.pgpass` и **пустые просроченные** шаблоны допуска. Базы он не создаёт
и разрешений не предоставляет. Защитите папку ACL-правами хоста: Windows `chmod`
не гарантирует ACL-защиту. Процессы контейнеров, включая backend UID 10001,
должны читать нужные файлы. Не решайте это публикацией секретов. Не выводите
полную Compose-конфигурацию/env/учётные данные; не добавляйте `.env.local`
и приватную папку в Git.

После настоящего согласия оператор записывает точную цель, область и будущий
срок UTC в файлы допуска. Рабочий DB runtime: `connect`; отдельный мигратор:
дополнительно `local_migrate`; тестовая БД: `connect` + `test_schema`,
`disposable=true`; рабочий Redis: `cache`; тестовый: `cache` + `cache_test`,
`disposable=true`. Рабочие адреса контейнеров: `postgres-work:5432`,
`redis-work:6379`.

Plaintext DB/Redis допускается только для точных loopback/приватных Docker-адресов;
порты хоста привязаны к `127.0.0.1`. Bridge-сети не являются firewall исходящего
трафика. Production требует проверенного TLS. Сохранены `DEBUG=false`, настоящий
вход телефон/пароль/JWT, необязательная KYC, отключённые платежи и отсутствие
seed/demo endpoint. SMS отключены по умолчанию; для проверки телефона/сброса
пароля нужен настоящий HTTP-провайдер, а не синтетический OTP.

### Обычный запуск и остановка

Нужны подготовленная среда и действующее разрешение. Выполняйте в PowerShell
из корня проекта. В каждом новом терминале задавайте `$dc`:

```powershell
$dc = @('--context','desktop-linux','compose','--env-file','deploy/.env.local','-f','deploy/compose.local.yml')
docker @dc config --quiet
docker @dc build backend gateway
```

Если рабочая база и миграции уже подготовлены:

```powershell
docker @dc --profile work up -d postgres-work redis-work
docker @dc --profile work up -d backend gateway
```

Сайт: **http://127.0.0.1:8080**; admin: **http://127.0.0.1:8080/django-admin/**.
`/api/v1/health/ready/` должен вернуть 200. Проверьте регистрацию/вход, профили,
категории, публикацию, заявки/приглашения, вместимость/найм, чат, уведомления,
завершение/отзывы и отключённые платежи.

Остановка и повторный запуск с сохранением данных:

```powershell
docker @dc --profile work stop
docker @dc --profile work up -d postgres-work redis-work backend gateway
```

**Не выполняйте `down -v`, volume prune, seed/reset рабочей базы или восстановление
поверх неё.** Пользователи и медиа сохраняются. Сохраняйте volume и JWT-секрет.
Redis AOF делает fsync каждую секунду; после потери состояния Redis не открывайте
трафик до согласования сессий и отозванных токенов.

Миграции под runtime-логином блокируются до подключения. Для них нужны отдельный
разрешённый мигратор, приватный секрет и overlay `deploy/compose.local-roles.yml`.
Зафиксированное разрешение/срок логина мигратора истекает 2026-11-17, 23:59
Ташкента; дальше требуется отдельное продление. Не создавайте admin при старте.
`collectstatic` также отдельно разрешается для нужного static volume.

### Повторный запуск тестов

Эти команды не нужны для обычного старта. Они сохранены для воспроизведения
исторических тестов; требуется действующая тестовая область разрешения
и отдельно разрешённая пустая/новая цель:

```powershell
docker @dc --profile test up -d postgres-test redis-test
.\backend\.venv\Scripts\python.exe deploy/local.py pg-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
.\backend\.venv\Scripts\python.exe deploy/local.py redis-tests --secrets-dir C:/Users/user/.codex/ishchi-local-private
```

Launcher очищает унаследованные DB/Redis/libpq-цели и выбирает точные локальные
настройки. PG-тесты используют внутрипроцессный кеш; Redis-тесты — SQLite fixture
в памяти. PG-схема остаётся: повтор требует отдельно разрешённого сброса
одноразовой базы или новой цели. Автоматических reset/клонирования, `--reuse-db`
и `--create-db` нет. Не передавайте тестам рабочие учётные данные.

### Копирование и восстановление

`deploy/local.py backup-plan --destination <existing-private-directory> --recipient
<owner-age-public-recipient>` только выводит **план** pg_dump/age для рабочего
localhost:55432, а не выполняет backup. Укажите приватный `local.pgpass` через
`PGPASSFILE`, не передавайте пароль аргументом. Согласуйте снимки БД/медиа,
шифруйте поток до записи на диск и проверяйте оба кода завершения.
`ops.py plan-media-backup` также только строит план.

`deploy/local.py restore-plan --archive <encrypted-dump> --identity-file
<owner-private-key>` предлагает только `127.0.0.1:55434`, базу
`ishchi_marketplace_restore_local`, роль `ishchi_local_restore`. Compose эту цель
не создаёт; нужны отдельная пустая цель и независимое разрешение. Не
восстанавливайте поверх рабочих БД/медиа. До открытия трафика проверьте
происхождение архива, совместимость данных/ACL/приложения и актуальный независимый
реестр удалений. Одних завершённых outbox-задач недостаточно для определения
всех ранее удалённых файлов. Последующие результаты recovery:
[LOCAL_OPERATIONS.md](LOCAL_OPERATIONS.md). Не считайте, что автоматическое
расписание backup уже включено.

### Исторические проверки и ограничения

Исходный отчёт: 269 backend-тестов, 18 frontend-тестов/build; сборка обоих Docker
image, nginx/shell-конфигурация, изолированный от сети smoke production-защиты,
SQLite HTTP smoke, Compose-изоляция, Django/drift/pip прошли. На PostgreSQL 18.6
пройдено 34/34 теста: миграции, `orders/0004`, `common/0001`, откат/повтор,
конкурентный найм, commit/audit rollback и media-outbox retry. На Redis 7.4.12 —
8/8. Локальный plaintext не доказывает production TLS; сбой моделировался
ошибкой транспорта, без физического отключения сервера.

Проверены readiness и HTTP-сценарии: admin, заказчик/три работника, необязательные
телефон/KYC, профили/категории, публикация, дубликаты/вместимость, найм двух
работников, приглашения, чат/уведомления, завершение/отзывы и отзыв токенов.
Два завершённых синтетических заказа и аккаунты сохранены, flush/reset рабочей
базы не выполнялся. Узбекская главная страница просмотрена с реальными метриками.
Первоначально Docker `internal`-сети мешали публикации портов хоста; после замены
на loopback bridge-сети оба интеграционных набора прошли.

Настоящие SMS, публичный hosting/TLS и production-требования этими локальными
проверками не подтверждены. По истечении допуска доступ блокируется; не
продлевайте срок молча и не генерируйте заново пароли/JWT. Последующее состояние
ролей/аудита/backup смотрите в актуальных документах выше.

`deploy/verify_local.py --allow-synthetic-writes` требует отдельного разрешения
и интерактивных учётных данных; создаёт **новые** синтетические записи.
`--credentials` и `--bootstrap-admin` отклоняются до чтения файлов/доступа
к приложению. При stabilization verifier повторно не запускался. Локальные
свидетельства: `deploy/.local/live-verification.json`,
`deploy/.local/postgres-tests.log`; оба исключены из Git. Историческая заметка
cleanup сообщает об отказе автоматической политики в рекурсивном удалении старой
временной smoke-папки; последующий smoke удалил свои новые fixture.

Источники: [официальный image PostgreSQL](https://hub.docker.com/_/postgres),
[документация Redis ACL](https://redis.io/docs/latest/manual/security/acl/).
