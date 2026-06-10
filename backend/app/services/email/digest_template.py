from html import escape

from app.repositories.digest_repository import JobDigestItem


def render_digest_html_email(
    *,
    recipient_name: str | None,
    items: list[JobDigestItem],
    download_url_by_resume_id: dict[str, str],
) -> str:
    display_name = escape(recipient_name or "there")
    rows = "\n".join(
        _render_digest_item(
            item,
            download_url_by_resume_id=download_url_by_resume_id,
        )
        for item in items
    )
    if not rows:
        rows = """
        <tr>
          <td style="padding: 20px; color: #475569;">
            No matched jobs are ready yet.
          </td>
        </tr>
        """

    return f"""<!doctype html>
<html>
  <body style="margin:0; padding:0; background:#f8fafc; font-family:Arial, sans-serif; color:#0f172a;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f8fafc; padding:24px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:760px; background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; overflow:hidden;">
            <tr>
              <td style="padding:24px 28px; background:#111827; color:#ffffff;">
                <div style="font-size:13px; letter-spacing:0.08em; text-transform:uppercase; color:#cbd5e1;">ApplyWise AI</div>
                <h1 style="margin:8px 0 0; font-size:24px; line-height:1.25;">Matched Jobs Digest</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 28px 8px;">
                <p style="margin:0 0 12px; color:#334155; font-size:15px; line-height:1.6;">Hi {display_name},</p>
                <p style="margin:0; color:#334155; font-size:15px; line-height:1.6;">Here are your latest matched jobs and generated resume links.</p>
              </td>
            </tr>
            {rows}
            <tr>
              <td style="padding:18px 28px 24px; color:#64748b; font-size:12px; line-height:1.5; border-top:1px solid #e2e8f0;">
                This digest only uses jobs, matches, and resumes stored in ApplyWise AI.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def render_digest_text_email(
    *,
    recipient_name: str | None,
    items: list[JobDigestItem],
    download_url_by_resume_id: dict[str, str],
) -> str:
    lines = [
        f"Hi {recipient_name or 'there'},",
        "",
        "Here are your latest matched jobs and generated resume links.",
        "",
    ]
    if not items:
        lines.append("No matched jobs are ready yet.")
        return "\n".join(lines)

    for index, item in enumerate(items, start=1):
        resume_link = _resume_link(item, download_url_by_resume_id)
        lines.extend(
            [
                f"{index}. {item.job.company} - {item.job.title}",
                f"Location: {item.job.location or 'Not specified'}",
                f"Job URL: {item.job.job_url or 'Not provided'}",
                f"Match score: {item.match.score}",
                f"Match reason: {item.match.match_reason}",
                f"Resume link: {resume_link or 'No generated resume link yet'}",
            ]
        )
        safety_warnings = _safety_warnings(item)
        if safety_warnings:
            lines.append(f"Safety warnings: {', '.join(safety_warnings)}")
        lines.append("")

    return "\n".join(lines).strip()


def _render_digest_item(
    item: JobDigestItem,
    *,
    download_url_by_resume_id: dict[str, str],
) -> str:
    job = item.job
    match = item.match
    resume_link = _resume_link(item, download_url_by_resume_id)
    resume_link_html = (
        f'<a href="{escape(resume_link)}" style="color:#2563eb;">Open generated resume</a>'
        if resume_link
        else '<span style="color:#64748b;">No generated resume link yet</span>'
    )
    job_url_html = (
        f'<a href="{escape(job.job_url)}" style="color:#2563eb;">Open job posting</a>'
        if job.job_url
        else '<span style="color:#64748b;">No job URL provided</span>'
    )
    safety_warning_html = _render_safety_warnings(_safety_warnings(item))

    return f"""
            <tr>
              <td style="padding:18px 28px; border-top:1px solid #e2e8f0;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td>
                      <h2 style="margin:0 0 4px; font-size:18px; line-height:1.35; color:#0f172a;">{escape(job.title)}</h2>
                      <div style="font-size:14px; color:#475569;">{escape(job.company)} · {escape(job.location or "Location not specified")}</div>
                    </td>
                    <td align="right" style="width:96px;">
                      <div style="display:inline-block; padding:8px 10px; background:#ecfdf5; color:#065f46; border-radius:8px; font-weight:700; font-size:16px;">{match.score}</div>
                    </td>
                  </tr>
                </table>
                <p style="margin:14px 0 10px; color:#334155; font-size:14px; line-height:1.6;">{escape(match.match_reason)}</p>
                <div style="font-size:14px; line-height:1.8;">
                  {job_url_html}<br>
                  {resume_link_html}
                </div>
                {safety_warning_html}
              </td>
            </tr>
    """


def _render_safety_warnings(safety_warnings: list[str]) -> str:
    if not safety_warnings:
        return ""

    items = "".join(
        f"<li>{escape(warning)}</li>"
        for warning in safety_warnings
    )
    return f"""
                <div style="margin-top:14px; padding:12px 14px; background:#fff7ed; border:1px solid #fed7aa; border-radius:8px;">
                  <div style="font-weight:700; color:#9a3412; font-size:13px; margin-bottom:6px;">Safety warnings</div>
                  <ul style="margin:0; padding-left:18px; color:#9a3412; font-size:13px; line-height:1.5;">{items}</ul>
                </div>
    """


def _resume_link(
    item: JobDigestItem,
    download_url_by_resume_id: dict[str, str],
) -> str | None:
    generated_resume = item.generated_resume
    if generated_resume is None:
        return None
    if generated_resume.drive_url:
        return generated_resume.drive_url
    if generated_resume.pdf_path:
        return download_url_by_resume_id.get(str(generated_resume.id))

    return None


def _safety_warnings(item: JobDigestItem) -> list[str]:
    if item.generated_resume is None:
        return []

    return [
        str(warning).strip()
        for warning in item.generated_resume.safety_warnings
        if str(warning).strip()
    ]
