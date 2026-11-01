import argparse
import unittest

from bank_salary.cli import _sources, http_client
from bank_salary.sources import BofaSource, CitiSource


class CliTests(unittest.TestCase):
    def test_bofa_and_citi_use_their_public_career_sources(self):
        args = argparse.Namespace(state_code="NY")
        self.assertEqual([type(s) for s in _sources(None, "BOFA", args)], [BofaSource])
        self.assertEqual([type(s) for s in _sources(None, "CITI", args)], [CitiSource])

    def test_citi_pages_are_requested_at_least_a_second_apart(self):
        self.assertEqual(
            http_client(argparse.Namespace(delay=0.35)).host_delays, {"jobs.citi.com": 1.0}
        )
        self.assertEqual(
            http_client(argparse.Namespace(delay=2.0)).host_delays, {"jobs.citi.com": 2.0}
        )


if __name__ == "__main__":
    unittest.main()
