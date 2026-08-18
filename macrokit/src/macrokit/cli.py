"""Command line entry point."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import click
import duckdb

from .catalog import load_catalog
from .expectations import compute as compute_expectations
from .ingest import default_catalog_root
from .panel import event_panel
from .snapshot import save_snapshot
from .sources.esri_calendar import EsriCalendarAdapter
from .sources.esri_gdp import EsriGdpAdapter, EsriGdpError
from .sources.mof_jgb import MofJgbAdapter
from .status import STATUS_ORDER, compute_status, load_validated
from .store import (
    ReleaseEvent,
    connect,
    insert_expectations,
    insert_observations,
    insert_rates,
    insert_releases,
    recompute_vintage_seq,
)

GDP_INDICATOR = "jp_real_gdp_qoq_saar"
DEFAULT_EXPECTATION_METHODS = ("random_walk", "prior_vintage", "ar_model")

# Seconds to wait between fetching one release's GDP table and the next. The
# ESRI archive has no per-indicator addressing or rate-limit header, so this
# is a fixed, conservative pause (see docs/superpowers/specs/2026-08-17-
# macrokit-design.md §5.4: static CSV/HTML sources get 1 req/sec) rather than
# anything adaptive.
VINTAGE_THROTTLE_SECONDS = 1.0


@click.group()
@click.option(
    "--data-root",
    type=click.Path(path_type=Path),
    default=Path("macrokit/data"),
    show_default=True,
    help="Where snapshots and the DuckDB file live.",
)
@click.pass_context
def main(ctx: click.Context, data_root: Path) -> None:
    """macrokit -- point-in-time macro indicators for Japan and the US."""
    ctx.ensure_object(dict)
    ctx.obj["data_root"] = data_root
    ctx.obj["catalog"] = load_catalog(default_catalog_root())


@main.group("catalog")
def catalog_group() -> None:
    """Inspect the indicator catalog."""


@catalog_group.command("list")
@click.pass_context
def catalog_list(ctx: click.Context) -> None:
    for name, indicator in sorted(ctx.obj["catalog"].items()):
        click.echo(f"{name:<28} {indicator.country}  {indicator.block:<10} {indicator.title_ja}")


@main.command("status")
@click.pass_context
def status_command(ctx: click.Context) -> None:
    """Show each indicator's derived implementation state."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    validated = load_validated(data_root)
    raw_root = data_root / "raw"

    counts: dict[str, int] = {}
    for name, indicator in sorted(ctx.obj["catalog"].items()):
        state = compute_status(indicator, con=con, raw_root=raw_root, validated=validated)
        counts[state] = counts.get(state, 0) + 1
        click.echo(f"{name:<28} {state}")

    click.echo("")
    click.echo("  ".join(f"{state}={counts.get(state, 0)}" for state in STATUS_ORDER))


@main.command("rates")
@click.pass_context
def rates_command(ctx: click.Context) -> None:
    """Ingest the MoF JGB constant-maturity curve (both CSVs, unioned)."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    now = datetime.now(UTC)
    adapter = MofJgbAdapter()

    payloads = adapter.fetch_raw()
    for content, url, status in payloads:
        save_snapshot(
            data_root / "raw", adapter.source, "jgb_curve", content,
            ingested_at=now, url=url, http_status=status, filename=url.rsplit("/", 1)[-1],
        )
    rows = adapter.parse(payloads, ingested_at=now)
    inserted = insert_rates(con, rows)
    click.echo(f"rates: {len(rows)} rows parsed, {inserted} inserted")


@main.group("gdp")
def gdp_group() -> None:
    """Japanese GDP releases, vintages, expectations and the event panel."""


def _load_events(
    con: duckdb.DuckDBPyConnection,
    indicator: str,
    *,
    scheduled: bool | None = None,
    exclude_kinds: tuple[str, ...] = (),
) -> list[ReleaseEvent]:
    """Reconstruct ReleaseEvent rows from the `releases` table, oldest release first."""
    query = (
        "SELECT indicator, period_start, period_end, release_kind, release_date, "
        "scheduled, source, source_url, ingested_at FROM releases WHERE indicator = ?"
    )
    params: list = [indicator]
    if scheduled is not None:
        query += " AND scheduled = ?"
        params.append(scheduled)
    query += " ORDER BY release_date"
    events = [ReleaseEvent(*row) for row in con.execute(query, params).fetchall()]
    return [e for e in events if e.release_kind not in exclude_kinds]


@gdp_group.command("releases")
@click.pass_context
def gdp_releases_command(ctx: click.Context) -> None:
    """Ingest the ESRI GDP release calendar (1st/2nd preliminary, and revisions)."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    now = datetime.now(UTC)
    adapter = EsriCalendarAdapter()

    content, url, status = adapter.fetch_raw()
    save_snapshot(
        data_root / "raw", adapter.source, GDP_INDICATOR, content,
        ingested_at=now, url=url, http_status=status, filename="e-stat_sna.xml",
    )
    events = adapter.parse(content, indicator=GDP_INDICATOR, source_url=url, ingested_at=now)
    inserted = insert_releases(con, events)
    click.echo(f"releases: {len(events)} parsed, {inserted} inserted")


@gdp_group.command("vintages")
@click.pass_context
def gdp_vintages_command(ctx: click.Context) -> None:
    """Ingest each release's own GDP table -- the true vintage history.

    Reads events from the `releases` table (run `gdp releases` first). Skips
    releases still `scheduled` (no table to fetch yet) and `2nd_prelim_revised`
    releases (no derivable menu URL -- see `sources/esri_gdp.menu_url`).
    """
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    indicator = ctx.obj["catalog"][GDP_INDICATOR]
    source_ref = indicator.source_ref
    now = datetime.now(UTC)
    adapter = EsriGdpAdapter()

    events = _load_events(
        con, GDP_INDICATOR, scheduled=False, exclude_kinds=("2nd_prelim_revised",)
    )
    parsed = inserted = skipped = 0
    for i, event in enumerate(events):
        # fetch, snapshot, and parse all live in one try: a release whose page
        # layout or column headers don't match what every other release uses
        # (both happen in the wild -- see the docstring above) must not abort
        # the whole backfill. The snapshot still gets banked even when parsing
        # then fails, per snapshot.py's "snapshot first, parse second" rule.
        try:
            content, csv_url, status = adapter.fetch_release(
                event,
                series_label=source_ref["series_label"],
                stem_prefix=source_ref["stem_prefix"],
            )
            save_snapshot(
                data_root / "raw", adapter.source, GDP_INDICATOR, content,
                ingested_at=now, url=csv_url, http_status=status,
                filename=csv_url.rsplit("/", 1)[-1],
            )
            rows = adapter.parse(
                event, content, indicator=GDP_INDICATOR, column=source_ref["column"],
                source_url=csv_url, ingested_at=now,
            )
        except EsriGdpError as exc:
            click.echo(f"  skip {event.period_start} {event.release_kind}: {exc}")
            skipped += 1
        else:
            parsed += len(rows)
            inserted += insert_observations(con, rows)
        if i < len(events) - 1:
            time.sleep(VINTAGE_THROTTLE_SECONDS)

    # Recompute rather than trust what `adapter.parse` stamped on each row:
    # a window function over the whole indicator is order-independent and
    # safe to re-run even after a partial backfill, so it cannot be skipped
    # here without silently reintroducing the bug it fixes.
    recompute_vintage_seq(con, GDP_INDICATOR)

    click.echo(
        f"vintages: {len(events)} releases, {parsed} rows parsed, "
        f"{inserted} inserted, {skipped} skipped"
    )


@gdp_group.command("expectations")
@click.option(
    "--methods",
    default=",".join(DEFAULT_EXPECTATION_METHODS),
    show_default=True,
    help="Comma-separated expectation methods to compute.",
)
@click.pass_context
def gdp_expectations_command(ctx: click.Context, methods: str) -> None:
    """Compute pre-release expectations for every ingested GDP release."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    method_names = tuple(m.strip() for m in methods.split(",") if m.strip())

    events = _load_events(con, GDP_INDICATOR)
    try:
        rows = compute_expectations(con, events, methods=method_names)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    # `insert_expectations` uses INSERT OR REPLACE, so its return value counts
    # only rows whose key was new. Reporting that alone would print "0 inserted"
    # after a repair re-run that had in fact corrected every stale value -- which
    # reads as "nothing happened". Report both halves.
    inserted = insert_expectations(con, rows)
    updated = len(rows) - inserted
    click.echo(
        f"expectations: {len(events)} events, {len(rows)} computed, "
        f"{inserted} new, {updated} updated"
    )


@gdp_group.command("panel")
@click.option(
    "--out", type=click.Path(path_type=Path), required=True, help="CSV path to write the panel to."
)
@click.pass_context
def gdp_panel_command(ctx: click.Context, out: Path) -> None:
    """Export the release/rate-move event panel to CSV."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    frame = event_panel(con, indicator=GDP_INDICATOR)
    if frame.empty:
        click.echo("no events")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    click.echo(
        f"panel: {len(frame)} rows written to {out} "
        f"({frame['release_date'].min()} to {frame['release_date'].max()})"
    )
