"""Command line entry point."""

from __future__ import annotations

from pathlib import Path

import click

from .catalog import load_catalog
from .ingest import default_catalog_root
from .status import compute_status, load_validated
from .store import connect


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
    click.echo(
        "  ".join(
            f"{state}={counts.get(state, 0)}"
            for state in ("declared", "fetching", "parsed", "validated")
        )
    )
