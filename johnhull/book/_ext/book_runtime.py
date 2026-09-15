"""Keep the Book's Thebe bootstrap declaration unique.

The bundled Jupyter Book / Sphinx combination can register the same inline
configuration twice. Redeclaring its top-level constants raises a SyntaxError
even on pages that never launch Thebe. Keep the first identical declaration,
preserving the order and content of every other script.
"""


def deduplicate_thebe_config(app, pagename, templatename, context, doctree):
    """Remove only repeated, identical Thebe configuration script bodies."""
    seen = set()
    scripts = []
    for script in context.get("script_files", []):
        body = getattr(script, "attributes", {}).get("body", "")
        if body.startswith("const THEBE_JS_URL"):
            if body in seen:
                continue
            seen.add(body)
        scripts.append(script)
    context["script_files"] = scripts


def setup(app):
    """Register the page-context repair after normal script collection."""
    app.connect("html-page-context", deduplicate_thebe_config, priority=900)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
