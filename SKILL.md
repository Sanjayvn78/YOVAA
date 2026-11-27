---
name: yovaa-project
description: "Use when working on the YOVAA Django bus-pass project, explaining its architecture, preparing a product demo or video, changing verification/payment/e-pass workflows, or documenting setup and testing."
---

# YOVAA Project Skill

## Purpose

Use this skill to work consistently with the YOVAA digital bus-pass platform. The project contains passenger journeys, official-record verification, institution review, Transport Admin operations, payment verification, QR/e-pass generation, and conductor validation.

## First read

Before changing code or writing a project explanation, inspect:

- `README.md` for architecture, commands, URLs, workflows, and the video plan.
- `CLAUDE.md` for repository rules and validation expectations.
- `config/settings.py` for database, media, static, and security configuration.
- The owning app's `urls.py`, `views.py`, `models.py`, and nearby templates.

## Ownership map

| Area | Primary code |
| --- | --- |
| User registration, login, profiles, dashboards | `accounts/` |
| User applications, routes, payment pages, e-pass, QR validation | `users/` |
| School, College, and Transport Admin operations | `admins/` |
| UMIS, EMIS, disability, and staff reference records | `verification/` |
| Application and e-pass persistence | `passes/` |
| Payment persistence | `payments/` |
| Shared UI | `templates/`, `static/css/yovaa.css` |

## Safe workflow for code changes

1. Identify the exact URL and template used by the affected screen.
2. Follow the view into the model query or state mutation that controls the behavior.
3. Check authentication, role, ownership, and status guards.
4. Preserve current named URLs and template context keys unless a coordinated migration is required.
5. Add or update a focused test for the changed behavior.
6. Run `python manage.py check`, then the relevant test, then the broader suite when practical.

## Core domain rules

- College eligibility comes from an active `UMISStudent` record.
- School eligibility comes from an allowed active `EMISStudent` record and the school admin's assigned student range.
- Disabled eligibility comes from an active `DisabledPerson` record.
- Special staff eligibility requires an active, eligible permanent `GovernmentTransportStaff` record.
- `PassApplication` is the central workflow record.
- `Payment` is one-to-one with an application.
- `EPass` is one-to-one with an application and carries the QR data/file and validity dates.
- Route and stop validation must use the configured route map in `users/views.py` and the matching route selector template.
- A completed payment must not be presented as a generated e-pass until the server-side approval path creates or confirms the `EPass`.

## Video-production workflow

For a product video, use synthetic records and this order:

1. Start at `/` and state the product value in one sentence.
2. Show `/users/` and identify the pass categories.
3. Complete one real end-to-end journey, preferably College or General.
4. Show the matching admin review and a deliberate approval/payment verification action.
5. Show the e-pass details and QR/pass validation page.
6. Use a short montage to introduce the remaining journeys.
7. Do not expose passwords, secret keys, PostgreSQL credentials, real identity documents, or personal data.

Keep the narration aligned with current code. Call local payment verification a demo workflow, not a live bank integration.

## Documentation requirements

When documenting a new feature, include:

- User role and entry URL.
- Verification source and required fields/documents.
- Application status changes.
- Admin action and permission boundary.
- Payment and e-pass effect.
- Test command and any setup dependency.

If implementation and UI disagree, report the mismatch and fix the controlling code path rather than hiding it in documentation.
