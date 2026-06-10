import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
import re
from uuid import UUID
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError

from app.models.github_job_source import GithubJobSource
from app.models.github_scan_run import GithubScanRun
from app.models.job_posting import JobExtractionStatus, JobPosting, JobSource, JobStatus
from app.repositories.github_job_source_repository import GithubJobSourceRepository
from app.repositories.github_scan_run_repository import GithubScanRunRepository
from app.repositories.job_posting_repository import JobPostingRepository
from app.services.job_service import JobPostingService, compute_content_hash
from app.services.job_status_service import JobStatusService
from app.services.jobs.job_content_extractor import (
    ExtractedJobContent,
    JobContentExtractorService,
)
from app.services.jobs.job_role_filter import (
    JobRoleFilterInput,
    JobRoleFilterResult,
    classify_job_role,
)


MAX_MARKDOWN_BYTES = 3 * 1024 * 1024
RECENT_JOB_MAX_AGE_DAYS = 7
JOB_TEXT_COLUMN_MAX_LENGTH = 255
JOB_URL_COLUMN_MAX_LENGTH = 2048


class DisabledGithubSourceError(Exception):
    pass


class GithubSourceScanError(Exception):
    pass


@dataclass(frozen=True)
class GithubSourceScan:
    source: GithubJobSource
    scan_run: GithubScanRun
    total_rows_seen: int
    parsed_jobs: int
    scanned_jobs: int
    inserted_jobs: int
    inserted_job_records: list[JobPosting]
    duplicate_jobs: int
    rows_skipped_by_filters: int
    jobs_tagged: int
    extraction_success_count: int
    extraction_failed_count: int
    matched_jobs: int
    generated_resumes: int
    uploaded_pdfs: int
    message: str


@dataclass(frozen=True)
class GithubJobRow:
    company: str
    title: str
    location: str | None
    job_url: str
    raw_text: str
    source_section: str | None = None


@dataclass(frozen=True)
class GithubJobParseResult:
    rows: list[GithubJobRow]
    total_rows_seen: int


@dataclass(frozen=True)
class GithubJobCreateResult:
    job: JobPosting
    inserted: bool
    tagged: bool


class GithubJobSourceService:
    def __init__(
        self,
        source_repository: GithubJobSourceRepository,
        job_repository: JobPostingRepository,
        scan_run_repository: GithubScanRunRepository,
        extractor: JobContentExtractorService | None = None,
        status_service: JobStatusService | None = None,
    ) -> None:
        self.source_repository = source_repository
        self.job_repository = job_repository
        self.scan_run_repository = scan_run_repository
        self.extractor = extractor or JobContentExtractorService()
        self.status_service = status_service

    def scan_source(self, source: GithubJobSource) -> GithubSourceScan:
        if not source.enabled:
            raise DisabledGithubSourceError("Enable this GitHub source before scanning.")

        markdown = _fetch_markdown(source.raw_readme_url)
        parse_result = parse_recent_github_job_rows_with_summary(
            markdown,
            base_url=source.repo_url,
        )
        parsed_rows = parse_result.rows
        job_service = JobPostingService(
            self.job_repository,
            status_service=self.status_service,
        )
        inserted_jobs: list[JobPosting] = []
        duplicate_jobs_count = 0
        rows_skipped_by_filters = 0
        jobs_tagged = 0
        extraction_success_count = 0
        extraction_failed_count = 0

        for row in parsed_rows:
            classification = classify_job_role(
                JobRoleFilterInput(
                    title=row.title,
                    raw_text=row.raw_text,
                    source_section=row.source_section,
                    scan_role_tags=getattr(source, "scan_role_tags", []),
                    include_keywords=getattr(source, "include_keywords", []),
                    exclude_keywords=getattr(source, "exclude_keywords", []),
                ),
            )
            if not classification.included:
                rows_skipped_by_filters += 1
                continue

            create_result = _create_github_job(
                job_service=job_service,
                job_repository=self.job_repository,
                user_id=source.user_id,
                source=source,
                row=row,
                classification=classification,
                status_service=self.status_service,
            )
            if create_result.tagged:
                jobs_tagged += 1
            if not create_result.inserted:
                duplicate_jobs_count += 1
                continue

            job = create_result.job
            inserted_jobs.append(job)
            extracted_content = self.extractor.extract_job_content(row.job_url)
            _store_extracted_content(self.job_repository, job, extracted_content)
            if extracted_content.extraction_success:
                extraction_success_count += 1
            else:
                extraction_failed_count += 1

        scanned_at = datetime.now(UTC)
        scanned_source = self.source_repository.mark_scanned(source, scanned_at)
        scan_run = self.scan_run_repository.create(
            {
                "user_id": source.user_id,
                "source_id": source.id,
                "scanned_jobs_count": len(parsed_rows),
                "inserted_jobs_count": len(inserted_jobs),
                "duplicate_jobs_count": duplicate_jobs_count,
                "rows_skipped_by_filters": rows_skipped_by_filters,
                "jobs_tagged": jobs_tagged,
                "extraction_success_count": extraction_success_count,
                "extraction_failed_count": extraction_failed_count,
            }
        )

        return GithubSourceScan(
            source=scanned_source,
            scan_run=scan_run,
            total_rows_seen=parse_result.total_rows_seen,
            parsed_jobs=len(parsed_rows),
            scanned_jobs=len(parsed_rows),
            inserted_job_records=inserted_jobs,
            inserted_jobs=len(inserted_jobs),
            duplicate_jobs=duplicate_jobs_count,
            rows_skipped_by_filters=rows_skipped_by_filters,
            jobs_tagged=jobs_tagged,
            extraction_success_count=extraction_success_count,
            extraction_failed_count=extraction_failed_count,
            matched_jobs=0,
            generated_resumes=0,
            uploaded_pdfs=0,
            message="GitHub source scan completed.",
        )


def _fetch_markdown(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/plain, text/markdown, */*",
            "User-Agent": "ApplyWise-AI/0.1",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            content = response.read(MAX_MARKDOWN_BYTES + 1)
    except HTTPError as error:
        raise GithubSourceScanError(
            f"GitHub returned HTTP {error.code} for the raw markdown URL.",
        ) from error
    except URLError as error:
        raise GithubSourceScanError("Could not fetch the raw markdown URL.") from error
    except TimeoutError as error:
        raise GithubSourceScanError("Fetching the raw markdown URL timed out.") from error

    if len(content) > MAX_MARKDOWN_BYTES:
        raise GithubSourceScanError("Raw markdown file is too large to scan.")

    return content.decode("utf-8", errors="replace")


def _create_github_job(
    *,
    job_service: JobPostingService,
    job_repository: JobPostingRepository,
    user_id: UUID,
    source: GithubJobSource,
    row: GithubJobRow,
    classification: JobRoleFilterResult,
    status_service: JobStatusService | None = None,
) -> GithubJobCreateResult:
    content_hash = compute_content_hash(
        company=row.company,
        title=row.title,
        location=row.location,
        job_url=row.job_url,
        description=None,
    )
    duplicate = job_service.find_duplicate(
        user_id=user_id,
        company=row.company,
        title=row.title,
        location=row.location,
        job_url=row.job_url,
        content_hash=content_hash,
    )
    if duplicate is not None:
        updated_duplicate = _merge_github_scan_metadata(
            job_repository=job_repository,
            job=duplicate,
            row=row,
            classification=classification,
        )
        return GithubJobCreateResult(
            job=updated_duplicate,
            inserted=False,
            tagged=bool(classification.job_tags),
        )

    values = {
        "user_id": user_id,
        "source": JobSource.GITHUB,
        "github_source_id": source.id,
        "source_repo_url": source.repo_url,
        "source_raw_url": source.raw_readme_url,
        "external_job_id": _external_job_id(source.id, row),
        "source_section": row.source_section,
        "job_tags": classification.job_tags,
        "scan_match_reason": classification.reason,
        "company": row.company,
        "title": row.title,
        "location": row.location,
        "job_url": row.job_url,
        "description": None,
        "raw_text": row.raw_text,
        "status": JobStatus.NEW,
        "content_hash": content_hash,
    }
    if status_service is not None:
        values["current_status_id"] = status_service.get_default_status(
            user_id,
            "New",
        ).id
    try:
        job = job_repository.create(values)
        if status_service is not None:
            status_service.record_initial_status(job=job)
        return GithubJobCreateResult(
            job=job,
            inserted=True,
            tagged=bool(classification.job_tags),
        )
    except IntegrityError:
        job_repository.rollback()
        duplicate = job_service.find_duplicate(
            user_id=user_id,
            company=row.company,
            title=row.title,
            location=row.location,
            job_url=row.job_url,
            content_hash=content_hash,
        )
        if duplicate is not None:
            updated_duplicate = _merge_github_scan_metadata(
                job_repository=job_repository,
                job=duplicate,
                row=row,
                classification=classification,
            )
            return GithubJobCreateResult(
                job=updated_duplicate,
                inserted=False,
                tagged=bool(classification.job_tags),
            )
        raise


def _merge_github_scan_metadata(
    *,
    job_repository: JobPostingRepository,
    job: JobPosting,
    row: GithubJobRow,
    classification: JobRoleFilterResult,
) -> JobPosting:
    update_values: dict[str, object] = {}
    current_tags = getattr(job, "job_tags", [])
    merged_tags = _merge_text_lists(current_tags, classification.job_tags)
    if merged_tags != (current_tags or []):
        update_values["job_tags"] = merged_tags
    if getattr(job, "source_section", None) is None and row.source_section is not None:
        update_values["source_section"] = row.source_section
    if getattr(job, "scan_match_reason", None) is None and classification.reason:
        update_values["scan_match_reason"] = classification.reason

    if not update_values:
        return job

    return job_repository.update(job, update_values)


def _merge_text_lists(current_values: list[str] | None, next_values: list[str]) -> list[str]:
    merged_values: list[str] = []
    seen_values: set[str] = set()
    for value in [*(current_values or []), *next_values]:
        cleaned_value = str(value).strip()
        normalized_value = cleaned_value.casefold()
        if cleaned_value == "" or normalized_value in seen_values:
            continue
        merged_values.append(cleaned_value)
        seen_values.add(normalized_value)

    return merged_values


def _store_extracted_content(
    job_repository: JobPostingRepository,
    job: JobPosting,
    extracted_content: ExtractedJobContent,
) -> JobPosting:
    extraction_status = (
        JobExtractionStatus.SUCCESS
        if extracted_content.extraction_success
        else JobExtractionStatus.FAILED
    )
    return job_repository.update(
        job,
        {
            "extracted_description": extracted_content.cleaned_text or None,
            "extraction_status": extraction_status,
            "extraction_error": extracted_content.error_message,
            "extracted_at": datetime.now(UTC),
            "posted_at": extracted_content.posted_at,
        },
    )


def _external_job_id(source_id: UUID, row: GithubJobRow) -> str:
    payload = f"{source_id}:{row.company}:{row.title}:{row.location or ''}:{row.job_url}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def count_recent_github_job_rows(markdown: str) -> int:
    return len(parse_recent_github_job_rows(markdown))


def parse_recent_github_job_rows(markdown: str, *, base_url: str = "") -> list[GithubJobRow]:
    return parse_recent_github_job_rows_with_summary(markdown, base_url=base_url).rows


def parse_recent_github_job_rows_with_summary(
    markdown: str,
    *,
    base_url: str = "",
) -> GithubJobParseResult:
    markdown_result = _parse_recent_markdown_table_rows(markdown, base_url=base_url)
    html_result = _parse_recent_html_table_rows(
        markdown,
        base_url=base_url,
    )
    return GithubJobParseResult(
        rows=markdown_result.rows + html_result.rows,
        total_rows_seen=markdown_result.total_rows_seen + html_result.total_rows_seen,
    )


def _parse_recent_markdown_table_rows(markdown: str, *, base_url: str) -> GithubJobParseResult:
    rows: list[GithubJobRow] = []
    total_rows_seen = 0
    headers: list[str] = []
    age_column_index: int | None = None
    last_company: str | None = None
    current_section: str | None = None

    for line in markdown.splitlines():
        if heading := _parse_markdown_heading(line):
            current_section = heading
            continue

        row = line.strip()
        if not _looks_like_table_row(row):
            continue
        if _looks_like_separator_row(row):
            continue

        cells = _split_markdown_table_row(row)
        raw_cells = _split_raw_markdown_table_row(row)
        next_age_column_index = _find_age_column_index(cells)
        if next_age_column_index is not None:
            headers = cells
            age_column_index = next_age_column_index
            continue
        if age_column_index is None or age_column_index >= len(cells):
            continue
        total_rows_seen += 1
        if not _is_recent_age(cells[age_column_index]):
            continue

        parsed_row = _row_from_cells(
            headers=headers,
            cells=cells,
            raw_cells=raw_cells,
            last_company=last_company,
            base_url=base_url,
            source_section=current_section,
        )
        if parsed_row is None:
            continue

        if parsed_row.company != "":
            last_company = parsed_row.company
        rows.append(parsed_row)

    return GithubJobParseResult(rows=rows, total_rows_seen=total_rows_seen)


def _parse_recent_html_table_rows(markdown: str, *, base_url: str) -> GithubJobParseResult:
    rows: list[GithubJobRow] = []
    total_rows_seen = 0
    soup = BeautifulSoup(markdown, "html.parser")

    for table in soup.find_all("table"):
        headers: list[str] = []
        age_column_index: int | None = None
        last_company: str | None = None
        for row in table.find_all("tr"):
            header_cells = [_clean_cell_text(cell.get_text(" ")) for cell in row.find_all("th", recursive=False)]
            if header_cells:
                headers = header_cells
                age_column_index = _find_age_column_index(header_cells)
                continue

            table_cells = row.find_all("td", recursive=False)
            cells = [_clean_cell_text(cell.get_text(" ")) for cell in table_cells]
            if not cells or age_column_index is None or age_column_index >= len(cells):
                continue
            total_rows_seen += 1
            if not _is_recent_age(cells[age_column_index]):
                continue

            parsed_row = _row_from_cells(
                headers=headers,
                cells=cells,
                raw_cells=[str(cell) for cell in table_cells],
                last_company=last_company,
                base_url=base_url,
            )
            if parsed_row is None:
                continue

            if parsed_row.company != "":
                last_company = parsed_row.company
            rows.append(parsed_row)

    return GithubJobParseResult(rows=rows, total_rows_seen=total_rows_seen)


def _row_from_cells(
    *,
    headers: list[str],
    cells: list[str],
    raw_cells: list[str],
    last_company: str | None,
    base_url: str,
    source_section: str | None = None,
) -> GithubJobRow | None:
    company_index = _find_named_column_index(headers, {"company", "employer"})
    title_index = _find_named_column_index(headers, {"role", "title", "position", "job"})
    location_index = _find_named_column_index(headers, {"location", "locations"})
    apply_index = _find_named_column_index(
        headers,
        {"application", "apply", "link", "url", "job url"},
    )

    if company_index is None or title_index is None or apply_index is None:
        return None
    if company_index >= len(cells) or title_index >= len(cells) or apply_index >= len(raw_cells):
        return None

    company = cells[company_index]
    if company in {"↳", "↪", "->", "—", "-"}:
        company = last_company or ""
    title = cells[title_index]
    location = cells[location_index] if location_index is not None and location_index < len(cells) else None
    job_url = _extract_apply_url(raw_cells[apply_index], base_url=base_url)
    if company.strip() == "" or title.strip() == "" or job_url is None:
        return None

    return GithubJobRow(
        company=_truncate_text(company, JOB_TEXT_COLUMN_MAX_LENGTH),
        title=_truncate_text(title, JOB_TEXT_COLUMN_MAX_LENGTH),
        location=_truncate_text(location, JOB_TEXT_COLUMN_MAX_LENGTH) if location else None,
        job_url=_truncate_text(job_url, JOB_URL_COLUMN_MAX_LENGTH),
        raw_text=" | ".join(cells),
        source_section=_truncate_text(source_section, JOB_TEXT_COLUMN_MAX_LENGTH * 2) if source_section else None,
    )


def _find_named_column_index(headers: list[str], names: set[str]) -> int | None:
    normalized_names = {_normalize_header(name) for name in names}
    for index, header in enumerate(headers):
        if _normalize_header(header) in normalized_names:
            return index

    return None


def _extract_apply_url(raw_cell: str, *, base_url: str) -> str | None:
    if match := re.search(r"<a\b[^>]*href=[\"']([^\"']+)[\"']", raw_cell, flags=re.IGNORECASE):
        return _absolute_url(match.group(1), base_url)
    if match := re.search(r"\[[^\]]*\]\((https?://[^)]+)\)", raw_cell):
        return _absolute_url(match.group(1), base_url)
    if match := re.search(r"https?://[^\s)\"']+", raw_cell):
        return _absolute_url(match.group(0), base_url)

    return None


def _absolute_url(url: str, base_url: str) -> str:
    return urljoin(base_url, unescape(url.strip()))


def _truncate_text(value: str, max_length: int) -> str:
    cleaned_value = value.strip()
    if len(cleaned_value) <= max_length:
        return cleaned_value

    return cleaned_value[:max_length].rstrip()


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _split_markdown_table_row(row: str) -> list[str]:
    return [_clean_cell_text(cell) for cell in _split_raw_markdown_table_row(row)]


def _split_raw_markdown_table_row(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _find_age_column_index(cells: list[str]) -> int | None:
    for index, cell in enumerate(cells):
        if _clean_cell_text(cell).casefold() == "age":
            return index

    return None


def _is_recent_age(value: str) -> bool:
    cleaned_value = _clean_cell_text(value).casefold()
    compact_value = re.sub(r"\s+", "", cleaned_value)
    if compact_value in {"new", "today", "justposted"}:
        return True
    if compact_value == "yesterday":
        return True

    if match := re.search(r"(\d+)(?:d|day|days)", compact_value):
        return int(match.group(1)) <= RECENT_JOB_MAX_AGE_DAYS
    if match := re.search(r"(\d+)(?:h|hr|hrs|hour|hours)", compact_value):
        return True
    if match := re.search(r"(\d+)(?:w|wk|wks|week|weeks)", compact_value):
        return int(match.group(1)) * 7 <= RECENT_JOB_MAX_AGE_DAYS
    if re.search(r"\d+(?:mo|mon|month|months)", compact_value):
        return False

    return False


def _clean_cell_text(value: str) -> str:
    without_html = re.sub(r"<[^>]+>", " ", value)
    without_markdown_images = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", without_html)
    without_markdown_links = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", without_markdown_images)
    return re.sub(r"\s+", " ", without_markdown_links).strip()


def _looks_like_table_row(row: str) -> bool:
    return row.startswith("|") and row.endswith("|") and row.count("|") >= 3


def _looks_like_separator_row(row: str) -> bool:
    characters = set(row.replace("|", "").replace(" ", ""))
    return len(characters) > 0 and characters.issubset({"-", ":"})


def _parse_markdown_heading(line: str) -> str | None:
    if match := re.match(r"^#{1,6}\s+(.+?)\s*$", line.strip()):
        heading = re.sub(r"\s+#*$", "", match.group(1)).strip()
        return heading or None

    return None
