# Kundalik lokal foydalanish — 2026-11-17

Ilova: http://127.0.0.1:8080. Oddiy start/stop `LOCAL.md` dagi work-only buyruqlar
bilan bajariladi. Startup migratsiya, seed/reset yoki demo login ishlatmaydi.
Bu polish davomida parol, DB rol/huquqlari yoki ruxsat muddatlari o'zgartirilmadi.

Tekshiruv: 303 backend, 30 frontend testi va build PASS. Mavjud PostgreSQL/Redis
bilan worker/buyurtmachi/admin API oqimi hamda 100+ xabarli chat tekshirildi;
sintetik DB yozuvlari rollback qilindi. Ordinary stop/start oldin/keyin barcha
jadval/media/security fingerprintlari mos: 5 akkaunt, 2 ish, 3 ariza, 3 assignment.
Public frontend 320/390/768/1024/1280 px kengliklarda ko'rildi; himoyalangan
kabinetlar komponent regressiyalari va real API orqali tekshirildi, egasining
brauzer loginlari bilan alohida walkthrough bajarilmadi.

## Backup jadvali — faqat taklif, ishga tushirilmagan

- Har kuni 20:00 Asia/Tashkent: yozuvlarni qisqa pauza qilib, PostgreSQL va media
  uchun bitta checkpointdan shifrlangan backup, hash/manifest va joriy mustaqil
  erasure ledger tekshiruvi; xatoda ilovani qayta ishga tushirish majburiy.
- Har yakshanba 21:00: alohida ruxsatlangan YANGI bo'sh restore DB/media targetida
  tiklash va solishtirish; working bazaga restore qilinmaydi.
- Taklif: 30 kun saqlash. Avtomatik o'chirish, scheduler yoki yangi backup/restore
  bu vazifada bajarilmadi. Rejalashtirilgan kelajak amallari, target va retention
  o'chirishlari uchun alohida owner approval kerak; runtime ruxsati yetarli emas.
- Account/media o'chirishlaridan keyin mustaqil ledger yangilanishi zarur.
  Ledgerning joriyligi isbotlanmasa, recovery trafik uchun ochilmaydi.
- Recovery `identity.agekey` maxfiy recovery papkasida qoladi. Egasi uning xavfsiz
  tashqi/offline nusxasini saqlashi hali kerak; kalitni chat/Git yoki shifrlangan
  arxivlar yoniga nusxalamang. Hozirgi bir kompyuterdagi nusxalar kompyuter
  yo'qolishidan himoya qilmaydi.

## Qolgan amaliy cheklovlar

SMS provider lokal muhitda o'chirilgan: SMS orqali parol tiklash va ixtiyoriy
telefon tasdiqlash hozir ishlamaydi. Oddiy telefon/parol registration/login va
optional KYC ishlashi saqlangan. Provider ulash alohida konfiguratsiya/ruxsat talab
qiladi. Eski credential fayli egasining oldingi ko'rsatmasiga binoan qoldirilgan,
operatsion login uchun ishlatilmaydi.

## Shu polishda o'zgargan fayllar

- `backend/apps/chat/views.py`
- `backend/tests/test_chat_history_usability.py`
- `frontend/src/app/router/AppRouter.tsx`
- `frontend/src/app/router/ScrollToTop.tsx`
- `frontend/src/components/navigation/Navbar.tsx`
- `frontend/src/features/admin/AdminUsersPage.tsx`
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/features/auth/RegisterPage.tsx`
- `frontend/src/features/employer/EmployerOrderFormPage.tsx`
- `frontend/src/features/chat/MessagesPage.tsx`
- `frontend/src/features/marketplace/MarketplacePage.tsx`
- `frontend/src/lib/utils.ts`
- `frontend/src/i18n/locales/uz.ts`
- `frontend/src/i18n/locales/ru.ts`
- `frontend/src/i18n/locales/en.ts`
- `frontend/src/test/localUsability.test.tsx`
- `deploy/DAILY_USE.md`

## Real browser acceptance — 2026-11-17 (core role flows verified)

Actual localhost frontend/backend browser checks, using three owner-approved new
synthetic accounts and one job (`Browser QA Job mwk4qurf`, UUID
`94100fad-b67a-4ef8-8408-d4b88d679b67`). Fixtures retained; no reseed/reset.

PASS: public navigation and UZ/RU/EN switching; marketplace search/no-match/reset;
registration validation, phone/password registration and normal login; optional
KYC unchanged; worker profile/category save and reload; employer draft with PNG,
publication; worker application; employer hiring; participant chat/TXT upload and
download; completion and two reviews; worker notifications and marking one read.
PASS: outsider cannot see completed job or its conversation; worker redirected
away from admin; guest direct completed-job image and chat attachment denied.
Authenticated outsider direct attachment endpoint: NOT RUN (UI has no attachment
control for outsiders; direct address-bar requests do not carry the app JWT).
PASS: landing inspected at 320/390/768/1024/1280px without horizontal overflow;
payments page remains disabled, without card collection or simulated payment.

Fixed browser-confirmed English hero, English login/registration success toasts,
mobile menu remaining open after logout, and untranslated forbidden API errors.
Frontend: 31 tests PASS; TypeScript/Vite and gateway builds PASS. Backend: 303
in-memory SQLite regressions PASS; these do not substitute for browser evidence.
Original row/media fingerprints and migration fingerprint: unchanged after the
synthetic workflow. Only gateway rebuilt/recreated, without volume operations.

PASS: owner entered credentials for a separately approved NEW PostgreSQL admin;
browser /admin displays Local owner administrator and live dashboard metrics
(9 users, 3 orders, 4 applications, 5 reviews). Existing SQLite admin was in a
different development database and was not modified/copied. The new account was
created once through hidden terminal prompts; no credentials saved or printed.
Core worker/employer/admin browser flows verified. Existing rotated-admin browser
login remains NOT RUN; that account was not used or modified. Browser evidence:
`deploy/.local/browser-acceptance-60pea3py/admin-dashboard.jpg`.
The previously noted notification/review accessibility localization gap is
implemented in the final gaps work below.

## Final browser gaps — 2026-11-17

- PASS: historical server notification templates/event labels and review star
  labels localized in UZ/RU/EN. Presentation only; existing notification records,
  user chat content and custom moderation notes retained. Unknown future/custom
  templates retain original text. List and dropdown share the same formatter.
- PASS: 40 frontend regressions, 303 offline backend tests, TypeScript/Vite build
  and Docker gateway build. No migrations/role/expiry/credential changes.
- PASS: `local/verify-private-attachment.py` made actual nginx HTTP GET requests
  using existing synthetic participant/outsider accounts and 60-second signed
  in-memory test access tokens (no password login, refresh-token INSERT or session
  revocation): both `/auth/me/` 200 with matching identities; participant attachment
  200 with exact file hash/private-no-store; unrelated attachment 403
  `chat_access_denied`; guest attachment 401. No APIClient/mocked transport.
- Historical inventory before the approved cleanup: two active staff/superusers in working PostgreSQL: owner
  admin `319cb674-96bc-4de3-bf08-e6c4462500f7` and synthetic verification admin
  `489124fe-ae1b-4551-8495-9f148c46490b`. The latter is a candidate for owner review
  if no longer needed. No account deleted/demoted/changed.
- NOT RUN: rotated verification administrator normal browser login; owner stated
  credentials unavailable. No reset/rotation/session changes attempted.
- Owner separately approved one NEW worker `Notification QA 20261117` and four
  clearly marked SINOV notification fixtures only for that account, retained after
  testing. Owner created worker `6b7afc3a-bab6-431c-82de-18fb02e53a87` through private
  browser entry. Exactly four notifications inserted once for that account.
  PASS: real browser list titles/messages/event labels in UZ/RU/EN; all four
  remained unread. Screenshots: `deploy/.local/final-gaps-notifications-{uz,ru,en}.jpg`.
  No new orders/applications/reviews/media authorized or created by this step.
- Docker Desktop was stopped during continuation; existing daemon started and
  gateway recreated after namespace restart. Work PG/Redis volumes reused without
  provisioning, migration, reset or deletion. Localhost is responding again.

- PASS: before/after HMAC fingerprints match for every pre-existing row, all
  existing media and migrations. Only the approved one worker/four notifications
  (plus that registration's normal profile/session records) added. Evidence:
  `deploy/.local/final-gaps-preservation.json`, `final-gaps-live-api.json`,
  `final-gaps-{frontend-tests,backend-tests,build,docker-build}.log`.
- Review star labels: actual component regression renders five accessible buttons
  in each language; no extra job/review writes were made to reopen a browser form.
- The former privilege-retention decision was resolved by the separately approved
  local operations cleanup below. Old admin normal browser login remains NOT RUN;
  its demotion/authorization checks are recorded in that section.

## Local admin cleanup and automated backup — 2026-11-17

Status: LOCAL_OPERATIONS_VERIFIED for approved local operations. See
[LOCAL_OPERATIONS.md](LOCAL_OPERATIONS.md) for daily use and recovery gates.

- Synthetic admin demoted under exact owner approval; active account/history and
  password retained. Owner admin unchanged; owner API 200, subject admin API 403,
  old-version access/refresh 401, Django permission denied, subject sessions zero.
- One real encrypted backup and an additionally approved native Task Scheduler run
  passed. Task `ISHCHI Encrypted Local Backup` is enabled/Ready; LastTaskResult=0;
  daily 20:00 Asia/Tashkent, current interactive Windows operator and Docker needed.
- Source DB/media checkpoint, encrypted/HMAC-authenticated manifest and independent
  ledger, ciphertext/structure/media checks passed. Existing backup/key reused;
  original records/media/migrations/recovery files preserved except approved
  demotion/session/blacklist/audit changes. No role grants or expiry changes.
- Authorization expires Nov 24 2026 23:59 Tashkent; expired runs fail with renewal
  required. No retention deletion. After deletion/anonymization, a fresh approved
  authoritative ledger checkpoint is mandatory before recovery traffic.
- No new restore performed. Secure offline recovery-key copy remains owner action.

- Final regression PASS: **345 backend tests** (42 focused operations regressions),
  one existing DATABASES-override warning. Frontend NOT RUN: unchanged.
  Native task schema, real Windows ACL checks, backend image build and actual
  Task Scheduler backup run PASS. New restore NOT RUN; no PG/Redis test DB reset.
