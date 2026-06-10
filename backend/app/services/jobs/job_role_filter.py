from dataclasses import dataclass
import re

from rapidfuzz import fuzz


FUZZY_KEYWORD_THRESHOLD = 88
FUZZY_TAG_THRESHOLD = 84


DEFAULT_ROLE_TAG_KEYWORDS: dict[str, list[str]] = {
    "Software Engineering": [
        "software engineer",
        "software engineering",
        "swe",
        "software developer",
        "full stack",
        "frontend",
        "backend",
    ],
    "Backend": ["backend", "back end", "api", "server"],
    "Frontend": ["frontend", "front end", "react", "web"],
    "Full Stack": ["full stack", "fullstack"],
    "Machine Learning": [
        "machine learning",
        "ml engineer",
        "ai engineer",
        "artificial intelligence",
        "deep learning",
    ],
    "Data Science": ["data science", "data scientist", "analytics"],
    "Product": ["product manager", "product management", "apm"],
    "Design": ["designer", "product design", "ux", "ui design"],
    "Quant": ["quant", "quantitative", "trading"],
}


@dataclass(frozen=True)
class JobRoleFilterInput:
    title: str
    raw_text: str | None = None
    source_section: str | None = None
    description: str | None = None
    scan_role_tags: list[str] | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None


@dataclass(frozen=True)
class JobRoleFilterResult:
    included: bool
    job_tags: list[str]
    reason: str


def classify_job_role(values: JobRoleFilterInput) -> JobRoleFilterResult:
    scan_role_tags = _clean_list(values.scan_role_tags or [])
    include_keywords = _clean_list(values.include_keywords or [])
    exclude_keywords = _clean_list(values.exclude_keywords or [])
    searchable_text = _searchable_text(values)

    exclude_match = _first_keyword_match(exclude_keywords, searchable_text)
    if exclude_match is not None:
        return JobRoleFilterResult(
            included=False,
            job_tags=[],
            reason=f"Skipped because {exclude_match.location} matched exclude keyword '{exclude_match.keyword}'.",
        )

    matched_tags = _matched_tags(scan_role_tags, searchable_text)
    has_filters = bool(scan_role_tags or include_keywords or exclude_keywords)

    if include_keywords:
        include_match = _first_keyword_match(include_keywords, searchable_text)
        if include_match is None:
            return JobRoleFilterResult(
                included=False,
                job_tags=matched_tags,
                reason="Skipped because no include keywords matched.",
            )

        return JobRoleFilterResult(
            included=True,
            job_tags=matched_tags,
            reason=_included_reason(
                f"Included because {include_match.location} matched include keyword '{include_match.keyword}'.",
                matched_tags,
            ),
        )

    if scan_role_tags and not matched_tags:
        return JobRoleFilterResult(
            included=False,
            job_tags=[],
            reason="Skipped because no configured role tags matched.",
        )

    if has_filters:
        return JobRoleFilterResult(
            included=True,
            job_tags=matched_tags,
            reason=_included_reason("Included by configured role filters.", matched_tags),
        )

    inferred_tags = _matched_tags(list(DEFAULT_ROLE_TAG_KEYWORDS), searchable_text)
    return JobRoleFilterResult(
        included=True,
        job_tags=inferred_tags,
        reason=_included_reason("Included because no scan filters are configured.", inferred_tags),
    )


@dataclass(frozen=True)
class _KeywordMatch:
    keyword: str
    location: str


def _searchable_text(values: JobRoleFilterInput) -> dict[str, str]:
    return {
        "title": _normalize_text(values.title),
        "row": _normalize_text(values.raw_text or ""),
        "section": _normalize_text(values.source_section or ""),
        "description": _normalize_text(values.description or ""),
    }


def _first_keyword_match(
    keywords: list[str],
    searchable_text: dict[str, str],
) -> _KeywordMatch | None:
    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword == "":
            continue
        for location, text in searchable_text.items():
            if text == "":
                continue
            if _keyword_matches(normalized_keyword, text):
                return _KeywordMatch(keyword=keyword, location=location)

    return None


def _matched_tags(tags: list[str], searchable_text: dict[str, str]) -> list[str]:
    matched_tags: list[str] = []
    seen_tags: set[str] = set()
    for tag in tags:
        normalized_tag = tag.casefold()
        keywords = DEFAULT_ROLE_TAG_KEYWORDS.get(tag, [tag])
        if _first_keyword_match_for_tag(keywords, searchable_text) and normalized_tag not in seen_tags:
            matched_tags.append(tag)
            seen_tags.add(normalized_tag)

    return matched_tags


def _first_keyword_match_for_tag(
    keywords: list[str],
    searchable_text: dict[str, str],
) -> bool:
    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword == "":
            continue
        for text in searchable_text.values():
            if text and _keyword_matches(normalized_keyword, text, threshold=FUZZY_TAG_THRESHOLD):
                return True

    return False


def _keyword_matches(
    normalized_keyword: str,
    normalized_text: str,
    *,
    threshold: int = FUZZY_KEYWORD_THRESHOLD,
) -> bool:
    if re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", normalized_text):
        return True

    return fuzz.token_set_ratio(normalized_keyword, normalized_text) >= threshold


def _included_reason(base_reason: str, tags: list[str]) -> str:
    if not tags:
        return base_reason

    return f"{base_reason} Tagged as {', '.join(tags)}."


def _clean_list(values: list[str]) -> list[str]:
    cleaned_values: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        cleaned_value = str(value).strip()
        normalized_value = cleaned_value.casefold()
        if cleaned_value == "" or normalized_value in seen_values:
            continue
        cleaned_values.append(cleaned_value)
        seen_values.add(normalized_value)

    return cleaned_values


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", value.casefold()).strip()
