from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
import tempfile
import unittest
from uuid import uuid4

from app.services.resume_pdf_service import CompilerCommand, ResumePdfService
from app.services.resume_pdf_service import _prepare_latex_for_compiler


class ResumePdfServiceTests(unittest.TestCase):
    def test_missing_latex_compiler_returns_readable_error(self) -> None:
        repository = FakeGeneratedResumeRepository()
        service = ResumePdfService(
            repository,
            command_resolver=lambda name: None,
        )
        resume = _resume()

        result = service.compile_pdf(resume)

        self.assertFalse(result.success)
        self.assertIsNone(result.download_url)
        self.assertIn("No LaTeX compiler found", result.error_message or "")
        self.assertIsNone(repository.updated_values)

    def test_successful_compile_stores_pdf_and_updates_resume_path(self) -> None:
        repository = FakeGeneratedResumeRepository()
        resume = _resume()
        with tempfile.TemporaryDirectory() as temp_dir_name:
            storage_root = Path(temp_dir_name) / "storage" / "resumes"
            service = ResumePdfService(
                repository,
                storage_root=storage_root,
                command_resolver=lambda name: "/usr/local/bin/tectonic"
                if name == "tectonic"
                else None,
                command_runner=_successful_runner,
            )

            result = service.compile_pdf(resume)

            self.assertTrue(result.success)
            self.assertEqual(result.compiler, "tectonic")
            self.assertIsNotNone(result.download_url)
            self.assertIsNotNone(repository.updated_values)
            stored_pdf_path = Path(repository.updated_values["pdf_path"])
            self.assertTrue(stored_pdf_path.exists())

    def test_compile_failure_returns_logs_without_updating_resume(self) -> None:
        repository = FakeGeneratedResumeRepository()
        with tempfile.TemporaryDirectory() as temp_dir_name:
            service = ResumePdfService(
                repository,
                storage_root=Path(temp_dir_name) / "storage" / "resumes",
                command_resolver=lambda name: "/usr/local/bin/pdflatex"
                if name == "pdflatex"
                else None,
                command_runner=_failed_runner,
            )

            result = service.compile_pdf(_resume())

            self.assertFalse(result.success)
            self.assertEqual(result.compiler, "pdflatex")
            self.assertIn("Missing $ inserted", result.logs or "")
            self.assertIsNone(repository.updated_values)

    def test_tectonic_adds_pdftex_glyphtounicode_compatibility_shim(self) -> None:
        latex = "\\documentclass{article}\\input{glyphtounicode}\\pdfgentounicode=1\\begin{document}Resume\\end{document}"

        prepared_latex = _prepare_latex_for_compiler(
            latex,
            CompilerCommand(name="tectonic", executable="/usr/local/bin/tectonic"),
        )

        self.assertIn("\\newcommand{\\pdfglyphtounicode}[2]{}", prepared_latex)
        self.assertIn("\\newcount\\pdfgentounicode", prepared_latex)
        self.assertLess(
            prepared_latex.index("\\newcommand{\\pdfglyphtounicode}"),
            prepared_latex.index("\\input{glyphtounicode}"),
        )

    def test_pdflatex_does_not_add_tectonic_compatibility_shim(self) -> None:
        latex = "\\documentclass{article}\\input{glyphtounicode}\\begin{document}Resume\\end{document}"

        prepared_latex = _prepare_latex_for_compiler(
            latex,
            CompilerCommand(name="pdflatex", executable="/usr/local/bin/pdflatex"),
        )

        self.assertEqual(prepared_latex, latex)


class FakeGeneratedResumeRepository:
    def __init__(self) -> None:
        self.updated_values: dict[str, object] | None = None

    def update(self, generated_resume: SimpleNamespace, values: dict[str, object]) -> SimpleNamespace:
        self.updated_values = values
        for field, value in values.items():
            setattr(generated_resume, field, value)
        return generated_resume


def _resume() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        tailored_latex="\\documentclass{article}\\begin{document}Resume\\end{document}",
        pdf_path=None,
    )


def _successful_runner(command, cwd, capture_output, text, timeout):
    Path(cwd, "resume.pdf").write_bytes(b"%PDF-1.4\n")
    return CompletedProcess(command, 0, stdout="compiled", stderr="")


def _failed_runner(command, cwd, capture_output, text, timeout):
    Path(cwd, "resume.log").write_text("! Missing $ inserted.", encoding="utf-8")
    return CompletedProcess(command, 1, stdout="failed", stderr="")


if __name__ == "__main__":
    unittest.main()
