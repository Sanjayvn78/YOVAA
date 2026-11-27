from pathlib import Path
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pypdf import PdfReader

from verification.models import (
    DisabledPerson,
    EMISStudent,
    GovernmentTransportStaff,
    UMISStudent,
)


DEFAULT_PDF = Path(
    "C:/Users/Sanjay/Downloads/"
    "YOVAA_State_UT_UMIS_EMIS_Disability_Transport_Demo_Data (1).pdf"
)
SECTION_NAMES = {
    "UMIS – College Students": "umis",
    "EMIS – School Students": "emis",
    "Disabled Persons": "disabled",
    "Transport Staff": "staff",
}
YEAR_PATTERN = re.compile(r"^\d{4}-(?:\d{2}|\d{4})$")


def nonempty_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def records_by_id(lines, prefix):
    indexes = [
        index for index, line in enumerate(lines)
        if line.startswith(prefix) and re.search(r"-\d{3}$", line)
    ]
    for position, start in enumerate(indexes):
        end = indexes[position + 1] if position + 1 < len(indexes) else len(lines)
        yield lines[start:end]


def parse_page(page_text):
    lines = nonempty_lines(page_text)
    section_positions = []
    for index, line in enumerate(lines):
        if line in SECTION_NAMES:
            section_positions.append((index, SECTION_NAMES[line]))
    if not section_positions:
        return None, {}

    first_section_index = section_positions[0][0]
    state = lines[first_section_index - 1]
    parsed = {}
    for position, (start, section_name) in enumerate(section_positions):
        end = (
            section_positions[position + 1][0]
            if position + 1 < len(section_positions)
            else len(lines)
        )
        parsed[section_name] = list(
            records_by_id(lines[start:end], {
                "umis": "UMIS-",
                "emis": "EMIS-",
                "disabled": "DIS-",
                "staff": "TO-",
            }[section_name])
        )
    return state, parsed


def parse_umis(records, state):
    result = []
    for record in records:
        year_index = next(
            (index for index, value in enumerate(record) if YEAR_PATTERN.match(value)),
            None,
        )
        if year_index is None or year_index < 5 or year_index + 1 >= len(record):
            raise ValueError(f"Invalid UMIS record: {record}")
        result.append(
            UMISStudent(
                umis_number=record[0],
                registration_number=record[1],
                name=record[2],
                department=record[3],
                college_name=" ".join(record[4:year_index]),
                academic_year=record[year_index],
                year=record[year_index + 1],
                state=state,
            )
        )
    return result


def parse_emis(records, state):
    result = []
    for record in records:
        year_index = next(
            (index for index, value in enumerate(record) if YEAR_PATTERN.match(value)),
            None,
        )
        if year_index is None or year_index < 4 or year_index + 1 >= len(record):
            raise ValueError(f"Invalid EMIS record: {record}")
        result.append(
            EMISStudent(
                student_id=record[0],
                student_name=record[2],
                school_name=" ".join(record[3:year_index]),
                academic_year=record[year_index],
                class_name=record[year_index + 1],
                state=state,
            )
        )
    return result


def parse_disabled(records, state):
    result = []
    for record in records:
        if len(record) < 6:
            raise ValueError(f"Invalid disabled-person record: {record}")
        result.append(
            DisabledPerson(
                disability_id=record[0],
                name=record[1],
                disability_type=record[3],
                district=record[4],
                state=record[5],
            )
        )
    return result


def parse_staff(records, state):
    result = []
    for record in records:
        if len(record) < 7:
            raise ValueError(f"Invalid transport-staff record: {record}")
        result.append(
            GovernmentTransportStaff(
                staff_number=record[0],
                name=record[1],
                department=record[2],
                designation=record[3],
                workplace=" ".join(record[4:-2]),
                district=record[-2],
                state=record[-1],
                employment_status="ACTIVE",
                is_eligible=True,
                is_active=True,
            )
        )
    return result


class Command(BaseCommand):
    help = "Replace verification demo data with the supplied state-wise PDF dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pdf",
            type=Path,
            default=DEFAULT_PDF,
            help="Path to the state-wise verification data PDF.",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            help="Keep existing verification rows instead of replacing them.",
        )

    def handle(self, *args, **options):
        pdf_path = options["pdf"]
        if not pdf_path.exists():
            raise CommandError(f"Dataset PDF not found: {pdf_path}")

        umis = []
        emis = []
        disabled = []
        staff = []
        try:
            for page in PdfReader(str(pdf_path)).pages:
                state, sections = parse_page(page.extract_text() or "")
                if not state:
                    continue
                umis.extend(parse_umis(sections.get("umis", []), state))
                emis.extend(parse_emis(sections.get("emis", []), state))
                disabled.extend(parse_disabled(sections.get("disabled", []), state))
                staff.extend(parse_staff(sections.get("staff", []), state))
        except (IndexError, ValueError) as error:
            raise CommandError(f"Could not parse dataset PDF: {error}") from error

        expected = 36 * 4
        counts = (len(umis), len(emis), len(disabled), len(staff))
        if counts != (expected, expected, expected, expected):
            raise CommandError(
                "Unexpected dataset size. Expected 144 records in each category, "
                f"got UMIS={counts[0]}, EMIS={counts[1]}, "
                f"disabled={counts[2]}, staff={counts[3]}."
            )

        with transaction.atomic():
            if not options["append"]:
                UMISStudent.objects.all().delete()
                EMISStudent.objects.all().delete()
                DisabledPerson.objects.all().delete()
                GovernmentTransportStaff.objects.all().delete()
            UMISStudent.objects.bulk_create(umis)
            EMISStudent.objects.bulk_create(emis)
            DisabledPerson.objects.bulk_create(disabled)
            GovernmentTransportStaff.objects.bulk_create(staff)

        mode = "appended" if options["append"] else "replaced"
        self.stdout.write(
            self.style.SUCCESS(
                f"Verification data {mode}: "
                f"UMIS={len(umis)}, EMIS={len(emis)}, "
                f"disabled={len(disabled)}, transport staff={len(staff)}."
            )
        )
