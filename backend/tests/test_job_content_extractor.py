import unittest
from datetime import UTC, datetime

from app.services.jobs.job_content_extractor import extract_job_content_from_html


class JobContentExtractorTests(unittest.TestCase):
    def test_extracts_json_ld_job_posting_description(self) -> None:
        html = """
        <html>
          <head>
            <title>Senior Backend Engineer | Acme</title>
            <meta property="og:site_name" content="Acme Careers">
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Senior Backend Engineer",
                "hiringOrganization": {"name": "Acme Systems"},
                "description": "<h2>Responsibilities</h2><p>Build reliable API services for internal teams.</p><ul><li>Design FastAPI services</li><li>Improve PostgreSQL workflows</li></ul><h2>Requirements</h2><p>Production Python experience and clear communication.</p>"
              }
            </script>
          </head>
          <body>
            <nav>Careers navigation</nav>
            <main>Short marketing content.</main>
          </body>
        </html>
        """

        result = extract_job_content_from_html(
            html,
            page_url="https://boards.greenhouse.io/acme/jobs/123",
        )

        self.assertTrue(result.extraction_success)
        self.assertEqual(result.extraction_method, "json_ld_job_posting")
        self.assertEqual(result.company_guess, "Acme Systems")
        self.assertEqual(result.title_guess, "Senior Backend Engineer")
        self.assertIn("Responsibilities", result.cleaned_text)
        self.assertIn("- Design FastAPI services", result.cleaned_text)
        self.assertNotIn("Careers navigation", result.cleaned_text)

    def test_extracts_json_ld_location_guess(self) -> None:
        html = """
        <html>
          <head>
            <title>Backend Engineer</title>
            <script type="application/ld+json">
              {
                "@type": "JobPosting",
                "title": "Backend Engineer",
                "hiringOrganization": {"name": "Acme"},
                "jobLocation": {
                  "address": {
                    "addressLocality": "New York",
                    "addressRegion": "NY",
                    "addressCountry": "US"
                  }
                },
                "description": "<h2>Responsibilities</h2><p>Build backend services.</p><h2>Requirements</h2><p>Python and SQL experience.</p>"
              }
            </script>
          </head>
          <body></body>
        </html>
        """

        result = extract_job_content_from_html(html, page_url="https://example.com/jobs/1")

        self.assertTrue(result.extraction_success)
        self.assertEqual(result.location_guess, "New York, NY, US")

    def test_extracts_json_ld_posted_date(self) -> None:
        html = """
        <html>
          <head>
            <script type="application/ld+json">
              {
                "@type": "JobPosting",
                "title": "Backend Engineer",
                "datePosted": "2026-05-21",
                "description": "<h2>Responsibilities</h2><p>Build backend services.</p><h2>Requirements</h2><p>Python and SQL experience.</p>"
              }
            </script>
          </head>
          <body></body>
        </html>
        """

        result = extract_job_content_from_html(html, page_url="https://example.com/jobs/1")

        self.assertTrue(result.extraction_success)
        self.assertEqual(result.posted_at, datetime(2026, 5, 21, tzinfo=UTC))

    def test_extracts_lever_posting_content(self) -> None:
        html = """
        <html>
          <head><title>Backend Engineer - Acme</title></head>
          <body>
            <header>Global links</header>
            <div class="posting-page">
              <div class="posting">
                <h1>Backend Engineer</h1>
                <section class="section-wrapper">
                  <h2>About the role</h2>
                  <p>You will build APIs that power customer-facing workflows.</p>
                  <h2>What you will do</h2>
                  <ul>
                    <li>Own Python services from design to rollout</li>
                    <li>Partner with product and data teams</li>
                    <li>Keep systems observable and reliable</li>
                  </ul>
                  <h2>Qualifications</h2>
                  <p>Experience with FastAPI, SQL databases, and pragmatic engineering tradeoffs.</p>
                </section>
              </div>
            </div>
            <footer>Footer links</footer>
          </body>
        </html>
        """

        result = extract_job_content_from_html(
            html,
            page_url="https://jobs.lever.co/acme/backend-engineer",
        )

        self.assertTrue(result.extraction_success)
        self.assertTrue(result.extraction_method.startswith("lever_selectors"))
        self.assertIn("Backend Engineer", result.cleaned_text)
        self.assertIn("- Own Python services from design to rollout", result.cleaned_text)
        self.assertNotIn("Global links", result.cleaned_text)
        self.assertNotIn("Footer links", result.cleaned_text)

    def test_generic_extraction_removes_non_content_elements(self) -> None:
        html = """
        <html>
          <head>
            <title>Data Engineer</title>
            <style>.hidden { display: none; }</style>
          </head>
          <body>
            <nav>Navigation</nav>
            <main>
              <h1>Data Engineer</h1>
              <p>Join the platform team building reliable batch and streaming pipelines.</p>
              <h2>Responsibilities</h2>
              <ul>
                <li>Develop Python data services</li>
                <li>Maintain PostgreSQL reporting models</li>
              </ul>
              <h2>Requirements</h2>
              <p>Strong SQL, Python, and production debugging experience.</p>
            </main>
            <script>window.analytics = true;</script>
            <footer>Footer</footer>
          </body>
        </html>
        """

        result = extract_job_content_from_html(
            html,
            page_url="https://example.com/jobs/data-engineer",
        )

        self.assertTrue(result.extraction_success)
        self.assertIn("Data Engineer", result.cleaned_text)
        self.assertEqual(result.title_guess, "Data Engineer")
        self.assertIn("- Develop Python data services", result.cleaned_text)
        self.assertNotIn("Navigation", result.cleaned_text)
        self.assertNotIn("window.analytics", result.cleaned_text)
        self.assertNotIn("Footer", result.cleaned_text)

    def test_returns_failed_result_with_fallback_text(self) -> None:
        html = """
        <html>
          <head><title>Blocked</title></head>
          <body>
            <nav>Navigation</nav>
            <main><p>Apply</p></main>
          </body>
        </html>
        """

        result = extract_job_content_from_html(html, page_url="https://example.com/jobs/blocked")

        self.assertFalse(result.extraction_success)
        self.assertEqual(result.cleaned_text, "Apply")
        self.assertEqual(result.page_title, "Blocked")
        self.assertEqual(
            result.error_message,
            "Could not extract a meaningful job description.",
        )


if __name__ == "__main__":
    unittest.main()
