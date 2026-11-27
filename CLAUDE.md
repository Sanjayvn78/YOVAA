# YOVAA Project Instructions

## Project context

YOVAA is a Django 6.1.1 digital bus-pass platform. It serves passengers, school and college administrators, Transport Admin, and conductors. The central workflow is identity verification -> application -> review -> payment verification -> e-pass generation -> QR/pass validation.

Read `README.md` before making broad changes. For a screen-recorded demo, use synthetic data only.

## Repository conventions

- Keep business logic in the existing app that owns the workflow: `accounts` for auth/profile flows, `users` for application/payment/e-pass flows, `admins` for review and operations, `verification` for reference datasets, and `passes`/`payments` for models.
- Reuse existing Django templates, named URLs, decorators, session keys, status choices, route definitions, and shared styles before introducing new abstractions.
- Preserve the existing tab-indented Python style in files that already use tabs. Do not reformat unrelated code.
- Use Django ORM and `get_object_or_404` for database access. Keep POST actions CSRF-protected.
- Keep uploaded files under the configured `MEDIA_ROOT`; do not commit real identity documents or generated private credentials.
- Verification demo records are replaced with `python manage.py import_demo_data`; do not hand-edit or mix the old dataset back into the four verification tables.
- When changing a status transition, inspect both the user-facing tracking template and the corresponding admin action.
- When changing e-pass behavior, inspect QR generation, validity dates, the e-pass templates, and pass verification together.

## Validation

Run these from the directory containing `manage.py`:

```powershell
python manage.py check
python manage.py test
```

For model changes, also run:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Before reporting success, validate the narrowest relevant test first, then run the broader check when practical.

## Security and configuration

- `config/settings.py` currently contains a development secret key and PostgreSQL credentials. Never expose them in documentation, screenshots, commits, or video.
- `DEBUG = True` and the database configuration are development settings. Do not describe this project as production-ready without changing them.
- Do not replace the PostgreSQL configuration with SQLite merely because `db.sqlite3` exists; document or deliberately configure the chosen database.
- Admin demo passwords in `admins/views.py` are development-only. Never add new hard-coded production credentials.
- Use fake names, IDs, phone numbers, files, and payment references in tests and videos.

## Video and documentation work

When asked to prepare a project video:

1. Use the journey in `README.md` as the source of truth.
2. Demonstrate one complete College or General pass flow rather than clicking disconnected screens.
3. Include one verification/admin decision and the final e-pass or QR validation.
4. Mention the other pass categories briefly.
5. Avoid showing secrets, real documents, or raw database data.
6. Keep narration factual: distinguish implemented behavior from future ideas.

When updating documentation, keep it synchronized with URL names, model names, status choices, commands, and actual screens. If a feature is incomplete or a module is only a placeholder, say so explicitly.

## Change discipline

Make the smallest focused change that solves the request. Do not rewrite templates or perform unrelated formatting. Add or update tests when behavior changes, especially for permissions, ownership checks, status transitions, payments, QR validation, or uploaded-document requirements.
