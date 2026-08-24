# Roadmap

GitHub [issue #28](https://github.com/y-marui/python-matplotlib-extension/issues/28) is the canonical roadmap. Sub-issues are outcome-sized; implementation checklists remain in pull requests and do not become one issue per task.

## Version 1 Foundation

- [#30 Canonical safe package and core round-trip](https://github.com/y-marui/python-matplotlib-extension/issues/30)
- [#29 Editable PDF, PNG, and SVG bindings](https://github.com/y-marui/python-matplotlib-extension/issues/29)

This release also writes and reads a generic CFB/OLE Package whose native file is the same user-facing editable PNG. It is a passive data carrier: a separate Python process or console restores that PNG with `loadfig()` and performs all editing through Matplotlib.

## Coverage and Hardening

- [#31 Expanded artist allowlist and numeric data recovery](https://github.com/y-marui/python-matplotlib-extension/issues/31)
- [#32 Parser fuzzing and compatibility fixtures](https://github.com/y-marui/python-matplotlib-extension/issues/32)

## OLE and Presentation Interoperability

- [#33 Python-centered OLE and presentation interoperability](https://github.com/y-marui/python-matplotlib-extension/issues/33)

This phase keeps the canonical package unchanged and supports selecting an OLE object in PowerPoint, saving or exporting `figure.editable.png` on every platform, restoring the `Figure` in a separate Python console, and writing an updated graphic or object. Raw `.bin` and `.mplpkg` files remain implementation details rather than user-facing interchange formats.

PowerPoint editing UI and Python-side PPTX object discovery are out of scope. If generic Package behavior is insufficient on Windows, a minimal extraction/export-only verb or adapter may be added. On macOS, an extraction-only PowerPoint bridge uses the selected OLE Shape to resolve its internal OLE part from a locally obtained PPTX copy, unwraps the native editable PNG, and saves only that PNG. Neither component may restore a Figure, edit it, upload the presentation by default, or execute embedded code; those operations remain exclusively in Python.
