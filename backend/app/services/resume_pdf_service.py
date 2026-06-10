from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import UUID

from app.core.config import PROJECT_ROOT
from app.models.generated_resume import GeneratedResume
from app.repositories.generated_resume_repository import GeneratedResumeRepository


BACKEND_ROOT = PROJECT_ROOT / "backend"
PDF_STORAGE_ROOT = BACKEND_ROOT / "storage" / "resumes"
MAX_LOG_LENGTH = 12000


@dataclass(frozen=True)
class PdfCompileResult:
    success: bool
    resume_id: UUID
    pdf_path: str | None
    download_url: str | None
    compiler: str | None
    logs: str | None
    error_message: str | None


@dataclass(frozen=True)
class CompilerCommand:
    name: str
    executable: str


class ResumePdfService:
    def __init__(
        self,
        repository: GeneratedResumeRepository,
        *,
        storage_root: Path = PDF_STORAGE_ROOT,
        command_resolver=shutil.which,
        command_runner=subprocess.run,
    ) -> None:
        self.repository = repository
        self.storage_root = storage_root
        self.command_resolver = command_resolver
        self.command_runner = command_runner

    def compile_pdf(self, generated_resume: GeneratedResume) -> PdfCompileResult:
        compiler = self._find_compiler()
        if compiler is None:
            return PdfCompileResult(
                success=False,
                resume_id=generated_resume.id,
                pdf_path=generated_resume.pdf_path,
                download_url=None,
                compiler=None,
                logs=None,
                error_message=(
                    "No LaTeX compiler found. Install tectonic or pdflatex locally, "
                    "then retry PDF compilation."
                ),
            )

        with tempfile.TemporaryDirectory(prefix="applywise-resume-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            tex_path = temp_dir / "resume.tex"
            tex_path.write_text(
                _prepare_latex_for_compiler(
                    generated_resume.tailored_latex,
                    compiler,
                ),
                encoding="utf-8",
            )

            command = _build_compile_command(compiler, tex_path, temp_dir)
            try:
                process = self.command_runner(
                    command,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
            except subprocess.TimeoutExpired as error:
                return PdfCompileResult(
                    success=False,
                    resume_id=generated_resume.id,
                    pdf_path=generated_resume.pdf_path,
                    download_url=None,
                    compiler=compiler.name,
                    logs=_compile_logs(
                        _optional_process_text(error.stdout),
                        _optional_process_text(error.stderr),
                        temp_dir / "resume.log",
                    ),
                    error_message="LaTeX compilation timed out.",
                )
            except OSError as error:
                return PdfCompileResult(
                    success=False,
                    resume_id=generated_resume.id,
                    pdf_path=generated_resume.pdf_path,
                    download_url=None,
                    compiler=compiler.name,
                    logs=None,
                    error_message=f"Could not start LaTeX compiler: {error}",
                )

            logs = _compile_logs(process.stdout, process.stderr, temp_dir / "resume.log")
            pdf_path = temp_dir / "resume.pdf"
            if process.returncode != 0 or not pdf_path.exists():
                return PdfCompileResult(
                    success=False,
                    resume_id=generated_resume.id,
                    pdf_path=generated_resume.pdf_path,
                    download_url=None,
                    compiler=compiler.name,
                    logs=logs,
                    error_message="LaTeX compilation failed.",
                )

            stored_pdf_path = self.storage_root / str(generated_resume.user_id) / f"{generated_resume.id}.pdf"
            stored_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, stored_pdf_path)
            try:
                stored_pdf_value = str(stored_pdf_path.relative_to(BACKEND_ROOT))
            except ValueError:
                stored_pdf_value = str(stored_pdf_path)

        updated_resume = self.repository.update(
            generated_resume,
            {"pdf_path": stored_pdf_value},
        )
        return PdfCompileResult(
            success=True,
            resume_id=updated_resume.id,
            pdf_path=updated_resume.pdf_path,
            download_url=f"/api/generated-resumes/{updated_resume.id}/download",
            compiler=compiler.name,
            logs=logs,
            error_message=None,
        )

    def _find_compiler(self) -> CompilerCommand | None:
        tectonic_path = self.command_resolver("tectonic")
        if tectonic_path is not None:
            return CompilerCommand(name="tectonic", executable=tectonic_path)

        pdflatex_path = self.command_resolver("pdflatex")
        if pdflatex_path is not None:
            return CompilerCommand(name="pdflatex", executable=pdflatex_path)

        return None


def resolve_generated_resume_pdf_path(generated_resume: GeneratedResume) -> Path | None:
    if generated_resume.pdf_path is None or generated_resume.pdf_path.strip() == "":
        return None

    path = Path(generated_resume.pdf_path)
    if path.is_absolute():
        resolved_path = path.resolve()
    else:
        resolved_path = (BACKEND_ROOT / path).resolve()

    storage_root = PDF_STORAGE_ROOT.resolve()
    if not resolved_path.is_relative_to(storage_root):
        return None

    return resolved_path


def _build_compile_command(
    compiler: CompilerCommand,
    tex_path: Path,
    output_dir: Path,
) -> list[str]:
    if compiler.name == "tectonic":
        return [
            compiler.executable,
            "--keep-logs",
            "--outdir",
            str(output_dir),
            str(tex_path),
        ]

    return [
        compiler.executable,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(output_dir),
        str(tex_path),
    ]


def _prepare_latex_for_compiler(latex_content: str, compiler: CompilerCommand) -> str:
    if compiler.name != "tectonic":
        return latex_content
    if "\\pdfglyphtounicode" not in latex_content and "\\pdfgentounicode" not in latex_content:
        return latex_content

    shim = (
        "\\ifdefined\\pdfglyphtounicode\\else\n"
        "  \\newcommand{\\pdfglyphtounicode}[2]{}\n"
        "\\fi\n"
        "\\ifdefined\\pdfgentounicode\\else\n"
        "  \\newcount\\pdfgentounicode\n"
        "\\fi\n"
    )
    documentclass_match = re.search(
        r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}",
        latex_content,
    )
    if documentclass_match is not None:
        insertion_index = documentclass_match.end()
        return (
            f"{latex_content[:insertion_index]}\n"
            f"{shim}\n"
            f"{latex_content[insertion_index:]}"
        )

    return f"{shim}\n{latex_content}"


def _compile_logs(stdout: str, stderr: str, log_path: Path) -> str:
    parts = []
    if stdout.strip():
        parts.append(stdout.strip())
    if stderr.strip():
        parts.append(stderr.strip())
    if log_path.exists():
        log_content = log_path.read_text(encoding="utf-8", errors="replace").strip()
        if log_content:
            parts.append(log_content)

    logs = "\n\n".join(parts).strip()
    if len(logs) > MAX_LOG_LENGTH:
        return logs[-MAX_LOG_LENGTH:]

    return logs


def _optional_process_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value
