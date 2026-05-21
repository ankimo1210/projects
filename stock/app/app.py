"""Dash dashboard entry point.

Run:
    uv run python app/app.py
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc
app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
)
app.title = "stockkit dashboard"

navbar = dbc.NavbarSimple(
    brand="stockkit",
    color="primary",
    dark=True,
    children=[
        dbc.NavItem(dcc.Link(page["name"], href=page["path"], className="nav-link"))
        for page in dash.page_registry.values()
    ],
)

app.layout = dbc.Container(
    [navbar, html.Hr(), dash.page_container],
    fluid=True,
    className="p-3",
)


if __name__ == "__main__":
    from api.server import start as start_api
    start_api(port=8051)
    app.run(debug=True, host="127.0.0.1", port=8050, use_reloader=False)
