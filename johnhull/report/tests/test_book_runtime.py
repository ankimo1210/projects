from types import SimpleNamespace

from johnhull.book._ext.book_runtime import deduplicate_thebe_config


def test_page_scripts_keep_one_local_mathjax_and_identical_thebe_declaration():
    mathjax = SimpleNamespace(
        filename="_static/mathjax-3.2.2-tex-svg-full.js",
        attributes={"defer": "defer"},
    )
    mathjax_duplicate = SimpleNamespace(filename=mathjax.filename, attributes={})
    thebe = SimpleNamespace(filename=None, attributes={"body": "const THEBE_JS_URL = 'a';"})
    thebe_duplicate = SimpleNamespace(filename=None, attributes=thebe.attributes.copy())
    other_thebe = SimpleNamespace(filename="", attributes={"body": "const THEBE_JS_URL = 'b';"})
    other_script = SimpleNamespace(filename="_static/other.js", attributes={})
    context = {
        "script_files": [
            mathjax,
            other_script,
            mathjax_duplicate,
            thebe,
            thebe_duplicate,
            other_thebe,
            other_script,
        ]
    }

    deduplicate_thebe_config(None, "page", None, context, None)

    assert context["script_files"] == [
        mathjax,
        other_script,
        thebe,
        other_thebe,
        other_script,
    ]


def test_page_without_script_files_remains_valid():
    context = {}
    deduplicate_thebe_config(None, "page", None, context, None)
    assert context["script_files"] == []
