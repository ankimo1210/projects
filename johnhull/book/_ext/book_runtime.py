"""Keep the Book's Thebe configuration and local math renderer unique.

The bundled Jupyter Book / Sphinx combination can register the same inline
configuration twice, and register the local MathJax renderer twice. Redeclaring
Thebe's top-level constants raises a SyntaxError even on pages that never launch
it. Keep the first copy of these scripts, preserving every other script.
"""


def deduplicate_thebe_config(app, pagename, templatename, context, doctree):
    """Remove duplicate Thebe declarations and the bundled MathJax renderer."""
    seen = set()
    mathjax_seen = False
    scripts = []
    for script in context.get("script_files", []):
        filename = getattr(script, "filename", "") or ""
        if filename.endswith("mathjax-3.2.2-tex-svg-full.js"):
            if mathjax_seen:
                continue
            mathjax_seen = True
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
