# YOVAA

YOVAA is a Django-based digital bus-pass platform for applying, verifying, approving, paying for, issuing, and validating public-transport passes.

The system connects different passenger categories with the records and administrators responsible for checking eligibility. A successful application ends with a digital e-pass and QR-based validation for conductors.

## What the system does

- Verifies applicants against UMIS, EMIS, disability, or Government Transport Staff records.
- Collects routes, boarding points, destination points, photos, identity documents, address proof, and signatures.
- Uses dependent travel selection: State -> District -> Route -> Starting Bus Stop and Destination Bus Stop.
- State and district options are sourced from `static/js/india_locations.js`, generated from the supplied India 2026 PDF catalog (36 States/UTs and 760 districts).
- District routes and bus stops are sourced from `routes/route_catalog.json` and `static/js/bus_routes.js`, generated from the collected routes PDF.
- UMIS, EMIS, Disabled Person, and Transport Staff verification records are loaded from the supplied state-wise demo PDF with `verification/management/commands/import_demo_data.py`.
- School and College Admin logins are loaded from the supplied credentials PDF with `admins/management/commands/import_admin_credentials.py`.
- Tracks application status through verification and payment stages.
- Provides institution and Transport Admin workspaces.
- Creates digital e-passes with validity dates and QR data.
- Lets conductors verify a pass number or scan a QR code.
- Supports renewal for eligible existing passes.

## Technology

- Python
- Django 6.1.1
- Django authentication and sessions
- PostgreSQL configured in `config/settings.py`
- Django templates, HTML, CSS, and small JavaScript modules
- File uploads stored under `media/`
- QR code generation and browser QR scanning

There is a `db.sqlite3` file in the repository, but the current settings use PostgreSQL. Use the configured PostgreSQL database or change the database configuration deliberately for local development.

The collected routes PDF contributes 144 routes across 100 districts. The importer also preserves six existing Coimbatore routes used by the application, for 150 selectable routes overall. To regenerate both route data files after replacing the PDF, run `python routes/import_bus_routes.py` from the project root. Districts without a route remain unavailable for route selection.

## Project structure

```text
manage.py                 Django command entry point
config/                   Settings, root URLs, ASGI, WSGI, home view
accounts/                 Registration, login, profiles, user dashboards
users/                    Applications, payments, e-passes, QR verification
admins/                   School, college, and Transport Admin workflows
passes/                   PassApplication and EPass models
payments/                 Payment model and payment records
verification/             UMIS, EMIS, disabled, and staff reference records
documents/                Reserved document app boundary
routes/                   Reserved route app boundary
templates/                Django templates for users and administrators
static/                   CSS, images, and front-end assets
media/                    Uploaded documents and generated QR files
```

## Main data model

### `accounts.UserProfile`

Extends Django's `User` with user type, role, phone number, registration number, disability ID, staff number, and activation state.

User types are `COLLEGE`, `DISABLED`, `GENERAL`, and `SPECIAL`. Roles include `USER`, `SCHOOL_ADMIN`, `COLLEGE_ADMIN`, `TRANSPORT_ADMIN`, and `CONDUCTOR`.

### `verification`

- `UMISStudent`: college student identity and academic record.
- `EMISStudent`: school student identity and academic record.
- `DisabledPerson`: disability ID, eligibility, district, and disability details.
- `GovernmentTransportStaff`: staff ID, employment status, eligibility, and workplace.

### `passes.PassApplication`

Stores the applicant, pass type, application type, status, identity fields, travel route, uploaded documents, remarks, and timestamps. It is the central record moving through the approval pipeline.

### `passes.EPass`

One-to-one with a completed application. Stores the pass number, issue and expiry dates, validity window, QR payload, generated QR file, and active state.

### `payments.Payment`

One-to-one with an application. Stores amount, UPI or QR method, transaction ID, payment status, and payment timestamp.

## Application journeys

### College student

1. Student enters a UMIS registration number.
2. YOVAA checks an active `UMISStudent` record.
3. Student signs in or registers with a college email.
4. Student selects a state, district, configured route, and two stops from that route.
5. Student uploads photo, Aadhaar/address proof, and signature.
6. Application goes through Transport and College verification.
7. Student pays after approval.
8. Transport Admin verifies the payment and the e-pass is generated.

### Disabled person

1. Applicant enters a disability ID.
2. YOVAA verifies an active `DisabledPerson` record.
3. Applicant selects the travel district and uploads required documents.
4. Application moves to payment.
5. Transport Admin verifies payment and issues the e-pass.

### General user

1. User creates an account with name and phone number.
2. User submits personal details, district, route, stops, and documents.
3. YOVAA creates a payment record.
4. User submits UPI or QR payment details.
5. Transport Admin verifies the payment.
6. YOVAA generates the digital pass.

### Special transport staff

1. Staff member enters a Staff ID.
2. YOVAA accepts only active, eligible permanent staff.
3. Staff reviews the verified record and uploads four documents.
4. Transport Admin verifies the application.
5. A free all-bus special e-pass is generated.

### School student

1. School Admin enters an EMIS student ID.
2. The account is restricted to the school and student range assigned to that admin.
3. Admin selects route and stops and uploads the student photo, school ID, and Aadhaar document.
4. The application is sent to Transport Admin for payment verification and e-pass issuance.

## Status lifecycle

Common status values are:

```text
DRAFT -> SUBMITTED -> verification stage -> PAYMENT_PENDING
      -> PAYMENT_COMPLETED -> e-pass available
```

The exact verification stage depends on the pass type. Current choices also include `TRANSPORT_VERIFICATION`, `COLLEGE_VERIFICATION`, `SCHOOL_VERIFICATION`, `DISABLED_VERIFICATION`, `GENERAL_VERIFICATION`, `SPECIAL_VERIFICATION`, `COLLEGE_APPROVED`, `SCHOOL_APPROVED`, and rejection states.

## Important URLs

### Public and user URLs

- `/` - YOVAA landing page
- `/users/` - pass-type selection
- `/accounts/college/register/` and `/accounts/college/login/`
- `/accounts/disabled/register/` and `/accounts/disabled/login/`
- `/accounts/general/register/` and `/accounts/general/login/`
- `/accounts/special/login/`
- `/users/apply/college/`
- `/users/apply/disabled/`
- `/users/apply/general/`
- `/users/apply/special/`
- `/users/dashboard/`
- `/users/verify-pass/`
- `/users/qr-scanner/`

### Administration URLs

- `/admins/` - Admin Control Center
- `/admins/school/login/`
- `/admins/college/login/`
- `/admins/transport/`
- `/admins/transport/school/`
- `/admins/transport/college/`
- `/admins/transport/disabled/`
- `/admins/transport/general/`
- `/admins/transport/special/`

## Local setup

From the `YOVAA` directory:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install django psycopg[binary] qrcode pillow pypdf
python manage.py check
python manage.py migrate
python manage.py runserver
```

To replace the verification database rows with the supplied PDF dataset:

```powershell
python manage.py import_demo_data
```

The command replaces the existing four verification tables by default and imports 144 rows per category. Use `--pdf "C:/path/to/file.pdf"` for another copy of the dataset, or `--append` when replacement is not wanted. The source PDF contains some repeated demo identifiers across states; raw identifiers are preserved and state is stored with every record.

To regenerate the School and College Admin credential catalog:

```powershell
python manage.py import_admin_credentials
```

This imports 288 synthetic credentials and writes `admins/admin_credentials.json`. They are demo-only credentials.

Open `http://127.0.0.1:8000/`.

If the virtual environment is outside the project directory, activate the workspace `.venv` instead. The PostgreSQL database configured in `config/settings.py` must exist and be reachable before migrations or normal requests can use the database.

Useful commands:

```powershell
python manage.py test
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

The repository currently contains no `requirements.txt`; keep the installed package list documented when the environment is prepared for another machine.

## Demo data and credentials

Admin usernames and demo passwords are currently hard-coded in `admins/views.py`. Treat them as development-only credentials and never use them in production. Before recording a video, seed or confirm the following records exist:

- One active UMIS student for the college journey.
- One active EMIS student for the school journey.
- One active disabled-person record.
- One active permanent eligible transport staff record.
- At least one route with valid stops.

Do not show real identity documents, phone numbers, passwords, or database credentials in a public recording. Use synthetic demo data.

## Testing

Run the full Django test suite with:

```powershell
python manage.py test
```

The main tests are in `accounts/tests.py`, `admins/tests.py`, and `users/tests.py`. Also run `python manage.py check` after configuration or view changes.

## Video demo plan

A clear 5-7 minute product video can use this sequence:

1. **Opening, 20 seconds:** Show the YOVAA home page and explain that one platform connects application, verification, payment, e-pass, and on-board validation.
2. **User choice, 30 seconds:** Open `/users/` and introduce the five pass categories.
3. **College journey, 2 minutes:** Verify a UMIS student, complete route and document details, show the application number and tracking timeline.
4. **Admin review, 1 minute:** Open the College Admin workspace, approve the application, then open the Transport Admin college module.
5. **Payment and e-pass, 1 minute:** Submit or verify payment, show the generated pass number, validity, route, and QR code.
6. **Conductor validation, 45 seconds:** Open the QR scanner or pass verification page and show valid, expired, or invalid outcomes.
7. **Other modules, 45 seconds:** Briefly show Disabled, General, Special Staff, and School flows, emphasizing that each uses the correct official dataset.
8. **Closing, 20 seconds:** Summarize the audit-friendly flow: verified identity, controlled approvals, payment confirmation, and digital travel validation.

Suggested narration: "YOVAA brings every bus-pass journey into one connected workflow. Each applicant is checked against the right source record, every approval is visible to the responsible administrator, and the final pass can be carried and verified digitally."

## Production notes

- Run the server locally before screen recording.
- Use a clean browser profile and synthetic seed data.
- Keep one browser window for the user and another for admin workspaces.
- Hide the terminal, database credentials, media paths, and password fields.
- Prefer a short focused journey in the main recording; use the other pass types as a fast overview.
- Reset demo data before a second take so application statuses remain predictable.

## Known limitations

- Database and secret-key values are currently in `config/settings.py` and should move to environment variables for deployment.
- `DEBUG` is enabled and `ALLOWED_HOSTS` is empty for local development.
- Several apps are reserved boundaries with minimal model/view code; most current business logic is in `accounts`, `users`, and `admins`.
- Payment is a local verification workflow, not a live payment-gateway integration.
- Some templates are legacy screens while newer screens use the shared YOVAA stylesheet.
