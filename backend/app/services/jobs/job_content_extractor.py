from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, time as datetime_time
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag

try:
    from readability import Document
except ImportError:  # pragma: no cover - dependency is optional at runtime
    Document = None  # type: ignore[assignment]


MIN_MEANINGFUL_TEXT_LENGTH = 120
MAX_HTML_BYTES = 4 * 1024 * 1024
REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=6.0)
RETRY_ATTEMPTS = 3


@dataclass(frozen=True)
class ExtractedJobContent:
    cleaned_text: str
    page_title: str
    company_guess: str | None
    extraction_success: bool
    extraction_method: str
    raw_html: str | None = None
    error_message: str | None = None
    title_guess: str | None = None
    location_guess: str | None = None
    posted_at: datetime | None = None


@dataclass(frozen=True)
class ExtractionCandidate:
    text: str
    method: str
    company_guess: str | None = None
    title_guess: str | None = None
    location_guess: str | None = None
    posted_at: datetime | None = None


class JobContentExtractorService:
    def __init__(self, *, include_raw_html: bool = False) -> None:
        self.include_raw_html = include_raw_html

    def extract_job_content(self, job_url: str) -> ExtractedJobContent:
        try:
            raw_html = _fetch_html(job_url)
        except httpx.HTTPStatusError as error:
            return _failed_result(
                error_message=f"Job page returned HTTP {error.response.status_code}.",
                method="http_error",
            )
        except httpx.RequestError as error:
            return _failed_result(
                error_message=f"Could not fetch job page: {error.__class__.__name__}.",
                method="fetch_error",
            )
        except UnicodeDecodeError as error:
            return _failed_result(
                error_message="Could not decode job page HTML.",
                method="decode_error",
            )

        result = extract_job_content_from_html(
            raw_html,
            page_url=job_url,
            include_raw_html=self.include_raw_html,
        )
        if self.include_raw_html:
            return result

        return ExtractedJobContent(
            cleaned_text=result.cleaned_text,
            page_title=result.page_title,
            company_guess=result.company_guess,
            extraction_success=result.extraction_success,
            extraction_method=result.extraction_method,
            raw_html=None,
            error_message=result.error_message,
            title_guess=result.title_guess,
            location_guess=result.location_guess,
            posted_at=result.posted_at,
        )


def extract_job_content(job_url: str) -> ExtractedJobContent:
    return JobContentExtractorService().extract_job_content(job_url)


def extract_job_content_from_html(
    html: str,
    *,
    page_url: str = "",
    include_raw_html: bool = False,
) -> ExtractedJobContent:
    soup = BeautifulSoup(html, "html.parser")
    page_title = _clean_inline_text(soup.title.get_text(" ")) if soup.title else ""
    company_guess = _extract_company_guess(soup)
    title_guess = _extract_title_guess(soup, page_title)
    posted_at = _extract_posted_at(soup)

    json_ld_candidate = _extract_json_ld_job_posting(soup)
    if json_ld_candidate is not None and _is_meaningful_text(json_ld_candidate.text):
        return _success_result(
            candidate=_with_company_guess(json_ld_candidate, company_guess),
            page_title=page_title,
            title_guess=title_guess,
            posted_at=posted_at,
            raw_html=html if include_raw_html else None,
        )

    _remove_non_content_elements(soup)
    candidates = _domain_candidates(soup, page_url)
    readability_candidate = _readability_candidate(str(soup))
    if readability_candidate is not None:
        candidates.append(readability_candidate)

    body_text = _html_to_text(soup.body if soup.body is not None else soup)
    if body_text:
        candidates.append(ExtractionCandidate(text=body_text, method="generic_body"))

    best_candidate = _select_best_candidate(candidates)
    if best_candidate is not None and _is_meaningful_text(best_candidate.text):
        return _success_result(
            candidate=_with_company_guess(best_candidate, company_guess),
            page_title=page_title,
            title_guess=title_guess,
            posted_at=posted_at,
            raw_html=html if include_raw_html else None,
        )

    fallback_text = best_candidate.text if best_candidate is not None else body_text
    fallback_method = best_candidate.method if best_candidate is not None else "no_content"
    return ExtractedJobContent(
        cleaned_text=fallback_text,
        page_title=page_title,
        company_guess=company_guess,
        extraction_success=False,
        extraction_method=fallback_method,
        raw_html=html if include_raw_html else None,
        error_message="Could not extract a meaningful job description.",
        title_guess=title_guess,
        location_guess=None,
        posted_at=posted_at,
    )


def _fetch_html(job_url: str) -> str:
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "ApplyWise-AI/0.1 job-content-extractor",
    }
    last_error: httpx.RequestError | None = None
    with httpx.Client(
        follow_redirects=True,
        headers=headers,
        max_redirects=5,
        timeout=REQUEST_TIMEOUT,
    ) as client:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                response = client.get(job_url)
                response.raise_for_status()
                content = response.content[: MAX_HTML_BYTES + 1]
                if len(content) > MAX_HTML_BYTES:
                    raise httpx.RequestError("Job page HTML is too large.")
                return content.decode(response.encoding or "utf-8", errors="replace")
            except httpx.HTTPStatusError:
                raise
            except httpx.RequestError as error:
                last_error = error
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(0.35 * (attempt + 1))

    if last_error is not None:
        raise last_error

    raise httpx.RequestError("Could not fetch job page.")


def _extract_json_ld_job_posting(soup: BeautifulSoup) -> ExtractionCandidate | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_json = script.string or script.get_text()
        if raw_json.strip() == "":
            continue

        for payload in _iter_json_objects(raw_json):
            job_payload = _find_job_posting_payload(payload)
            if job_payload is None:
                continue

            description = str(job_payload.get("description") or "")
            text = _html_to_text(description)
            company_guess = _jsonld_company_name(job_payload)
            title_guess = _clean_jsonld_text(job_payload.get("title"))
            location_guess = _jsonld_location(job_payload)
            posted_at = _parse_posted_datetime(job_payload.get("datePosted"))
            if text:
                return ExtractionCandidate(
                    text=text,
                    method="json_ld_job_posting",
                    company_guess=company_guess,
                    title_guess=title_guess,
                    location_guess=location_guess,
                    posted_at=posted_at,
                )

    return None


def _iter_json_objects(raw_json: str) -> list[Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    return payload if isinstance(payload, list) else [payload]


def _find_job_posting_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    payload_type = payload.get("@type")
    if _contains_job_posting_type(payload_type):
        return payload

    graph = payload.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            found_payload = _find_job_posting_payload(item)
            if found_payload is not None:
                return found_payload

    return None


def _contains_job_posting_type(value: Any) -> bool:
    if isinstance(value, str):
        return value.casefold() == "jobposting"
    if isinstance(value, list):
        return any(_contains_job_posting_type(item) for item in value)

    return False


def _jsonld_company_name(payload: dict[str, Any]) -> str | None:
    organization = payload.get("hiringOrganization")
    if isinstance(organization, dict):
        name = organization.get("name")
        if isinstance(name, str) and name.strip():
            return _clean_inline_text(name)

    return None


def _jsonld_location(payload: dict[str, Any]) -> str | None:
    location = payload.get("jobLocation")
    if isinstance(location, list):
        location_parts = [
            cleaned_location
            for item in location
            if (cleaned_location := _jsonld_location({"jobLocation": item})) is not None
        ]
        return ", ".join(location_parts) if location_parts else None

    if isinstance(location, str):
        return _clean_jsonld_text(location)

    if not isinstance(location, dict):
        return None

    address = location.get("address")
    if isinstance(address, str):
        return _clean_jsonld_text(address)
    if not isinstance(address, dict):
        return None

    parts = [
        _clean_jsonld_text(address.get("addressLocality")),
        _clean_jsonld_text(address.get("addressRegion")),
        _clean_jsonld_text(address.get("addressCountry")),
    ]
    location_text = ", ".join(part for part in parts if part is not None)
    return location_text or None


def _clean_jsonld_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned_value = _clean_inline_text(value)
    return cleaned_value or None


def _domain_candidates(soup: BeautifulSoup, page_url: str) -> list[ExtractionCandidate]:
    host = urlparse(page_url).netloc.casefold()
    rules = _domain_rules(host)
    candidates: list[ExtractionCandidate] = []

    for method, selectors in rules:
        candidates.extend(_selector_candidates(soup, method, selectors))

    candidates.extend(
        _selector_candidates(
            soup,
            "generic_selectors",
            [
                "[itemprop='description']",
                "[data-testid*='job']",
                "[class*='job-description']",
                "[class*='jobDescription']",
                "[class*='job-posting']",
                "[class*='description']",
                "[role='main']",
                "main",
                "article",
            ],
        )
    )
    return candidates


def _domain_rules(host: str) -> list[tuple[str, list[str]]]:
    if "greenhouse.io" in host:
        return [
            (
                "greenhouse_selectors",
                ["#content", "#app_body", ".app-body", ".opening", "main"],
            )
        ]
    if "lever.co" in host:
        return [
            (
                "lever_selectors",
                [".posting-page", ".posting", ".section-wrapper", ".content", "main"],
            )
        ]
    if "workdayjobs.com" in host or "myworkdayjobs.com" in host:
        return [
            (
                "workday_selectors",
                [
                    "[data-automation-id='jobPostingHeader']",
                    "[data-automation-id='jobPostingDescription']",
                    "[data-automation-id='jobPosting']",
                    "main",
                ],
            )
        ]
    if "ashbyhq.com" in host:
        return [
            (
                "ashby_selectors",
                [
                    "[data-testid='job-posting']",
                    "[class*='job-posting']",
                    "[class*='ashby']",
                    "main",
                ],
            )
        ]
    if "smartrecruiters.com" in host:
        return [
            (
                "smartrecruiters_selectors",
                [".job-sections", "[itemprop='description']", ".description", "section", "main"],
            )
        ]

    return []


def _selector_candidates(
    soup: BeautifulSoup,
    method: str,
    selectors: list[str],
) -> list[ExtractionCandidate]:
    candidates: list[ExtractionCandidate] = []
    for selector in selectors:
        for element in soup.select(selector):
            if not isinstance(element, Tag):
                continue

            text = _html_to_text(element)
            if text:
                candidates.append(
                    ExtractionCandidate(
                        text=text,
                        method=f"{method}:{selector}",
                    )
                )

    return candidates


def _readability_candidate(html: str) -> ExtractionCandidate | None:
    if Document is None:
        return None

    try:
        document = Document(html)
        summary_html = document.summary(html_partial=True)
    except Exception:
        return None

    text = _html_to_text(summary_html)
    if text:
        return ExtractionCandidate(text=text, method="readability_lxml")

    return None


def _select_best_candidate(candidates: list[ExtractionCandidate]) -> ExtractionCandidate | None:
    if not candidates:
        return None

    return max(candidates, key=_score_candidate)


def _score_candidate(candidate: ExtractionCandidate) -> int:
    method = candidate.method
    method_bonus = 0
    if method.startswith(
        (
            "greenhouse_selectors",
            "lever_selectors",
            "workday_selectors",
            "ashby_selectors",
            "smartrecruiters_selectors",
        )
    ):
        method_bonus = 3000
    elif method.startswith("generic_selectors"):
        method_bonus = 1500
    elif method == "readability_lxml":
        method_bonus = 500

    return _score_text(candidate.text) + method_bonus


def _score_text(text: str) -> int:
    lowered_text = text.casefold()
    keyword_score = sum(
        80
        for keyword in [
            "responsibilities",
            "requirements",
            "qualifications",
            "experience",
            "skills",
            "about the role",
            "what you'll do",
            "what you will do",
        ]
        if keyword in lowered_text
    )
    bullet_score = min(600, text.count("\n- ") * 45)
    return len(text) + keyword_score + bullet_score


def _is_meaningful_text(text: str) -> bool:
    if len(text) >= MIN_MEANINGFUL_TEXT_LENGTH:
        return True

    lowered_text = text.casefold()
    return (
        len(text) >= 80
        and "requirements" in lowered_text
        and ("responsibilities" in lowered_text or "qualifications" in lowered_text)
    )


def _remove_non_content_elements(soup: BeautifulSoup) -> None:
    for selector in [
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "canvas",
        "iframe",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "[aria-hidden='true']",
        "[hidden]",
        ".cookie",
        ".cookies",
        ".breadcrumb",
        ".breadcrumbs",
        ".social",
        ".share",
    ]:
        for element in soup.select(selector):
            element.decompose()


def _html_to_text(value: str | Tag | BeautifulSoup) -> str:
    soup = BeautifulSoup(value, "html.parser") if isinstance(value, str) else value
    for element in soup.find_all(["script", "style", "noscript", "template"]):
        element.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")

    for item in soup.find_all("li"):
        item.insert_before("\n- ")
        item.append("\n")

    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        heading.insert_before("\n\n")
        heading.append("\n")

    for block in soup.find_all(["p", "div", "section", "article", "tr"]):
        block.append("\n")

    text = soup.get_text("\n")
    return _clean_multiline_text(text)


def _clean_multiline_text(text: str) -> str:
    cleaned_lines: list[str] = []
    previous_blank = False
    pending_bullet = False
    for line in text.splitlines():
        cleaned_line = _clean_inline_text(line)
        if cleaned_line == "":
            if not previous_blank and cleaned_lines:
                cleaned_lines.append("")
            previous_blank = True
            continue

        if cleaned_line == "-":
            pending_bullet = True
            previous_blank = False
            continue

        if pending_bullet:
            cleaned_line = f"- {cleaned_line}"
            pending_bullet = False

        cleaned_lines.append(cleaned_line)
        previous_blank = False

    return "\n".join(cleaned_lines).strip()


def _clean_inline_text(text: str) -> str:
    return re.sub(r"[ \t\xa0]+", " ", text).strip()


def _extract_company_guess(soup: BeautifulSoup) -> str | None:
    site_name = soup.find("meta", attrs={"property": "og:site_name"})
    if site_name is not None:
        content = site_name.get("content")
        if isinstance(content, str) and content.strip():
            return _clean_inline_text(content)

    return None


def _extract_title_guess(soup: BeautifulSoup, page_title: str) -> str | None:
    for attrs in [
        {"property": "og:title"},
        {"name": "twitter:title"},
    ]:
        element = soup.find("meta", attrs=attrs)
        if element is None:
            continue

        content = element.get("content")
        if isinstance(content, str) and content.strip():
            return _clean_inline_text(content)

    heading = soup.find("h1")
    if heading is not None:
        heading_text = _clean_inline_text(heading.get_text(" "))
        if heading_text:
            return heading_text

    return page_title or None


def _extract_posted_at(soup: BeautifulSoup) -> datetime | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_json = script.string or script.get_text()
        if raw_json.strip() == "":
            continue

        for payload in _iter_json_objects(raw_json):
            job_payload = _find_job_posting_payload(payload)
            if job_payload is None:
                continue

            posted_at = _parse_posted_datetime(job_payload.get("datePosted"))
            if posted_at is not None:
                return posted_at

    meta_selectors = [
        {"property": "article:published_time"},
        {"property": "og:published_time"},
        {"name": "date"},
        {"name": "publishdate"},
        {"name": "published_date"},
        {"name": "datePosted"},
    ]
    for attrs in meta_selectors:
        element = soup.find("meta", attrs=attrs)
        if element is None:
            continue

        content = element.get("content")
        if not isinstance(content, str):
            continue

        posted_at = _parse_posted_datetime(content)
        if posted_at is not None:
            return posted_at

    for element in soup.find_all("time"):
        datetime_value = element.get("datetime")
        if isinstance(datetime_value, str):
            posted_at = _parse_posted_datetime(datetime_value)
            if posted_at is not None:
                return posted_at

    return None


def _parse_posted_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    cleaned_value = value.strip()
    if cleaned_value == "":
        return None

    normalized_value = cleaned_value.replace("Z", "+00:00")
    try:
        parsed_datetime = datetime.fromisoformat(normalized_value)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(cleaned_value[:10])
        except ValueError:
            return None

        return datetime.combine(parsed_date, datetime_time.min, tzinfo=UTC)

    if parsed_datetime.tzinfo is None:
        return parsed_datetime.replace(tzinfo=UTC)

    return parsed_datetime


def _success_result(
    *,
    candidate: ExtractionCandidate,
    page_title: str,
    title_guess: str | None,
    posted_at: datetime | None,
    raw_html: str | None,
) -> ExtractedJobContent:
    return ExtractedJobContent(
        cleaned_text=candidate.text,
        page_title=page_title,
        company_guess=candidate.company_guess,
        extraction_success=True,
        extraction_method=candidate.method,
        raw_html=raw_html,
        error_message=None,
        title_guess=candidate.title_guess or title_guess,
        location_guess=candidate.location_guess,
        posted_at=candidate.posted_at or posted_at,
    )


def _with_company_guess(
    candidate: ExtractionCandidate,
    company_guess: str | None,
) -> ExtractionCandidate:
    if candidate.company_guess is not None:
        return candidate

    return ExtractionCandidate(
        text=candidate.text,
        method=candidate.method,
        company_guess=company_guess,
        title_guess=candidate.title_guess,
        location_guess=candidate.location_guess,
        posted_at=candidate.posted_at,
    )


def _failed_result(*, error_message: str, method: str) -> ExtractedJobContent:
    return ExtractedJobContent(
        cleaned_text="",
        page_title="",
        company_guess=None,
        extraction_success=False,
        extraction_method=method,
        raw_html=None,
        error_message=error_message,
        title_guess=None,
        location_guess=None,
        posted_at=None,
    )
