"""Collect a bounded snapshot, export it, and report actual coverage."""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .audit import audit
from .sources import (
    BofaSource,
    CitiSource,
    EightfoldSource,
    HttpClient,
    OracleSource,
    WorkdaySource,
    discover_oracle_sites,
)
from .storage import Store, utcnow

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "_data" / "bank-salary"
HOSTS = {"GS": "https://hdpc.fa.us2.oraclecloud.com", "JPM": "https://jpmc.fa.oraclecloud.com"}
COMPANIES = ("MS", "GS", "JPM", "BOFA", "CITI")
# Citigroup's terms restrict scraping; its pages are read slowly (see CitiSource).
CITI_DELAY = 1.0


def log(message):
    print(f"[{utcnow()}] {message}", flush=True)


def http_client(args):
    return HttpClient(delay=args.delay, host_delays={"jobs.citi.com": max(args.delay, CITI_DELAY)})


def _sources(http, company, args):
    if company == "BOFA":
        return [BofaSource(http, args.state_code)]
    if company == "CITI":
        return [CitiSource(http)]
    if company == "MS":
        return [
            WorkdaySource(http, args.state_name),
            EightfoldSource(http, args.ms_location, args.state_code),
        ]
    sites = discover_oracle_sites(http, HOSTS[company], company)
    location_id = args.gs_location_id if company == "GS" else args.jpm_location_id
    return [OracleSource(http, company, HOSTS[company], site, location_id) for site in sites]


def _fetch(req, candidates):
    errors = []
    for source, item in candidates:
        try:
            job, payload = source.detail(item)
            if str(job["requisition_id"]) != req:
                raise ValueError(f"Detail ID {job['requisition_id']} differs from listing {req}")
            return job, payload, errors
        except Exception as exc:
            errors.append(f"{source.label}: {exc}")
    return None, None, errors


def collect(args, store):
    companies = list(dict.fromkeys(args.companies.split(",")))
    config = {
        k: getattr(args, k)
        for k in ("state_name", "state_code", "gs_location_id", "jpm_location_id", "ms_location")
    }
    config["companies"] = sorted(companies)
    config["scope"] = "public career-site listings containing the selected state; all roles"
    run_id = store.start_run(config)
    report = {
        "sources": {},
        "companies": {},
        "limitations": [
            "GS Higher catalog is not independently enumerated; coverage refers to the discovered active Oracle Lateral/Campus sites.",
            "Public listings are observed over an interval, not an atomic snapshot; an actual hiring end date is never inferred.",
            "Salary periods absent from the original remain unspecified; base pay is not total compensation.",
            "MS Workday state filter is primary; the Eightfold global index supplies separately labelled NY matches and supplements.",
            "BOFA scope is the careers-site index filtered by NY state codes; details come from the Workday Lateral-US posting. Campus roles (tal.net) are not covered.",
            "CITI is read only from jobs.citi.com New York State location and job pages (robots.txt disallows /search-jobs/ and the Workday site); one salary range per posting, for its primary location.",
        ],
    }
    http = http_client(args)
    all_complete = True
    log(f"Run {run_id}; output={args.output}; companies={companies}")
    try:
        for company in companies:
            candidates, listings = {}, []
            company_errors = []
            try:
                sources = _sources(http, company, args)
            except Exception as exc:
                report["companies"][company] = {"complete": False, "errors": [str(exc)]}
                store.record_listing(run_id, company, [], False)
                all_complete = False
                continue
            for source in sources:
                log(f"{source.label}: enumerating all pages")
                try:
                    listing = source.list_jobs()
                    listings.append((source, listing))
                    report["sources"][source.label] = listing.summary()
                    log(f"{source.label}: {listing.summary()}")
                    for item in listing.items.values():
                        req = source.requisition_id(item)
                        candidates.setdefault(req, []).append((source, item))
                    if not listing.complete:
                        company_errors.extend(f"{source.label}: {e}" for e in listing.errors)
                except Exception as exc:
                    company_errors.append(f"{source.label}: {exc}")
                    report["sources"][source.label] = {"complete": False, "errors": [str(exc)]}
            stubs = {req: options[0][0].stub(options[0][1]) for req, options in candidates.items()}
            store.record_listing(run_id, company, stubs, False)
            success, failures, fallbacks = 0, 0, []
            log(f"{company}: {len(candidates)} unique requisitions; fetching every detail")
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {
                    pool.submit(_fetch, req, options): req for req, options in candidates.items()
                }
                for future in as_completed(futures):
                    req = futures[future]
                    job, payload, errors = future.result()
                    if job is None:
                        failures += 1
                        store.record_error(run_id, company, req, " | ".join(errors))
                    else:
                        store.save(run_id, job, payload)
                        success += 1
                        if errors:
                            fallbacks.append(
                                {
                                    "requisition_id": req,
                                    "errors": errors,
                                    "resolved_source": job["source"],
                                }
                            )
                    done = success + failures
                    if done % 50 == 0 or done == len(candidates):
                        log(
                            f"{company}: details {done}/{len(candidates)}; success={success}, failed={failures}"
                        )
            # Re-enumerate after the detail interval, rather than treating the initial count as timeless.
            for source, original in listings:
                try:
                    final = source.list_jobs()
                    original_ids, final_ids = set(original.items), set(final.items)
                    check = final.summary()
                    check["added_since_start"] = sorted(final_ids - original_ids)
                    check["removed_since_start"] = sorted(original_ids - final_ids)
                    report["sources"][source.label]["after_details"] = check
                    if not final.complete or final_ids != original_ids:
                        company_errors.append(
                            f"{source.label}: listing changed or failed during final enumeration"
                        )
                except Exception as exc:
                    company_errors.append(f"{source.label}: final enumeration failed: {exc}")
            complete = not company_errors and failures == 0 and len(listings) == len(sources)
            store.record_listing(run_id, company, stubs, complete)
            report["companies"][company] = {
                "unique_jobs": len(candidates),
                "detail_success": success,
                "detail_failed": failures,
                "complete": complete,
                "errors": company_errors,
                "fallbacks": fallbacks,
                "source_memberships": sum(len(v) for v in candidates.values()),
            }
            all_complete = all_complete and complete
            log(f"{company}: complete_in_observed_source_scope={complete}; errors={company_errors}")
        status = "complete" if all_complete else "partial"
        store.finish_run(run_id, status, report)
    except BaseException as exc:
        report["interruption"] = f"{type(exc).__name__}: {exc}"
        store.finish_run(run_id, "interrupted", report)
        store.export(run_id, args.output)
        raise
    store.export(run_id, args.output)
    validation = store.validate(run_id)
    (args.output / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(
        json.dumps(
            {
                "run_id": run_id,
                "status": status,
                "integrity_ok": validation["integrity_ok"],
                "companies": validation["companies"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "complete" and validation["integrity_ok"] else 2


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Public MS / GS / JPM / BOFA / CITI salary observations (no production dependencies)."
    )
    parser.add_argument("command", choices=("collect", "export", "validate", "reparse", "audit"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--run-id", type=int)
    parser.add_argument(
        "--companies", default=",".join(COMPANIES), help="Comma-separated: " + ",".join(COMPANIES)
    )
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument(
        "--delay", type=float, default=0.35, help="Minimum seconds between requests per host"
    )
    parser.add_argument("--state-name", default="New York", help="Workday state descriptor")
    parser.add_argument(
        "--state-code", default="NY", help="Eightfold / BofA careers-site state code"
    )
    parser.add_argument(
        "--ms-location",
        default="",
        help="Eightfold location query; empty = enumerate global index then filter state",
    )
    parser.add_argument(
        "--gs-location-id",
        default="300000645029810",
        help="Oracle geography ID; default New York state",
    )
    parser.add_argument(
        "--jpm-location-id",
        default="300000020657200",
        help="Oracle geography ID; default New York state",
    )
    args = parser.parse_args(argv)
    if not set(args.companies.split(",")) <= set(COMPANIES) or not args.companies:
        parser.error("companies must be drawn from " + ",".join(COMPANIES))
    if not 1 <= args.workers <= 8 or args.delay < 0.1:
        parser.error("workers must be 1..8 and delay must be >= 0.1 seconds")
    if args.command != "collect" and not (args.output / "jobs.sqlite").exists():
        parser.error("No jobs.sqlite exists at the selected output directory")
    store = Store(args.output / "jobs.sqlite")
    try:
        if args.command == "collect":
            return collect(args, store)
        run_id = args.run_id if args.run_id is not None else store.latest_run()
        store.validate(run_id)
        if args.command == "audit":
            result = audit(store, run_id, args.output)
            (args.output / "audit.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 2
        if args.command == "reparse":
            store.reparse(run_id)
        if args.command in ("export", "reparse"):
            store.export(run_id, args.output)
        result = store.validate(run_id)
        (args.output / "validation.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["integrity_ok"] else 2
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
