import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from pypdf import PdfReader


DEFAULT_PDF = Path(
    "C:/Users/Sanjay/Downloads/"
    "school_college_demo_usernames_passwords (1).pdf"
)
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "admin_credentials.json"
HEADERS = {"State / UT", "Type", "Institution", "Username", "Password"}
TYPES = {"School", "College"}
STATES = [
    "Dadra and Nagar Haveli and Daman and Diu", "Andaman and Nicobar Islands",
    "Arunachal Pradesh", "Andhra Pradesh", "Chhattisgarh", "Himachal Pradesh",
    "Jammu and Kashmir", "Madhya Pradesh", "Tamil Nadu", "Uttar Pradesh",
    "West Bengal", "Uttarakhand", "Telangana", "Rajasthan", "Maharashtra",
    "Karnataka", "Jharkhand", "Haryana", "Gujarat", "Chandigarh", "Delhi",
    "Lakshadweep", "Puducherry", "Ladakh", "Tripura", "Sikkim", "Punjab",
    "Odisha", "Nagaland", "Mizoram", "Meghalaya", "Manipur", "Kerala",
    "Goa", "Bihar", "Assam", "Andaman and Nicobar Islands",
]


def state_at(lines, index):
    for state in sorted(set(STATES), key=len, reverse=True):
        words = state.split()
        for size in range(1, min(4, len(words)) + 1):
            if " ".join(lines[index:index + size]) == " ".join(words):
                return state, size
    return None, 0


def parse_credentials(pdf_path):
    lines = [
        line.strip()
        for page in PdfReader(str(pdf_path)).pages
        for line in (page.extract_text() or "").splitlines()
        if line.strip()
    ]
    records = []
    index = 0
    while index < len(lines):
        if lines[index] in HEADERS:
            index += 1
            continue
        state, state_size = state_at(lines, index)
        if not state or index + state_size >= len(lines):
            index += 1
            continue
        kind = lines[index + state_size]
        if kind not in TYPES:
            index += 1
            continue
        index += state_size + 1
        body = []
        while index < len(lines):
            next_state, next_size = state_at(lines, index)
            if next_state and index + next_size < len(lines) and lines[index + next_size] in TYPES:
                break
            if lines[index] not in HEADERS:
                body.append(lines[index])
            index += 1
        if not body:
            raise ValueError(f"Missing credential row for {state} {kind}")
        password = body[-1]
        username_parts = body[:-1]
        username_index = None
        username = None
        for suffix_size in range(1, min(3, len(username_parts)) + 1):
            candidate = "".join(username_parts[-suffix_size:])
            if re.fullmatch(r"[a-z0-9_]+_demo", candidate):
                username_index = len(username_parts) - suffix_size
                username = candidate
                break
        if username_index is None or not password.startswith("Demo@"):
            raise ValueError(f"Invalid credential row for {state} {kind}: {body}")
        institution = " ".join(body[:username_index])
        records.append({
            "state": state,
            "type": kind,
            "institution": institution,
            "username": username,
            "password": password,
        })
    return records


class Command(BaseCommand):
    help = "Import school and college admin credentials from the supplied PDF."

    def add_arguments(self, parser):
        parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)

    def handle(self, *args, **options):
        pdf_path = options["pdf"]
        if not pdf_path.exists():
            raise CommandError(f"Credentials PDF not found: {pdf_path}")
        try:
            records = parse_credentials(pdf_path)
        except ValueError as error:
            raise CommandError(str(error)) from error
        if len(records) != 288:
            raise CommandError(f"Expected 288 credentials, found {len(records)}")
        OUTPUT_PATH.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"Imported {len(records)} admin credentials."))