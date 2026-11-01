import http.client
import json
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from bank_salary.sources import (
    BofaSource,
    CitiSource,
    HttpClient,
    OracleSource,
    WorkdaySource,
    discover_oracle_sites,
    scan_pages,
)


class PagingTests(unittest.TestCase):
    def test_paginates_by_returned_page_size(self):
        def page(offset):
            return 3, [{"Id": str(i)} for i in range(offset, min(offset + 2, 3))]

        result = scan_pages(page, lambda x: x["Id"])
        self.assertTrue(result.complete)
        self.assertEqual(set(result.items), {"0", "1", "2"})

    def test_duplicate_ids_do_not_hide_missing_jobs(self):
        def page(offset):
            return 4, ([{"Id": "a"}, {"Id": "b"}] if offset == 0 else [{"Id": "b"}, {"Id": "c"}])

        result = scan_pages(page, lambda x: x["Id"])
        self.assertFalse(result.complete)
        self.assertTrue(result.errors)

    def test_empty_page_before_expected_total_is_incomplete(self):
        result = scan_pages(
            lambda offset: (3, [{"Id": "a"}] if offset == 0 else []), lambda x: x["Id"]
        )
        self.assertFalse(result.complete)

    def test_changing_count_is_incomplete(self):
        calls = []

        def page(offset):
            calls.append(offset)
            return (2 if len(calls) == 1 else 3), [{"Id": "a"}, {"Id": "b"}]

        self.assertFalse(scan_pages(page, lambda x: x["Id"]).complete)


class SourceTests(unittest.TestCase):
    def test_discovers_real_active_site_numbers(self):
        class Http:
            def request(self, url, data=None):
                return {
                    "items": [
                        {
                            "SiteNumber": "CX_3002",
                            "SiteURLName": "LateralHiring",
                            "StatusCode": "ORA_ACTIVE",
                        },
                        {
                            "SiteNumber": "CX_3001",
                            "SiteURLName": "CampusHiring",
                            "StatusCode": "ORA_ACTIVE",
                        },
                        {"SiteNumber": "CX_1", "StatusCode": "ORA_INACTIVE"},
                    ],
                    "hasMore": False,
                }

        sites = discover_oracle_sites(Http(), "https://example.com", "GS")
        self.assertEqual({s["SiteNumber"] for s in sites}, {"CX_3001", "CX_3002"})

    def test_oracle_detail_preserves_secondary_locations_and_raw_unit(self):
        class Http:
            def request(self, url, data=None):
                return {
                    "items": [
                        {
                            "Id": "42",
                            "Title": "Analyst",
                            "PrimaryLocation": "Chicago, IL, United States",
                            "secondaryLocations": [{"Name": "New York, NY, United States"}],
                            "ExternalDescriptionStr": "<p>Job</p>",
                            "Category": "Analysts",
                            "requisitionFlexFields": [
                                {
                                    "Prompt": "Base Pay/Salary",
                                    "Value": "New York,NY $100000-$150000",
                                }
                            ],
                        }
                    ]
                }

        source = OracleSource(
            Http(), "JPM", "https://example.com", {"SiteNumber": "CX_1001"}, "123"
        )
        job, raw = source.detail({"Id": "42"})
        self.assertIn("New York, NY, United States", job["locations"])
        self.assertEqual(job["job_level"], "Analysts")
        self.assertEqual(job["salary_fields"], raw["requisitionFlexFields"])

    def test_workday_requires_posted_job_not_silent_empty_payload(self):
        class Http:
            def request(self, url, data=None):
                return {"jobPostingInfo": {"jobReqId": "JR1", "posted": False}}

        source = WorkdaySource(Http(), "New York")
        with self.assertRaises(ValueError):
            source.detail({"externalPath": "/job/a/JR1"})

    def test_workday_later_pages_omit_total_but_keep_jobs(self):
        class Http:
            def request(self, url, data=None):
                if not data["appliedFacets"]:
                    return {
                        "facets": [
                            {
                                "facetParameter": "Location_Region_State_Province",
                                "values": [{"descriptor": "New York", "id": "ny"}],
                            }
                        ]
                    }
                offset = data["offset"]
                return {
                    "total": 3 if offset == 0 else 0,
                    "jobPostings": [
                        {"externalPath": str(i)} for i in range(offset, min(offset + 2, 3))
                    ],
                }

        listing = WorkdaySource(Http(), "New York").list_jobs()
        self.assertTrue(listing.complete)
        self.assertEqual(listing.raw_unique, 3)


class _Response:
    def __init__(self, body, error=None):
        self.body, self.error = body, error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        if self.error:
            raise self.error
        return self.body


class HttpClientTests(unittest.TestCase):
    def test_text_request_returns_the_decoded_page(self):
        seen = {}

        def urlopen(request, timeout):
            seen["accept"] = request.get_header("Accept")
            return _Response("<p>Citi – jobs</p>".encode())

        with mock.patch("bank_salary.sources.urlopen", urlopen):
            body = HttpClient(delay=0.1).request("https://jobs.citi.com/x", text=True)
        self.assertEqual(body, "<p>Citi – jobs</p>")
        self.assertIn("text/html", seen["accept"])

    def test_host_specific_delay_spaces_requests_to_that_host_only(self):
        sleeps = []
        with (
            mock.patch("bank_salary.sources.urlopen", lambda r, timeout: _Response(b"{}")),
            mock.patch("bank_salary.sources.time.monotonic", lambda: 100.0),
            mock.patch("bank_salary.sources.time.sleep", sleeps.append),
        ):
            http = HttpClient(delay=0.35, host_delays={"jobs.citi.com": 1.0})
            for url in (
                "https://jobs.citi.com/a",
                "https://jobs.citi.com/b",
                "https://example.com/a",
            ):
                http.request(url)
        self.assertEqual(sleeps, [1.0])

    def test_a_truncated_response_body_is_retried(self):
        responses = [
            _Response(b"", http.client.IncompleteRead(b"<html>partial")),
            _Response(b'{"ok": 1}'),
        ]
        with (
            mock.patch("bank_salary.sources.urlopen", lambda r, timeout: responses.pop(0)),
            mock.patch("bank_salary.sources.time.sleep", lambda s: None),
        ):
            self.assertEqual(HttpClient(delay=0.1).request("https://jobs.citi.com/x"), {"ok": 1})
        self.assertEqual(responses, [])


BOFA_JOBS = [
    {
        "jobRequisitionId": "1",
        "postingTitle": "Analyst",
        "state": "New York",
        "stateAbbriviation": "NY",
        "locationString": "US - NY - New York - ONE BRYANT PARK (NY1100)",
        "additionalLocations": "",
    },
    {
        "jobRequisitionId": "2",
        "postingTitle": "Banker",
        "state": "Arizona",
        "stateAbbriviation": "AZ",
        "locationString": "US - AZ - Scottsdale (AZ3566)",
        "additionalLocations": "US - NY - Brooklyn - 16 Court St (NY0016),",
    },
    {
        "jobRequisitionId": "3",
        "postingTitle": "Teller",
        "state": "Arizona",
        "stateAbbriviation": "AZ",
        "locationString": "US - AZ - Phoenix (AZ1)",
        "additionalLocations": "US - WA - Bellevue (WA3400),US - WA - Bellevue (WA3400),",
    },
]


class BofaSourceTests(unittest.TestCase):
    def test_lists_the_whole_careers_index_and_keeps_new_york_jobs(self):
        class Http:
            def request(self, url, data=None, text=False):
                # The servlet reads rows as an end index (2026-10-31: start=100&rows=100 is
                # empty, start=100&rows=200 returns the second hundred).
                query = parse_qs(urlsplit(url).query)
                start, end = int(query["start"][0]), int(query["rows"][0])
                return {"totalMatches": 3, "jobsList": BOFA_JOBS[start:end]}

        listing = BofaSource(Http(), rows=2).list_jobs()
        self.assertTrue(listing.complete)
        self.assertEqual(listing.raw_unique, 3)
        self.assertEqual(set(listing.items), {"1", "2"})

    def test_detail_comes_from_the_workday_posting_with_the_same_requisition(self):
        item = {
            "jobRequisitionId": "26025230",
            "postingTitle": "Alternative Investments Sales Strategy Analyst",
            "lob": "Merrill Wealth Management",
            "family": "Client Products and Solutions",
            "locationString": "US - NY - New York - ONE BRYANT PARK (NY1100)",
            "additionalLocations": "US - NJ - Pennington - 1400 American Blvd (NJ2-140),",
        }

        class Http:
            def __init__(self):
                self.calls = []

            def request(self, url, data=None, text=False):
                self.calls.append((url, data))
                if data is not None:
                    return {
                        "total": 2,
                        "jobPostings": [
                            {
                                "externalPath": "/job/New-York/Other_126025230",
                                "bulletFields": ["126025230"],
                            },
                            {
                                "externalPath": "/job/New-York/Alt_26025230-2",
                                "bulletFields": ["26025230"],
                            },
                        ],
                    }
                return {
                    "jobPostingInfo": {
                        "posted": True,
                        "jobReqId": "26025230",
                        "title": "Alternative Investments Sales Strategy Analyst",
                        "jobDescription": "<p>Pay range $1 - $2</p>",
                        "timeType": "Full time",
                        "startDate": "2026-10-30",
                        "externalUrl": "https://ghr.wd1.myworkdayjobs.com/Lateral-US/job/New-York/Alt_26025230-2",
                    }
                }

        http = Http()
        job, raw = BofaSource(http).detail(item)
        self.assertEqual(http.calls[0][1]["searchText"], "26025230")
        self.assertTrue(
            http.calls[1][0].endswith("/wday/cxs/ghr/Lateral-US/job/New-York/Alt_26025230-2")
        )
        self.assertEqual(
            (job["company"], job["requisition_id"], job["department"], job["job_level"]),
            ("BOFA", "26025230", "Merrill Wealth Management", "Client Products and Solutions"),
        )
        self.assertEqual(
            job["locations"],
            [
                "US - NY - New York - ONE BRYANT PARK (NY1100)",
                "US - NJ - Pennington - 1400 American Blvd (NJ2-140)",
            ],
        )
        self.assertEqual((job["posted_at"], job["employment_type"]), ("2026-10-30", "Full time"))
        self.assertEqual(raw["careers_listing"], item)

    def test_detail_fails_without_an_exact_workday_requisition(self):
        class Http:
            def request(self, url, data=None, text=False):
                return {
                    "total": 1,
                    "jobPostings": [
                        {"externalPath": "/job/x/Y_126025230", "bulletFields": ["126025230"]}
                    ],
                }

        with self.assertRaises(ValueError):
            BofaSource(Http()).detail({"jobRequisitionId": "26025230"})


def _citi_page(ids, total):
    items = "".join(
        f'<h3 class="sr-job-item__title"><a class="sr-job-item__link" href="/job/new-york/role-{i}/287/{i}" '
        f'data-job-id="{i}" id="job-{i}">\n Role {i}\n</a></h3><span class="sr-job-item__facet '
        f'sr-job-item__facet-icon sr-job-location">New York, New York, United States</span>'
        for i in ids
    )
    return f'<section data-total-results="{total}" data-records-per-page="2">{items}</section>'


class CitiSourceTests(unittest.TestCase):
    def test_lists_new_york_location_pages_by_job_id(self):
        class Http:
            def __init__(self):
                self.urls = []

            def request(self, url, data=None, text=False):
                self.urls.append(url)
                return _citi_page({1: ["11", "12"], 2: ["13"]}[int(url.rsplit("/", 1)[1])], 3)

        http = Http()
        listing = CitiSource(http).list_jobs()
        self.assertTrue(listing.complete)
        self.assertEqual(set(listing.items), {"11", "12", "13"})
        self.assertEqual(listing.items["12"]["title"], "Role 12")
        self.assertEqual(listing.items["12"]["location"], "New York, New York, United States")
        self.assertTrue(
            all(
                "/search-jobs/" not in u and u.startswith("https://jobs.citi.com/location/")
                for u in http.urls
            )
        )

    def test_detail_reads_the_job_posting_structured_data(self):
        posting = {
            "@type": "JobPosting",
            "title": "NAM Syndicate Middle Office & Operations Head",
            "datePosted": "2026-10-29",
            "identifier": {"name": "Job ID", "value": "261006049"},
            "description": "<p>Role.</p><p>Job Family Group:</p><p>Operations - Transaction Services</p><p>------</p>"
            "<p>Job Family:</p><p>Securities and Derivatives Processing</p><p>------</p>"
            "<p>Primary Location:</p><p>New York New York United States</p><p>------</p>"
            "<p>Primary Location Full Time Salary Range:</p><p>$163,600.00 - $245,400.00</p>",
            "jobLocation": [
                {
                    "address": {
                        "addressLocality": "New York",
                        "addressRegion": "NY",
                        "addressCountry": "US",
                    }
                },
                {
                    "address": {
                        "addressLocality": "Getzville",
                        "addressRegion": "New York",
                        "addressCountry": "United States",
                    }
                },
            ],
        }
        page = (
            '<html><script type="application/ld+json">' + json.dumps(posting) + "</script></html>"
        )

        class Http:
            def request(self, url, data=None, text=False):
                return page

        item = {
            "id": "102602565104",
            "url": "https://jobs.citi.com/job/new-york/x/287/102602565104",
        }
        job, raw = CitiSource(Http()).detail(item)
        self.assertEqual((job["company"], job["requisition_id"]), ("CITI", "102602565104"))
        self.assertEqual(job["department"], "Operations - Transaction Services")
        self.assertEqual(job["job_level"], "Securities and Derivatives Processing")
        self.assertEqual(
            job["locations"], ["New York, NY, US", "Getzville, New York, United States"]
        )
        self.assertEqual(
            (job["posted_at"], job["workday_requisition_id"]), ("2026-10-29", "261006049")
        )
        self.assertIn("Salary Range: $163,600.00 - $245,400.00", job["description"])
        self.assertEqual(raw["json_ld"], posting)

    def test_detail_fields_stop_at_the_next_field_without_a_separator(self):
        posting = {
            "@type": "JobPosting",
            "title": "Trader",
            "description": "<p>Job Family Group:</p><p>Institutional Trading</p><p>Job Family:</p><p>Trading</p>"
            "<p>------</p><p>Job Family Group:</p><p>------</p>",
        }
        page = '<script type="application/ld+json">' + json.dumps(posting) + "</script>"

        class Http:
            def request(self, url, data=None, text=False):
                return page

        item = {
            "id": "102193204304",
            "url": "https://jobs.citi.com/job/new-york/x/287/102193204304",
        }
        job, _ = CitiSource(Http()).detail(item)
        self.assertEqual(
            (job["department"], job["job_level"]), ("Institutional Trading", "Trading")
        )

    def test_detail_accepts_raw_control_characters_inside_structured_data_strings(self):
        # 2026-10-31: one Citi page put a literal tab inside the JSON-LD description.
        page = (
            '<script type="application/ld+json">{"@type": "JobPosting", "title": "Python Developer", '
            '"description": "<p>Build\tservices.</p>"}</script>'
        )

        class Http:
            def request(self, url, data=None, text=False):
                return page

        item = {
            "id": "102161068544",
            "url": "https://jobs.citi.com/job/new-york/x/287/102161068544",
        }
        job, _ = CitiSource(Http()).detail(item)
        self.assertEqual(job["title"], "Python Developer")
        self.assertEqual(job["description"], "Build services.")

    def test_detail_without_a_job_posting_is_an_error(self):
        class Http:
            def request(self, url, data=None, text=False):
                return "<html>Job no longer available</html>"

        with self.assertRaises(ValueError):
            CitiSource(Http()).detail({"id": "1", "url": "https://jobs.citi.com/job/x/287/1"})


if __name__ == "__main__":
    unittest.main()
