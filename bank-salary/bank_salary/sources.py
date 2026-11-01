"""Read-only public career-site adapters. No login, application, or private endpoints."""

import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from .parsing import text_from_html


class HttpClient:
    def __init__(self, delay=0.35, attempts=3, timeout=30, host_delays=None):
        self.delay, self.attempts, self.timeout = delay, attempts, timeout
        self.host_delays = host_delays or {}
        self.lock = threading.Lock()
        self.next_request = {}

    def request(self, url, data=None, text=False):
        host = urlsplit(url).netloc
        for attempt in range(self.attempts):
            with self.lock:
                pause = max(0, self.next_request.get(host, 0) - time.monotonic())
                if pause:
                    time.sleep(pause)
                self.next_request[host] = time.monotonic() + self.host_delays.get(host, self.delay)
            headers = {
                "User-Agent": "Mozilla/5.0 (public-career-data research)",
                "Accept": "text/html" if text else "application/json",
            }
            body = None
            if data is not None:
                body = json.dumps(data).encode()
                headers["Content-Type"] = "application/json"
            try:
                with urlopen(
                    Request(url, data=body, headers=headers), timeout=self.timeout
                ) as response:
                    raw = response.read(10 * 1024 * 1024 + 1)
                    if len(raw) > 10 * 1024 * 1024:
                        raise ValueError("Response exceeded 10 MiB")
                    return raw.decode("utf-8", errors="replace") if text else json.loads(raw)
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt + 1 == self.attempts:
                    raise RuntimeError(f"HTTP {exc.code}: {urlsplit(url).path}") from exc
                retry = exc.headers.get("Retry-After", "")
                time.sleep(min(30, float(retry)) if retry.isdigit() else 2**attempt)
            except (URLError, TimeoutError, ConnectionError, IncompleteRead) as exc:
                if attempt + 1 == self.attempts:
                    raise RuntimeError(f"Network failure: {exc}") from exc
                time.sleep(2**attempt)
        raise RuntimeError("No HTTP attempts configured")


@dataclass
class Listing:
    items: dict = field(default_factory=dict)
    expected: int = 0
    verified_total: int | None = None
    errors: list = field(default_factory=list)
    raw_unique: int = 0

    @property
    def complete(self):
        return (
            not self.errors
            and self.raw_unique == self.expected
            and self.verified_total == self.expected
        )

    def summary(self):
        return {
            "expected": self.expected,
            "raw_unique": self.raw_unique,
            "selected": len(self.items),
            "verified_total": self.verified_total,
            "complete": self.complete,
            "errors": self.errors,
        }


def scan_pages(fetch_page, key):
    """Bounded enumeration; duplicate IDs, count drift and truncated pages are failures."""
    result = Listing()
    offset = 0
    try:
        for _ in range(1000):
            total, page = fetch_page(offset)
            if offset == 0:
                result.expected = int(total)
            elif total != result.expected:
                result.errors.append(
                    f"Count changed during pagination: {result.expected} -> {total}"
                )
            if not isinstance(page, list):
                raise ValueError("Search response has no list of jobs")
            if not page:
                if offset < result.expected:
                    result.errors.append(f"Empty page at {offset}, expected {result.expected}")
                break
            for item in page:
                item_key = str(key(item))
                if item_key in result.items:
                    result.errors.append(f"Duplicate listing ID: {item_key}")
                result.items[item_key] = item
            offset += len(page)
            if offset >= result.expected:
                break
        else:
            result.errors.append("Pagination exceeded 1000 pages")
        result.raw_unique = len(result.items)
        if result.raw_unique != result.expected:
            result.errors.append(f"Expected {result.expected}, unique IDs {result.raw_unique}")
        final_total, first_page = fetch_page(0)
        result.verified_total = int(final_total)
        if final_total != result.expected:
            result.errors.append(
                f"Count changed at verification: {result.expected} -> {final_total}"
            )
        if any(str(key(item)) not in result.items for item in first_page):
            result.errors.append("First-page membership changed at verification")
    except Exception as exc:
        result.raw_unique = len(result.items)
        result.errors.append(str(exc))
    return result


def _strings(values):
    return [
        v if isinstance(v, str) else v.get("Name", v.get("descriptor", "")) for v in values if v
    ]


def _normalized(company, req, title, description, locations, url, source, **extra):
    return {
        "company": company,
        "requisition_id": str(req),
        "title": title,
        "description": text_from_html(description),
        "locations": list(dict.fromkeys(locations)),
        "url": url,
        "source": source,
        "department": "",
        "job_level": "",
        "employment_type": "",
        "posted_at": "",
        "salary_fields": [],
        **extra,
    }


class WorkdaySource:
    company = "MS"
    label = "MS:workday"
    base = "https://ms.wd5.myworkdayjobs.com"
    api = base + "/wday/cxs/ms/External"

    def __init__(self, http, state_name):
        self.http, self.state_name = http, state_name

    def list_jobs(self):
        initial = self.http.request(
            self.api + "/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
        )
        states = [
            f
            for f in initial["facets"]
            if f.get("facetParameter") == "Location_Region_State_Province"
        ]
        matches = [
            v
            for f in states
            for v in f["values"]
            if v["descriptor"].casefold() == self.state_name.casefold()
        ]
        if len(matches) != 1:
            raise ValueError(f"Could not uniquely resolve Workday state {self.state_name}")
        initial_total = None

        def page(offset):
            nonlocal initial_total
            x = self.http.request(
                self.api + "/jobs",
                {
                    "appliedFacets": {"Location_Region_State_Province": [matches[0]["id"]]},
                    "limit": 20,
                    "offset": offset,
                    "searchText": "",
                },
            )
            if offset == 0:
                initial_total = x["total"]
            # Workday omits its aggregation on later pages: total=0 with valid jobs.
            # The generic scanner still compares the real first-page total before/after.
            total = (
                initial_total if offset > 0 and x["total"] == 0 and x["jobPostings"] else x["total"]
            )
            return total, x["jobPostings"]

        return scan_pages(page, lambda j: j["externalPath"])

    def requisition_id(self, item):
        if item.get("bulletFields"):
            return str(item["bulletFields"][0])
        raise ValueError("Workday listing has no requisition ID")

    def stub(self, item):
        return {
            "title": item.get("title", ""),
            "url": self.base + "/en-US/External" + item["externalPath"],
            "source": self.label,
            "locations": [item.get("locationsText", "")],
        }

    def detail(self, item):
        payload = self.http.request(self.api + item["externalPath"])
        info = payload["jobPostingInfo"]
        if not info.get("posted") or not info.get("title"):
            raise ValueError("Workday job is no longer publicly posted or detail is incomplete")
        locations = [info.get("location", ""), *_strings(info.get("additionalLocations", []))]
        job = _normalized(
            "MS",
            info["jobReqId"],
            info["title"],
            info.get("jobDescription", ""),
            locations,
            info.get("externalUrl") or self.stub(item)["url"],
            self.label,
            posted_at=info.get("startDate", ""),
            employment_type=info.get("timeType", ""),
            department=info.get("jobFamily", {}).get("descriptor", "")
            if isinstance(info.get("jobFamily"), dict)
            else "",
        )
        return job, payload


def discover_oracle_sites(http, host, company):
    data = http.request(
        host + "/hcmRestApi/resources/latest/recruitingCESites?onlyData=true&limit=100"
    )
    if data.get("hasMore"):
        raise ValueError("Site metadata was truncated")
    sites = []
    for site in data["items"]:
        if site.get("StatusCode") != "ORA_ACTIVE":
            continue
        if company == "GS" and site.get("SiteURLName") not in ("LateralHiring", "CampusHiring"):
            continue
        if company == "JPM" and site.get("SiteNumber") not in ("CX_1001", "CX_1002", "CX_2001"):
            continue
        if not site.get("SiteNumber"):
            raise ValueError("Active site has no real SiteNumber")
        sites.append(site)
    if not sites:
        raise ValueError(f"No supported active public sites discovered for {company}")
    return sorted(sites, key=lambda s: s["SiteNumber"])


class OracleSource:
    def __init__(self, http, company, host, site, location_id):
        self.http, self.company, self.host, self.site, self.location_id = (
            http,
            company,
            host,
            site,
            location_id,
        )
        self.label = f"{company}:oracle:{site['SiteNumber']}"

    def _get(self, resource, finder, expand):
        return self.http.request(
            self.host
            + "/hcmRestApi/resources/latest/"
            + resource
            + "?"
            + urlencode({"onlyData": "true", "expand": expand, "finder": finder})
        )

    def list_jobs(self):
        def page(offset):
            finder = f"findReqs;siteNumber={self.site['SiteNumber']},locationId={self.location_id},limit=100,offset={offset},sortBy=POSTING_DATES_DESC"
            data = self._get("recruitingCEJobRequisitions", finder, "requisitionList")
            if len(data["items"]) != 1:
                raise ValueError("Unexpected Oracle search envelope")
            x = data["items"][0]
            if x.get("SiteNumber") != self.site["SiteNumber"]:
                raise ValueError("Oracle returned a different career site")
            return x["TotalJobsCount"], x.get("requisitionList", [])

        return scan_pages(page, lambda j: j["Id"])

    def requisition_id(self, item):
        return str(item["Id"])

    def stub(self, item):
        route = self.site.get("SiteURLName") or self.site["SiteNumber"]
        return {
            "title": item.get("Title", ""),
            "url": self.host + f"/hcmUI/CandidateExperience/en/sites/{route}/job/{item['Id']}",
            "source": self.label,
            "locations": [item.get("PrimaryLocation", "")],
        }

    def detail(self, item):
        data = self._get(
            "recruitingCEJobRequisitionDetails",
            f"ById;Id={item['Id']},siteNumber={self.site['SiteNumber']}",
            "all",
        )
        if len(data["items"]) != 1:
            raise ValueError("Oracle job detail is absent")
        x = data["items"][0]
        if not x.get("Title") or str(x.get("Id")) != str(item["Id"]):
            raise ValueError("Oracle returned a mismatched or incomplete detail")
        locations = [x.get("PrimaryLocation", ""), *_strings(x.get("secondaryLocations", []))]
        job = _normalized(
            self.company,
            x["Id"],
            x["Title"],
            x.get("ExternalDescriptionStr", ""),
            locations,
            self.stub(item)["url"],
            self.label,
            posted_at=x.get("ExternalPostedStartDate") or "",
            employment_type=x.get("JobSchedule") or "",
            department=x.get("BusinessUnit") or x.get("Department") or "",
            job_level=x.get("Category") or "",
            salary_fields=x.get("requisitionFlexFields", []),
        )
        return job, x


class EightfoldSource:
    company = "MS"
    label = "MS:eightfold"
    host = "https://morganstanley.eightfold.ai"

    def __init__(self, http, location="New York", state_code="NY"):
        self.http, self.location, self.state_code = http, location, state_code

    def list_jobs(self):
        def page(offset):
            p = {"domain": "morganstanley.com", "location": self.location, "start": offset}
            x = self.http.request(self.host + "/api/pcsx/search?" + urlencode(p))["data"]
            return x["count"], x["positions"]

        result = scan_pages(page, lambda j: j["id"])
        pattern = re.compile(r"(?:^|,\s*)" + re.escape(self.state_code) + r"(?:,|$)", re.I)
        result.items = {
            k: v
            for k, v in result.items.items()
            if any(pattern.search(s) for s in v.get("standardizedLocations", []))
        }
        return result

    def requisition_id(self, item):
        return str(item.get("atsJobId") or item["displayJobId"])

    def stub(self, item):
        return {
            "title": item.get("name", ""),
            "url": self.host + item.get("positionUrl", f"/careers/job/{item['id']}"),
            "source": self.label,
            "locations": item.get("locations", []),
        }

    def detail(self, item):
        p = {"domain": "morganstanley.com", "position_id": item["id"], "hl": "en"}
        x = self.http.request(self.host + "/api/pcsx/position_details?" + urlencode(p))["data"]
        if not x.get("name") or str(x.get("id")) != str(item["id"]):
            raise ValueError("Eightfold returned a mismatched or incomplete detail")
        stamp = datetime.fromtimestamp(x["postedTs"], UTC).isoformat() if x.get("postedTs") else ""
        job = _normalized(
            "MS",
            self.requisition_id(x),
            x["name"],
            x.get("jobDescription", ""),
            x.get("locations", []),
            x.get("publicUrl") or self.stub(x)["url"],
            self.label,
            posted_at=stamp,
            department=x.get("department") or "",
            job_level=" | ".join(x.get("efcustomTextPcsPostingJobLevel", [])),
            employment_type=" | ".join(x.get("efcustomTextTextTimeType", [])),
        )
        return job, x


class BofaSource:
    """The careers-site index (with state codes) sets the scope; Workday has the posting."""

    company = "BOFA"
    label = "BOFA:careers"
    careers = "https://careers.bankofamerica.com"
    workday = "https://ghr.wd1.myworkdayjobs.com"
    api = workday + "/wday/cxs/ghr/Lateral-US"

    def __init__(self, http, state_code="NY", rows=100):
        self.http, self.state_code, self.rows = http, state_code, rows

    @staticmethod
    def _locations(item):
        values = [
            item.get("locationString") or "",
            *(item.get("additionalLocations") or "").split(","),
        ]
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))

    def list_jobs(self):
        def page(offset):
            # The servlet treats rows as the end index: start=100&rows=100 is empty.
            p = {"start": offset, "rows": offset + self.rows, "search": "getAllJobs"}
            x = self.http.request(self.careers + "/services/jobssearchservlet?" + urlencode(p))
            return x["totalMatches"], x["jobsList"]

        result = scan_pages(page, lambda j: j["jobRequisitionId"])
        prefix = f"US - {self.state_code} - "
        result.items = {
            k: v
            for k, v in result.items.items()
            if v.get("stateAbbriviation") == self.state_code
            or any(s.startswith(prefix) for s in self._locations(v))
        }
        return result

    def requisition_id(self, item):
        return str(item["jobRequisitionId"])

    def stub(self, item):
        return {
            "title": item.get("postingTitle", ""),
            "url": self.careers + item.get("jcrURL", ""),
            "source": self.label,
            "locations": self._locations(item),
        }

    def detail(self, item):
        req = self.requisition_id(item)
        found = self.http.request(
            self.api + "/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": req}
        )
        paths = [
            p["externalPath"]
            for p in found.get("jobPostings", [])
            if [str(b) for b in p.get("bulletFields", [])[:1]] == [req]
        ]
        if len(paths) != 1:
            raise ValueError(f"Workday search found {len(paths)} postings for requisition {req}")
        payload = self.http.request(self.api + paths[0])
        info = payload["jobPostingInfo"]
        if not info.get("posted") or not info.get("title") or str(info.get("jobReqId")) != req:
            raise ValueError("Workday job is not publicly posted or does not match the requisition")
        job = _normalized(
            "BOFA",
            req,
            info["title"],
            info.get("jobDescription", ""),
            self._locations(item),
            info.get("externalUrl") or self.workday + "/Lateral-US" + paths[0],
            self.label,
            posted_at=info.get("startDate", ""),
            employment_type=info.get("timeType", ""),
            department=item.get("lob") or "",
            job_level=item.get("family") or "",
        )
        return job, {"careers_listing": item, **payload}


class CitiSource:
    """jobs.citi.com location and job pages only: robots.txt disallows /search-jobs/ and the
    Workday site, and Citigroup's terms restrict scraping (collection rests on the user's permission)."""

    company = "CITI"
    label = "CITI:jobs.citi.com"
    host = "https://jobs.citi.com"
    item = re.compile(
        r'<a class="sr-job-item__link" href="(?P<path>/job/[^"]+)" data-job-id="(?P<id>\d+)"[^>]*>'
        r'(?P<title>.*?)</a>(?P<rest>.*?)(?=<a class="sr-job-item__link"|$)',
        re.S,
    )

    def __init__(self, http, location_path="/location/new-york-jobs/287/6252001-5128638/3"):
        self.http, self.location_path = http, location_path

    def list_jobs(self):
        per_page = []

        def page(offset):
            number = offset // per_page[0] + 1 if per_page else 1
            text = self.http.request(f"{self.host}{self.location_path}/{number}", text=True)
            total = re.search(r'data-total-results="(\d+)"', text)
            size = re.search(r'data-records-per-page="(\d+)"', text)
            if not total or not size:
                raise ValueError("Citi location page has no result count")
            if not per_page:
                per_page.append(int(size.group(1)))
            items = []
            for m in self.item.finditer(text):
                location = re.search(r'sr-job-location">([^<]*)<', m.group("rest"))
                items.append(
                    {
                        "id": m.group("id"),
                        "url": self.host + m.group("path"),
                        "title": text_from_html(m.group("title")),
                        "location": text_from_html(location.group(1)) if location else "",
                    }
                )
            return int(total.group(1)), items

        return scan_pages(page, lambda j: j["id"])

    def requisition_id(self, item):
        return str(item["id"])

    def stub(self, item):
        return {
            "title": item.get("title", ""),
            "url": item["url"],
            "source": self.label,
            "locations": [item.get("location", "")],
        }

    def detail(self, item):
        text = self.http.request(item["url"], text=True)
        posting = None
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
            # Pages can carry raw tabs or newlines inside JSON-LD strings.
            data = json.loads(block, strict=False)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                posting = data
        if not posting or not posting.get("title"):
            raise ValueError("Citi page has no JobPosting data (no longer posted?)")
        description = text_from_html(posting.get("description", ""))

        def field(name):
            # Some pages omit the separator before the next field.
            m = re.search(
                re.escape(name) + r":\s*(.+?)\s*(?:-{3,}|(?=\bJob Family:)|$)", description
            )
            return m.group(1) if m else ""

        locations = []
        for place in posting.get("jobLocation", []):
            a = place.get("address", {}) if isinstance(place, dict) else {}
            parts = (a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry"))
            locations.append(", ".join(v for v in parts if v))
        job = _normalized(
            "CITI",
            self.requisition_id(item),
            posting["title"],
            posting.get("description", ""),
            locations,
            item["url"],
            self.label,
            posted_at=posting.get("datePosted", ""),
            department=field("Job Family Group"),
            job_level=field("Job Family"),
            workday_requisition_id=str((posting.get("identifier") or {}).get("value", "")),
        )
        return job, {"url": item["url"], "json_ld": posting}
