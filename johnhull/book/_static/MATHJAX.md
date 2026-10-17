# Offline mathematical notation

The Book already uses MathJax 3 to display LaTeX. The additional equations in
volumes 18–25 must satisfy the Beyond-Hull release contract without a CDN.
The same renderer is therefore packaged locally as the SVG full component;
this is a browser asset, not a new Python or npm installation requirement.

- Version: 3.2.2, fixed rather than the previous floating major-version URL.
- Source: <https://github.com/mathjax/MathJax/tree/3.2.2>.
- Bundle: `es5/tex-svg-full.js`, saved as `mathjax-3.2.2-tex-svg-full.js`.
- License: Apache-2.0, retained in `mathjax-3.2.2-LICENSE.txt`.
- SHA-256 values: `release_manifest.json` → `vendored_book_assets`.

The full SVG component includes its TeX extensions and mathematical font data
([component documentation](https://docs.mathjax.org/en/v3.2/web/components/combined.html)).
The optional context menu is disabled to avoid on-demand component downloads
([menu documentation](https://docs.mathjax.org/en/v3.2/options/menu.html)).
Ordinary selection of the surrounding text and the notebook's LaTeX source
remain available. The global setting also makes existing Book equations local.

After changing these files, run `make hull-book` and `make hull-release-check`,
then check equation rendering in the browser. The release checker verifies the
asset fingerprints and rejects remote runtime assets on Beyond-Hull pages.
