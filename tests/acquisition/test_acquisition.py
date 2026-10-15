import tempfile
import unittest
import hashlib
from unittest.mock import patch
from pathlib import Path
import asyncio

import fitz

from backend.acquisition import _curl_download, _identity_check, _public_ip_for_host, _valid_source, _verify_ready_record, jmlr_landing_url, select_official_pdf_link, source_url_candidates


class AcquisitionIdentityTests(unittest.TestCase):
    def pdf(self, path: Path, first_page: str, metadata_title: str = "") -> Path:
        document = fitz.open()
        page = document.new_page()
        page.insert_textbox(fitz.Rect(50, 60, 550, 750), first_page, fontsize=11)
        document.set_metadata({"title": metadata_title})
        document.save(path)
        document.close()
        return path

    def test_header_title_matches_without_pdf_metadata(self):
        expected = "Model Transferability with Responsive Decision Subjects"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "ok.pdf", expected + "\nJane Doe and John Smith\nAbstract\n" + "Research text. " * 60)
            basis = _identity_check(path, {"title": expected, "doi": None, "arxiv_id": None})
        self.assertEqual(basis["kind"], "title")
        self.assertIn(expected, basis["evidence_excerpt"])

    def test_matching_catalog_venue_suffix_is_removed_before_pdf_title_match(self):
        expected = "A spatiotemporal defect-integrated deepfake video detection model"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "nature.pdf", expected + "\nJane Doe\nAbstract\n" + "Research text. " * 50)
            basis = _identity_check(path, {"title": expected + " | Scientific Reports", "venue": "Scientific Reports", "doi": None, "arxiv_id": None})
        self.assertEqual(basis["kind"], "title")
        self.assertEqual(basis["matched_title"], expected)
        self.assertEqual(basis["original_title"], expected + " | Scientific Reports")

    def test_wrong_paper_does_not_match_title_mentioned_later(self):
        expected = "Model Transferability with Responsive Decision Subjects"
        with tempfile.TemporaryDirectory() as folder:
            page1 = "An unrelated analysis of optimization.\n\nAbstract\n" + "Method text. " * 50
            page2 = "References\n" + expected + ". Journal reference, 2024.\n"
            path = Path(folder) / "wrong.pdf"
            doc = fitz.open()
            doc.new_page().insert_text((50, 60), page1)
            doc.new_page().insert_text((50, 60), page2)
            doc.save(path)
            doc.close()
            with self.assertRaisesRegex(ValueError, "identity_not_verified"):
                _identity_check(path, {"title": expected, "doi": None, "arxiv_id": None})

    def test_html_response_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "html.pdf"
            path.write_bytes(b"<!doctype html><title>sign in</title>")
            with self.assertRaisesRegex(ValueError, "html_or_captcha_response"):
                _identity_check(path, {"title": "A real paper title", "doi": None, "arxiv_id": None})

    def test_conflicting_primary_doi_cannot_fall_back_to_matching_title(self):
        expected = "Model Transferability with Responsive Decision Subjects"
        with tempfile.TemporaryDirectory() as folder:
            text = expected + "\nDOI: 10.1234/wrong.paper\nAbstract\n" + "Research text. " * 50
            path = self.pdf(Path(folder) / "wrong-doi.pdf", text)
            with self.assertRaisesRegex(ValueError, "identity_doi_mismatch"):
                _identity_check(path, {"title": expected, "doi": "10.1234/right.paper", "arxiv_id": None})

    def test_arxiv_version_corroborates_first_page_title_identity(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            text = expected + "\narXiv: 2401.01234v3\nAbstract\n" + "Research text. " * 50
            path = self.pdf(Path(folder) / "arxiv.pdf", text)
            basis = _identity_check(path, {"title": expected, "doi": None, "arxiv_id": "2401.01234v1"})
        self.assertEqual(basis["kind"], "title")
        self.assertEqual(basis["corroborating_arxiv"], "2401.01234v3")

    def test_acl_anthology_suffix_is_removed_before_header_match(self):
        expected = "A Helpful Paper about Long Context Reasoning Systems"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "acl.pdf", expected + "\nAlice Doe\nAbstract\n" + "Text. " * 40)
            basis = _identity_check(path, {"title": expected + " - ACL Anthology", "doi": None, "arxiv_id": None})
        self.assertEqual(basis["kind"], "title")
        self.assertEqual(basis["matched_title"], expected)

    def test_expected_doi_mentioned_only_in_first_page_references_does_not_match(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "doi-reference.pdf", "An unrelated paper on graph mining\nAbstract\nBody\nReferences\n10.1234/expected.doi")
            with self.assertRaisesRegex(ValueError, "identity_not_verified"):
                _identity_check(path, {"title": expected, "doi": "10.1234/expected.doi", "arxiv_id": None})

    def test_expected_arxiv_mentioned_only_in_abstract_does_not_match(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "arxiv-body.pdf", "An unrelated paper on graph mining\nAbstract\nWe compare with arXiv:2401.01234v3. " + "body " * 60)
            with self.assertRaisesRegex(ValueError, "identity_not_verified"):
                _identity_check(path, {"title": expected, "doi": None, "arxiv_id": "2401.01234v1"})

    def test_expected_title_only_in_first_page_references_does_not_match(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "title-reference.pdf", "An unrelated paper on graph mining\nAbstract\nBody\nReferences\n" + expected + ". 2024.")
            with self.assertRaisesRegex(ValueError, "identity_not_verified"):
                _identity_check(path, {"title": expected, "doi": None, "arxiv_id": None})

    def test_metadata_title_cannot_qualify_wrong_first_page_body(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "metadata-only.pdf", "An unrelated paper on graph mining\nAbstract\n" + "body " * 80, metadata_title=expected)
            with self.assertRaisesRegex(ValueError, "identity_not_verified"):
                _identity_check(path, {"title": expected, "doi": None, "arxiv_id": None})

    def test_obsolete_sha_valid_ready_marker_is_rejected_if_current_identity_fails(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "old-ready.pdf", "An unrelated paper on graph mining\nAbstract\n" + "body " * 80, metadata_title=expected)
            marker = {"pdf_path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "page_count": 1}
            self.assertIsNone(_verify_ready_record({"title": expected, "doi": None, "arxiv_id": None}, marker))

    def test_current_identity_revalidation_accepts_valid_ready_marker(self):
        expected = "A Useful Research Paper on Robust Learning"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "valid-ready.pdf", expected + "\nAlice Doe\nAbstract\n" + "Body " * 80)
            marker = {"pdf_path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "page_count": 1}
            self.assertEqual(_verify_ready_record({"title": expected, "doi": None, "arxiv_id": None}, marker)["kind"], "title")

    def test_generic_jmlr_masthead_cannot_qualify_as_paper_title(self):
        generic = "Journal of Machine Learning Research 22 (2021) 1-54"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "masthead.pdf", generic + "\nSubmitted 1/21; Revised 7/21; Published 10/21\nGraph Matching with Partially-Correct Seeds\n" + "Paper content. " * 40, generic)
            with self.assertRaisesRegex(ValueError, "identity_catalog_title_is_generic"):
                _identity_check(path, {"title": generic, "doi": None, "arxiv_id": None})

    def test_jmlr_masthead_prefix_with_article_title_is_not_identity(self):
        generic_prefix = "Journal of Machine Learning Research 22 (2021) 1-49Submitted 6/20; Revised 3/21; Published 4/21"
        actual_title = "Langevin Dynamics for Adaptive Inverse Reinforcement Learning of Stochastic Gradient Algorithms"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "masthead-plus-title.pdf", generic_prefix + "\n" + actual_title + "\nAbstract\n" + "Paper text. " * 80)
            with self.assertRaisesRegex(ValueError, "identity_catalog_title_is_generic"):
                _identity_check(path, {"title": generic_prefix, "doi": None, "arxiv_id": None})

    def test_jmlr_resolved_article_title_matches_after_issue_banner(self):
        expected = "Graph Matching with Partially-Correct Seeds"
        issue_header = "Journal of Machine Learning Research 22 (2021) 1-54\nSubmitted 1/21; Revised 7/21; Published 10/21"
        with tempfile.TemporaryDirectory() as folder:
            path = self.pdf(Path(folder) / "jmlr.pdf", issue_header + "\n" + expected + "\nJane Doe\nAbstract\n" + "Text. " * 40)
            basis = _identity_check(path, {"title": expected, "doi": None, "arxiv_id": None})
        self.assertEqual(basis["kind"], "title")
        self.assertIn(expected, basis["evidence_excerpt"])


class ResolverTests(unittest.TestCase):
    def test_deterministic_source_specific_pdf_urls(self):
        cases = [
            ({"source_url": "https://aclanthology.org/2025.acl-long.42/"}, "https://aclanthology.org/2025.acl-long.42.pdf"),
            ({"source_url": "https://proceedings.mlr.press/v202/chen23y.html"}, "https://proceedings.mlr.press/v202/chen23y/chen23y.pdf"),
            ({"source_url": "https://proceedings.mlr.press/v119/triastcyn20a/triastcyn20a.pdf"}, "https://proceedings.mlr.press/v119/triastcyn20a/triastcyn20a.pdf"),
            ({"source_url": "https://proceedings.neurips.cc/paper/2021/hash/447b0408b80078338810051bb38b177f-Abstract.html"}, "https://proceedings.neurips.cc/paper/2021/hash/447b0408b80078338810051bb38b177f-Paper.pdf"),
            ({"source_url": "https://jmlr.org/papers/v27/23-0944.html"}, "https://jmlr.org/papers/volume27/23-0944/23-0944.pdf"),
            ({"source_url": "https://jmlr.org/papers/v21/18-800.html"}, "https://jmlr.org/papers/volume21/18-800/18-800.pdf"),
            ({"source_url": "https://www.nature.com/articles/s41586-024-00001-2"}, "https://www.nature.com/articles/s41586-024-00001-2.pdf"),
        ]
        for paper, expected in cases:
            with self.subTest(expected=expected):
                urls = [url for url, _ in source_url_candidates(paper)]
                self.assertEqual(urls, [expected])

    def test_jmlr_pdf_url_maps_to_official_landing_page(self):
        self.assertEqual(jmlr_landing_url("https://jmlr.org/papers/volume22/21-0020/21-0020.pdf"),
                         "https://www.jmlr.org/papers/v22/21-0020.html")

    def test_official_pmlr_landing_selects_exact_pdf_anchor(self):
        source = "https://proceedings.mlr.press/v306/dauncey26a.html"
        link = select_official_pdf_link(source, source, [
            "/mlresearch/v306/main/assets/dauncey26a/dauncey26a.pdf",
            "/mlresearch/v306/main/assets/dauncey26a/dauncey26a-supplement.pdf",
        ])
        self.assertEqual(link, "https://proceedings.mlr.press/mlresearch/v306/main/assets/dauncey26a/dauncey26a.pdf")

    def test_official_neurips_landing_selects_conference_pdf(self):
        source = "https://proceedings.neurips.cc/paper_files/paper/2024/hash/1c0d54ebd0a6e58c4eca7d591e374b9d-Abstract-Conference.html"
        link = select_official_pdf_link(source, source, [
            "/paper_files/paper/2024/file/1c0d54ebd0a6e58c4eca7d591e374b9d-Paper-Conference.pdf",
            "/paper_files/paper/2024/file/1c0d54ebd0a6e58c4eca7d591e374b9d-Supplemental-Conference.pdf",
        ])
        self.assertEqual(link, "https://proceedings.neurips.cc/paper_files/paper/2024/file/1c0d54ebd0a6e58c4eca7d591e374b9d-Paper-Conference.pdf")

    def test_official_resolver_refuses_unallowlisted_pdf_link(self):
        source = "https://proceedings.mlr.press/v306/dauncey26a.html"
        self.assertIsNone(select_official_pdf_link(source, source, ["https://evil.example/dauncey26a.pdf"]))

    def test_rejects_non_https_and_nonstandard_port(self):
        self.assertFalse(_valid_source("http://aclanthology.org/2025.acl-long.42.pdf"))
        self.assertFalse(_valid_source("https://aclanthology.org:8443/2025.acl-long.42.pdf"))

    def test_rejects_non_allowlisted_and_private_dns_targets(self):
        self.assertRaisesRegex(ValueError, "host_not_allowlisted", _public_ip_for_host, "localhost", lambda *_a, **_k: [])
        private_resolver = lambda *_a, **_k: [(None, None, None, None, ("127.0.0.1", 443))]
        self.assertRaisesRegex(ValueError, "host_has_no_public_address", _public_ip_for_host, "aclanthology.org", private_resolver)

    def test_nature_identity_provider_is_classified_as_access_gate(self):
        self.assertRaisesRegex(ValueError, "access_gate_redirect", _public_ip_for_host, "idp.nature.com")

    def test_accepts_allowlisted_public_dns_target(self):
        public_resolver = lambda *_a, **_k: [(None, None, None, None, ("192.0.2.10", 443)), (None, None, None, None, ("8.8.8.8", 443))]
        self.assertEqual(_public_ip_for_host("aclanthology.org", public_resolver), "8.8.8.8")


class CurlDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def _download_with_responses(self, responses, url="https://aclanthology.org/start.pdf"):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "paper.part"
            calls = []

            class Process:
                def __init__(self, command, response):
                    self.command = command
                    self.response = response
                    self.returncode = response[0]

                async def communicate(self):
                    status, content_type, location, returncode, *extras = self.response
                    header = self.command[self.command.index("--dump-header") + 1]
                    output = self.command[self.command.index("--output") + 1]
                    text = f"HTTP/2 {status}\r\n"
                    if location:
                        text += f"location: {location}\r\n"
                    if extras and extras[0]:
                        text += f"Set-Cookie: {extras[0]}\r\n"
                    Path(header).write_text(text + "\r\n")
                    if extras and extras[0] and "--cookie-jar" in self.command:
                        Path(self.command[self.command.index("--cookie-jar") + 1]).write_text(extras[0])
                    if "--cookie" in self.command:
                        calls.append(("cookie", Path(self.command[self.command.index("--cookie") + 1]).read_text() if Path(self.command[self.command.index("--cookie") + 1]).exists() else ""))
                    if status == 200:
                        Path(output).write_bytes(b"%PDF-1.7 test")
                    self.returncode = returncode
                    stdout = f"{status}\n{content_type}\n{self.command[-1]}".encode()
                    stderr = b"test http error" if returncode else b""
                    return stdout, stderr

                def kill(self):
                    self.returncode = -9

            async def fake_create(*command, **_kwargs):
                calls.append(command[-1])
                return Process(command, responses.pop(0))

            with patch("backend.acquisition._public_ip_for_host", return_value="8.8.8.8"), \
                 patch("backend.acquisition.asyncio.create_subprocess_exec", side_effect=fake_create):
                result = await _curl_download(url, path, {})
            return result, path.stat().st_size if path.exists() else 0, calls

    async def test_http_200_download(self):
        result, size, calls = await self._download_with_responses([(200, "application/pdf", None, 0)])
        self.assertEqual(result[:2], (200, "application/pdf"))
        self.assertEqual(size, len(b"%PDF-1.7 test"))
        self.assertEqual(len(calls), 1)

    async def test_https_redirect_is_followed_with_independent_request(self):
        result, size, calls = await self._download_with_responses([
            (302, "text/html", "https://jmlr.org/final.pdf", 0),
            (200, "application/pdf", None, 0),
        ])
        self.assertEqual(result[2], "https://jmlr.org/final.pdf")
        self.assertEqual(size, len(b"%PDF-1.7 test"))
        self.assertEqual(len(calls), 2)

    async def test_http_404_is_returned_once_as_error(self):
        with self.assertRaisesRegex(RuntimeError, "http_404"):
            await self._download_with_responses([(404, "text/html", None, 22)])

    async def test_https_to_http_downgrade_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "redirect_to_non_https_url"):
            await self._download_with_responses([(302, "text/html", "http://aclanthology.org/final.pdf", 0)])

    async def test_nature_anonymous_cookie_bootstrap_reuses_cookie_and_returns_to_same_pdf(self):
        source = "https://www.nature.com/articles/s41467-024-54712-1.pdf"
        result, size, calls = await self._download_with_responses([
            (303, "text/html", "https://idp.nature.com/authorize?response_type=code", 0, "nature_session=abc; HttpOnly; Secure"),
            (302, "text/html", "https://idp.nature.com/transit?state=xyz", 0),
            (302, "text/html", source, 0),
            (200, "application/pdf", None, 0),
        ], url=source)
        self.assertEqual(result[:2], (200, "application/pdf"))
        self.assertEqual(result[2], source)
        self.assertEqual(size, len(b"%PDF-1.7 test"))
        cookie_calls = [item[1] for item in calls if isinstance(item, tuple) and item[0] == "cookie"]
        self.assertEqual(len(cookie_calls), 4)
        self.assertTrue(all("nature_session=abc" in item for item in cookie_calls[1:]))

    async def test_nature_bootstrap_rejects_external_redirect(self):
        with self.assertRaisesRegex(ValueError, "nature_redirect_out_of_scope"):
            await self._download_with_responses([
                (302, "text/html", "https://evil.example/collect", 0),
            ], url="https://www.nature.com/articles/s41467-024-54712-1.pdf")

    async def test_nature_bootstrap_rejects_http_downgrade(self):
        with self.assertRaisesRegex(ValueError, "redirect_to_non_https_url"):
            await self._download_with_responses([
                (302, "text/html", "http://idp.nature.com/authorize", 0),
            ], url="https://www.nature.com/articles/s41467-024-54712-1.pdf")


if __name__ == "__main__":
    unittest.main()
