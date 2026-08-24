# Security Policy

## Editable File Trust Boundary

Treat every editable figure as untrusted input. Loading a file validates and parses data; it must not execute behavior selected by that file.

The implementation has these non-negotiable rules:

- no live Python object serialization or deserialization;
- no source evaluation, dynamic execution, or file-selected import;
- no file-selected class lookup or arbitrary class construction;
- no automatic restore path for the legacy object-bearing format;
- NumPy loads always use `allow_pickle=False`, and object or structured dtypes are rejected;
- Matplotlib objects are restored only through explicit built-in allowlists;
- container and package paths, counts, sizes, versions, duplicate entries, checksums, and dtypes are validated before restore;
- TeX execution is disabled on restored text objects.

The exact format and limits are documented in [docs/EDITABLE_FORMAT.md](docs/EDITABLE_FORMAT.md).

## Unsupported Objects

Saving an unsupported exact class, transform, locator, or formatter emits `UnsupportedFigureWarning` and records a warning in the manifest. The object is skipped. A class name in a file is never used to import or construct that class.

This means restore is intentionally lossy outside the documented allowlist. Preserving the security boundary takes precedence over reproducing arbitrary extension objects.

## OLE Boundary

The `.ole` writer creates a generic CFB Package with one `\x01Ole10Native` stream. Loading accepts only that expected stream shape and then validates the same canonical package used by PDF, PNG, and SVG.

The generic container is passive data storage and cannot itself provide an editing UI in PowerPoint. The represented Figure is edited only after exporting the OLE object to a file, passing that file to a separate Python process, and restoring a new `Figure` through the same validated, allowlisted path as the other bindings.

A future Windows extraction/export verb or adapter may copy the selected object's native editable PNG to a user-selected destination. That component must not deserialize Python objects, construct a Figure, invoke a file-selected program, or provide in-place editing. It is an extraction boundary only.

A macOS extraction bridge may request the selected PowerPoint Shape and a temporary OOXML copy of the current presentation solely to resolve that Shape's OLE relationship and unwrap its native editable PNG. Parsing and extraction must happen locally by default. The bridge must not upload the presentation, enumerate unrelated embedded payload contents, deserialize the canonical package, or construct a Figure. It writes only `figure.mpl.png` for subsequent validation by Python.

## Legacy Files

Older `.plt.pdf` files can contain a live Python object stream. This project does not load that stream, even as a compatibility fallback. Opening such a file with `loadfig()` fails safely.

Converting a trusted legacy file, if a separate migration tool is ever provided, must happen in an isolated environment and must never be part of the normal load path.

## Reporting a Vulnerability

Do not attach a malicious proof-of-concept to a public issue. Contact the repository owner privately first and include the affected format version, impact, and a minimal reproduction. Public tracking can be added after a coordinated fix is available.
