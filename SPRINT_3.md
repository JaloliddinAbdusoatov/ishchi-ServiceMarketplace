# Sprint 3 — authentication, API authorization and audit reliability

`SPRINT_3_COMPLETE_OFFLINE` — 2026-11-16 (Asia/Tashkent).

## Confirmed defects fixed

- Phone verification previously issued login tokens to anyone presenting a phone
  OTP, including a number merely claimed at registration. Verification now requires
  the active account's authenticated session, binds the requested number to that
  account, and returns no tokens. Frontend verification preserves the existing
  session and redirects signed-out users to login.
- SMS recovery accepts only a previously verified account phone. Registration
  still activates immediately without SMS; verification and KYC remain optional.
  Unverified users must verify while signed in before relying on SMS recovery.
- OTPs are bound to the account ID and credential version, preventing reuse after
  anonymization/number reuse, password changes or logout-all. Recovery validates
  the password before consuming the OTP, locks the account, and revokes existing
  JWT sessions on success. Replay is rejected.
- Reset acknowledgement is uniform for absent, unverified and eligible accounts,
  including cooldown/rate-limit and SMS delivery failures. Failed delivery still
  invalidates its OTP. Cache outages return sanitized 503 for every account case.
  This does not claim constant-time responses; immediate registration also
  necessarily reveals whether an identifier can be registered.
- Auth throttles previously trusted arbitrary X-Forwarded-For. They now trust only
  the actual peer or explicitly configured proxy/X-Real-IP. Refresh and reset
  confirmation now have security throttles. Missing-account login performs dummy
  password hashing, and password serializers preserve significant whitespace.
- Django admin now requires the active ADMIN/staff account boundary and limits
  login POSTs by trusted client IP, failing closed on cache outage. Generic user
  forms cannot provision accounts, edit passwords/privileges or hard-delete users;
  reviewed APIs and operator CLI provisioning remain the write paths.
- KYC notes are restricted to the profile owner and administrator. Suspended
  employers' published orders are no longer readable by unrelated users or open
  to new applications. Favorites enforce current order visibility on add/list;
  bookmarks cannot disclose draft/paused or otherwise inaccessible orders.
- Reporting a message requires current chat membership; reporting an order
  requires order visibility. Existing application-based chat policy is preserved.
- Chat attachments now validate size, extension, declared MIME and content shape,
  including image decoding, UTF-8 text, document signatures and bounded DOCX
  archive entries; traversal and macro payload entries are rejected. Service-level
  validation prevents bypassing the serializer. This is not malware certification.
- Order images are delivered through a visibility-checked API with private/no-store
  headers. Local media serving and the nginx template deny their raw storage URLs.
  Frontend blob requests use the API client and release image data on session change.
- Administrative suspension, activation, verification, moderation, report resolution
  and category writes now record actor/action/target in Django's existing LogEntry
  table inside the mutation transaction. Audit failure rolls back the mutation;
  no request payload, private KYC notes or credentials are copied. The audit admin
  is read-only. Moderation also closes pending applications/invitations atomically.
- Deletion uses a keyed phone digest and excludes unstructured deletion reasons
  from new audit entries. Public profile/portfolio media is removed after commit;
  a rolled-back deletion retains original media. Storage cleanup is post-commit,
  not a cross-storage transaction or a guarantee about backups/downloaded copies.

## Actual final results

- PASS: **217 backend tests** on ephemeral SQLite, including **58 new Sprint 3 cases**.
- PASS: **18 frontend tests**, including two new private-image lifecycle cases.
- PASS: TypeScript/Vite production build; Django system check; migration drift
  check (no new migrations); pip dependency consistency; git diff whitespace check.
- PASS: npm audit — **0 reported vulnerabilities**. No dependency upgrades made.
- PASS: bounded local source scan found no recognizable private keys/provider
  tokens or non-template environment files in the scanned Git-visible inventory;
  source/configuration review checked signing/SMS defaults. This is not proof that
  arbitrary credentials or secrets in historical Git objects are absent.
- NOT RUN: Python advisory/vulnerability audit — pip-audit is not installed;
  pip check validates dependency consistency only.
- BLOCKED / NOT RUN: PostgreSQL and Redis runtime integration, distributed races,
  append-only database permissions, real SMS and hosted/nginx/TLS/media checks.
- Existing non-failing output: one SQLite DATABASES-override warning and Zod build
  annotation warnings. Final test failures: **0**.

No PostgreSQL/Redis connection, legacy database access, provisioning, SQL proposal
execution, external deployment, commit or push occurred. Sprint 2 production
authorization safeguards remain intact. Existing unrelated work was preserved.

## Release blockers / next steps

1. Run an approved Python vulnerability auditor; triage actual advisory results.
2. Obtain exact-target, operations and expiry authorization before any PostgreSQL/
   Redis runtime work. The owner-controlled production authorization mechanism
   remains a Sprint 2 release blocker. Verify concurrency and database audit ACLs
   on separately authorized targets; SQLite results do not establish those guarantees.
3. Verify the revised nginx media-denial rules, authenticated downloads, trusted
   proxy limits, HTTPS and real SMS on an authorized hosted environment; include
   media-erasure failure/retry and storage/backup retention procedures.

This is offline completion, not full security certification or production readiness.
