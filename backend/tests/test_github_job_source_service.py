from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from app.models.job_posting import JobExtractionStatus
from app.services.github_job_source_service import (
    GithubJobSourceService,
    count_recent_github_job_rows,
    parse_recent_github_job_rows,
    parse_recent_github_job_rows_with_summary,
)
from app.services.jobs.job_content_extractor import ExtractedJobContent


class GithubJobSourceServiceTests(unittest.TestCase):
    def test_counts_only_markdown_rows_with_age_at_or_under_seven_days(self) -> None:
        markdown = """
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Intern | Remote | [Apply](https://example.com/1) | 0d |
        | Beta | Frontend Intern | NYC | [Apply](https://example.com/2) | 7d |
        | Gamma | Data Intern | SF | [Apply](https://example.com/3) | 8d |
        | Delta | ML Intern | Austin | [Apply](https://example.com/4) | 1mo |
        """

        self.assertEqual(count_recent_github_job_rows(markdown), 2)

    def test_parse_summary_counts_all_table_rows_seen_before_age_filter(self) -> None:
        markdown = """
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Intern | Remote | [Apply](https://example.com/1) | 0d |
        | Beta | Frontend Intern | NYC | [Apply](https://example.com/2) | 8d |
        | Gamma | Data Intern | SF | [Apply](https://example.com/3) | 1mo |
        """

        result = parse_recent_github_job_rows_with_summary(markdown)

        self.assertEqual(result.total_rows_seen, 3)
        self.assertEqual(len(result.rows), 1)

    def test_parses_markdown_job_row_fields(self) -> None:
        markdown = """
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Intern | Remote | [Apply](https://example.com/1) | 0d |
        | Beta | Frontend Intern | NYC | [Apply](https://example.com/2) | 8d |
        """

        rows = parse_recent_github_job_rows(markdown)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].company, "Acme")
        self.assertEqual(rows[0].title, "Backend Intern")
        self.assertEqual(rows[0].location, "Remote")
        self.assertEqual(rows[0].job_url, "https://example.com/1")

    def test_captures_markdown_section_heading_for_rows(self) -> None:
        markdown = """
        ## Software Engineering Internship Roles
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Intern | Remote | [Apply](https://example.com/1) | 0d |
        """

        rows = parse_recent_github_job_rows(markdown)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source_section, "Software Engineering Internship Roles")

    def test_truncates_long_database_fields_and_unescapes_apply_url(self) -> None:
        long_location = " ".join(f"Location {index}" for index in range(80))
        markdown = f"""
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Intern | {long_location} | <a href="https://example.com/jobs?id=1&amp;source=github">Apply</a> | 0d |
        """

        rows = parse_recent_github_job_rows(markdown)

        self.assertEqual(len(rows), 1)
        self.assertLessEqual(len(rows[0].location or ""), 255)
        self.assertEqual(rows[0].job_url, "https://example.com/jobs?id=1&source=github")

    def test_counts_html_rows_using_age_column(self) -> None:
        markdown = """
        <table>
          <thead>
            <tr>
              <th>Company</th>
              <th>Role</th>
              <th>Location</th>
              <th>Application</th>
              <th>Age</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Acme</td>
              <td>Backend Intern</td>
              <td>Remote</td>
              <td><a href="https://example.com/1">Apply</a></td>
              <td>3d</td>
            </tr>
            <tr>
              <td>Beta</td>
              <td>Frontend Intern</td>
              <td>Remote</td>
              <td><a href="https://example.com/2">Apply</a></td>
              <td>3w</td>
            </tr>
          </tbody>
        </table>
        """

        self.assertEqual(count_recent_github_job_rows(markdown), 1)

    def test_parses_html_job_row_fields_and_reuses_arrow_company(self) -> None:
        markdown = """
        <table>
          <tr>
            <th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th>
          </tr>
          <tr>
            <td>Acme</td><td>Backend Intern</td><td>Remote</td>
            <td><a href="https://example.com/1">Apply</a></td><td>3d</td>
          </tr>
          <tr>
            <td>↳</td><td>Platform Intern</td><td>Remote</td>
            <td><a href="https://example.com/2">Apply</a></td><td>4d</td>
          </tr>
        </table>
        """

        rows = parse_recent_github_job_rows(markdown)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].company, "Acme")
        self.assertEqual(rows[1].title, "Platform Intern")

    def test_supports_common_recent_age_labels(self) -> None:
        markdown = """
        | Company | Role | Application | Age |
        | --- | --- | --- | --- |
        | Acme | Backend Intern | [Apply](https://example.com/1) | Today |
        | Beta | Frontend Intern | [Apply](https://example.com/2) | Yesterday |
        | Gamma | Data Intern | [Apply](https://example.com/3) | 12 hours |
        | Delta | ML Intern | [Apply](https://example.com/4) | 1 week |
        | Epsilon | Platform Intern | [Apply](https://example.com/5) | 4 weeks |
        """

        self.assertEqual(count_recent_github_job_rows(markdown), 4)

    def test_rows_without_age_column_are_not_counted(self) -> None:
        markdown = """
        | Company | Role | Location |
        | --- | --- | --- |
        | Acme | Backend Intern | Remote |
        """

        self.assertEqual(count_recent_github_job_rows(markdown), 0)

    def test_scan_inserts_new_jobs_and_extracts_only_new_jobs(self) -> None:
        user_id = uuid4()
        source_id = uuid4()
        markdown = """
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Existing | Backend Intern | Remote | [Apply](https://example.com/duplicate) | 0d |
        | Acme | Platform Intern | Remote | [Apply](https://example.com/new1) | 1d |
        | Beta | Data Intern | NYC | [Apply](https://example.com/new2) | 2d |
        """
        source = SimpleNamespace(
            id=source_id,
            user_id=user_id,
            enabled=True,
            repo_url="https://github.com/example/jobs",
            raw_readme_url="https://raw.githubusercontent.com/example/jobs/main/README.md",
        )
        job_repository = FakeJobPostingRepository(
            existing_jobs=[
                SimpleNamespace(
                    id=uuid4(),
                    user_id=user_id,
                    job_url="https://example.com/duplicate",
                    content_hash="existing",
                    company="Existing",
                    title="Backend Intern",
                    location="Remote",
                )
            ]
        )
        source_repository = FakeGithubJobSourceRepository()
        scan_run_repository = FakeGithubScanRunRepository()
        extractor = FakeJobContentExtractor()
        service = GithubJobSourceService(
            source_repository=source_repository,
            job_repository=job_repository,
            scan_run_repository=scan_run_repository,
            extractor=extractor,
        )

        with patch(
            "app.services.github_job_source_service._fetch_markdown",
            return_value=markdown,
        ):
            result = service.scan_source(source)

        self.assertEqual(result.scanned_jobs, 3)
        self.assertEqual(result.inserted_jobs, 2)
        self.assertEqual(result.duplicate_jobs, 1)
        self.assertEqual(result.extraction_success_count, 1)
        self.assertEqual(result.extraction_failed_count, 1)
        self.assertEqual(len(extractor.seen_urls), 2)
        self.assertEqual(scan_run_repository.created_values["extraction_success_count"], 1)
        self.assertEqual(
            job_repository.created_jobs[0].extraction_status,
            JobExtractionStatus.SUCCESS,
        )
        self.assertEqual(
            job_repository.created_jobs[1].extraction_status,
            JobExtractionStatus.FAILED,
        )

    def test_scan_applies_include_keyword_filter(self) -> None:
        user_id = uuid4()
        source = _source(
            user_id=user_id,
            include_keywords=["backend engineer"],
        )
        markdown = """
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Engineer Intern | Remote | [Apply](https://example.com/backend) | 0d |
        | Beta | Product Manager Intern | Remote | [Apply](https://example.com/product) | 0d |
        """
        job_repository = FakeJobPostingRepository(existing_jobs=[])
        service = GithubJobSourceService(
            source_repository=FakeGithubJobSourceRepository(),
            job_repository=job_repository,
            scan_run_repository=FakeGithubScanRunRepository(),
            extractor=FakeJobContentExtractor(),
        )

        with patch(
            "app.services.github_job_source_service._fetch_markdown",
            return_value=markdown,
        ):
            result = service.scan_source(source)

        self.assertEqual(result.rows_skipped_by_filters, 1)
        self.assertEqual(result.inserted_jobs, 1)
        self.assertEqual(job_repository.created_jobs[0].title, "Backend Engineer Intern")

    def test_scan_applies_exclude_keyword_filter(self) -> None:
        user_id = uuid4()
        source = _source(
            user_id=user_id,
            exclude_keywords=["product manager"],
        )
        markdown = """
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Engineer Intern | Remote | [Apply](https://example.com/backend) | 0d |
        | Beta | Product Manager Intern | Remote | [Apply](https://example.com/product) | 0d |
        """
        job_repository = FakeJobPostingRepository(existing_jobs=[])
        service = GithubJobSourceService(
            source_repository=FakeGithubJobSourceRepository(),
            job_repository=job_repository,
            scan_run_repository=FakeGithubScanRunRepository(),
            extractor=FakeJobContentExtractor(),
        )

        with patch(
            "app.services.github_job_source_service._fetch_markdown",
            return_value=markdown,
        ):
            result = service.scan_source(source)

        self.assertEqual(result.rows_skipped_by_filters, 1)
        self.assertEqual(result.inserted_jobs, 1)
        self.assertEqual(job_repository.created_jobs[0].title, "Backend Engineer Intern")

    def test_scan_assigns_matching_role_tags(self) -> None:
        user_id = uuid4()
        source = _source(
            user_id=user_id,
            scan_role_tags=["Software Engineering", "Backend", "Machine Learning"],
        )
        markdown = """
        ## Software Engineering Internship Roles
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Engineer Intern | Remote | [Apply](https://example.com/backend) | 0d |
        """
        job_repository = FakeJobPostingRepository(existing_jobs=[])
        service = GithubJobSourceService(
            source_repository=FakeGithubJobSourceRepository(),
            job_repository=job_repository,
            scan_run_repository=FakeGithubScanRunRepository(),
            extractor=FakeJobContentExtractor(),
        )

        with patch(
            "app.services.github_job_source_service._fetch_markdown",
            return_value=markdown,
        ):
            result = service.scan_source(source)

        self.assertEqual(result.jobs_tagged, 1)
        self.assertIn("Software Engineering", job_repository.created_jobs[0].job_tags)
        self.assertIn("Backend", job_repository.created_jobs[0].job_tags)
        self.assertEqual(
            job_repository.created_jobs[0].source_section,
            "Software Engineering Internship Roles",
        )

    def test_duplicate_scan_merges_tags_and_source_section(self) -> None:
        user_id = uuid4()
        existing_job = SimpleNamespace(
            id=uuid4(),
            user_id=user_id,
            job_url="https://example.com/backend",
            content_hash="existing",
            company="Acme",
            title="Backend Engineer Intern",
            location="Remote",
            job_tags=["Existing"],
            source_section=None,
            scan_match_reason=None,
        )
        source = _source(
            user_id=user_id,
            scan_role_tags=["Backend"],
            include_keywords=["backend"],
        )
        markdown = """
        ## Software Engineering Internship Roles
        | Company | Role | Location | Application | Age |
        | --- | --- | --- | --- | --- |
        | Acme | Backend Engineer Intern | Remote | [Apply](https://example.com/backend) | 0d |
        """
        job_repository = FakeJobPostingRepository(existing_jobs=[existing_job])
        extractor = FakeJobContentExtractor()
        service = GithubJobSourceService(
            source_repository=FakeGithubJobSourceRepository(),
            job_repository=job_repository,
            scan_run_repository=FakeGithubScanRunRepository(),
            extractor=extractor,
        )

        with patch(
            "app.services.github_job_source_service._fetch_markdown",
            return_value=markdown,
        ):
            result = service.scan_source(source)

        self.assertEqual(result.duplicate_jobs, 1)
        self.assertEqual(result.inserted_jobs, 0)
        self.assertEqual(extractor.seen_urls, [])
        self.assertEqual(existing_job.job_tags, ["Existing", "Backend"])
        self.assertEqual(existing_job.source_section, "Software Engineering Internship Roles")


class FakeGithubJobSourceRepository:
    def mark_scanned(self, source: SimpleNamespace, scanned_at: datetime) -> SimpleNamespace:
        source.last_scanned_at = scanned_at
        return source


class FakeGithubScanRunRepository:
    def __init__(self) -> None:
        self.created_values: dict[str, object] = {}

    def create(self, values: dict[str, object]) -> SimpleNamespace:
        self.created_values = values
        return SimpleNamespace(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **values,
        )


class FakeJobPostingRepository:
    def __init__(self, existing_jobs: list[SimpleNamespace]) -> None:
        self.jobs = list(existing_jobs)
        self.created_jobs: list[SimpleNamespace] = []

    def list_by_user(self, user_id):
        return [job for job in self.jobs if job.user_id == user_id]

    def find_by_job_url(self, *, user_id, job_url, exclude_job_id=None):
        for job in self.jobs:
            if job.user_id == user_id and job.job_url == job_url:
                return job
        return None

    def find_by_content_hash(self, *, user_id, content_hash, exclude_job_id=None):
        for job in self.jobs:
            if job.user_id == user_id and job.content_hash == content_hash:
                return job
        return None

    def create(self, values: dict[str, object]) -> SimpleNamespace:
        job = SimpleNamespace(id=uuid4(), **values)
        self.jobs.append(job)
        self.created_jobs.append(job)
        return job

    def update(self, job: SimpleNamespace, values: dict[str, object]) -> SimpleNamespace:
        for field, value in values.items():
            setattr(job, field, value)
        return job

    def rollback(self) -> None:
        return None


class FakeJobContentExtractor:
    def __init__(self) -> None:
        self.seen_urls: list[str] = []

    def extract_job_content(self, job_url: str) -> ExtractedJobContent:
        self.seen_urls.append(job_url)
        if job_url.endswith("/new1"):
            return ExtractedJobContent(
                cleaned_text="Responsibilities\n- Build backend services",
                page_title="Platform Intern",
                company_guess="Acme",
                extraction_success=True,
                extraction_method="test",
            )

        return ExtractedJobContent(
            cleaned_text="Fallback text",
            page_title="Data Intern",
            company_guess="Beta",
            extraction_success=False,
            extraction_method="test",
            error_message="Could not extract a meaningful job description.",
        )


def _source(
    *,
    user_id,
    include_keywords=None,
    exclude_keywords=None,
    scan_role_tags=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        enabled=True,
        repo_url="https://github.com/example/jobs",
        raw_readme_url="https://raw.githubusercontent.com/example/jobs/main/README.md",
        include_keywords=include_keywords or [],
        exclude_keywords=exclude_keywords or [],
        scan_role_tags=scan_role_tags or [],
        scan_instructions=None,
    )


if __name__ == "__main__":
    unittest.main()
