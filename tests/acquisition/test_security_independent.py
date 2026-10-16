"""Independent security-boundary checks for the optional acquisition runner."""

import unittest

from backend.acquisition import _public_ip_for_host, _valid_source


class IndependentNetworkBoundaryTests(unittest.TestCase):
    def test_rejects_userinfo_and_nonstandard_https_ports(self):
        self.assertFalse(_valid_source("https://user:secret@aclanthology.org/paper.pdf"))
        self.assertFalse(_valid_source("https://aclanthology.org:8443/paper.pdf"))

    def test_dns_rejects_loopback_link_local_and_private_ipv6(self):
        addresses = ["127.0.0.1", "169.254.1.2", "10.0.0.8", "::1", "fe80::1", "fc00::1"]
        for address in addresses:
            with self.subTest(address=address):
                resolver = lambda *_args, value=address, **_kwargs: [
                    (None, None, None, None, (value, 443))
                ]
                with self.assertRaisesRegex(ValueError, "host_has_no_public_address"):
                    _public_ip_for_host("aclanthology.org", resolver)

    def test_mixed_dns_answers_select_only_a_public_address(self):
        resolver = lambda *_args, **_kwargs: [
            (None, None, None, None, ("127.0.0.1", 443)),
            (None, None, None, None, ("8.8.8.8", 443)),
        ]
        self.assertEqual(_public_ip_for_host("aclanthology.org", resolver), "8.8.8.8")

    def test_nature_idp_is_rejected_without_nature_flow_context(self):
        resolver = lambda *_args, **_kwargs: [
            (None, None, None, None, ("8.8.8.8", 443)),
        ]
        with self.assertRaisesRegex(ValueError, "access_gate_redirect"):
            _public_ip_for_host("idp.nature.com", resolver)


if __name__ == "__main__":
    unittest.main()
