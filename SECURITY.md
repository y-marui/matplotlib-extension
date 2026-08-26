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

All untrusted discriminators are handled with positive, exact allowlists rather than denylists or fallback discovery. Unknown container bindings, schema tags, enum values, object kinds, classes, dtypes, locators, formatters, and presentation relationship types are rejected. Unsupported live Matplotlib objects may be skipped with a warning during saving, but a file never expands the restore allowlist. Adding a supported type requires an explicit implementation and, where interpretation changes, a schema version change.

The exact format and limits are documented in [docs/EDITABLE_FORMAT.md](docs/EDITABLE_FORMAT.md).

## Unsupported Objects

Saving an unsupported exact class, transform, locator, or formatter emits `UnsupportedFigureWarning` and records a warning in the manifest. The object is skipped. A class name in a file is never used to import or construct that class.

This means restore is intentionally lossy outside the documented allowlist. Preserving the security boundary takes precedence over reproducing arbitrary extension objects.

## OLE Boundary

The `.ole` writer creates a generic CFB Package with one `\x01Ole10Native` stream. Loading accepts only that expected stream shape and then validates the same canonical package used by PDF, PNG, and SVG.

The generic container is passive data storage and cannot itself provide an editing UI in PowerPoint. The represented Figure is edited only after exporting the OLE object to a file, passing that file to a separate Python process, and restoring a new `Figure` through the same validated, allowlisted path as the other bindings.

A future Windows extraction/export verb or adapter may copy the selected object's native editable PNG to a user-selected destination. That component must not deserialize Python objects, construct a Figure, invoke a file-selected program, or provide in-place editing. It is an extraction boundary only.

A macOS extraction bridge may request the selected PowerPoint Shape and a temporary OOXML copy of the current presentation solely to resolve that Shape's OLE relationship and unwrap its native editable PNG. Parsing and extraction must happen locally by default. The bridge must not upload the presentation, enumerate unrelated embedded payload contents, deserialize the canonical package, or construct a Figure. It writes only `figure.mpl.png` for subsequent validation by Python.

Presentation bridges are also allowlist-first. They accept only an explicitly supported selected OLE Shape, OOXML relationship and content type, normalized package-local embedded-object target, the expected CFB Package layout with exactly one `\x01Ole10Native` stream, the native filename `figure.mpl.png`, and a validated editable PNG. Missing, unknown, additional, or ambiguous structure is rejected rather than guessed or generically exported.

## Legacy Files

Older `.plt.pdf` files can contain a live Python object stream. This project does not load that stream, even as a compatibility fallback. Opening such a file with `loadfig()` fails safely.

Any future legacy converter is a separately distributed, deprecated migration tool, not a loader or a dependency of the main package. The main package and `loadfig()` do not import dill, pickle, or cloudpickle. Recognized legacy input is rejected before object deserialization and may only direct the user to migration documentation.

The migration process may deserialize only after displaying an arbitrary-code-execution warning immediately before its first deserialization and receiving one exact confirmation phrase. That confirmation applies once to the declared inputs in that process. Non-interactive execution is denied by default; automation requires a deliberately explicit flag such as `--allow-arbitrary-code-execution`, not a generic `--yes`.

Confirmation and process separation provide informed consent, not safety. Conversion must be limited to trusted files and should run in a disposable environment with networking disabled, inputs mounted read-only, and write access limited to a dedicated output directory. The converter writes an allowlisted canonical `.mpl.png`; a separate normal process then validates it through `loadfig()`. The converter must not become a supported legacy editing path or weaken the canonical reader. Implementation is tracked in [issue #35](https://github.com/y-marui/python-matplotlib-extension/issues/35).

## Reporting a Vulnerability

Do not attach a malicious proof-of-concept to a public issue. Contact the repository owner privately first and include the affected format version, impact, and a minimal reproduction. Public tracking can be added after a coordinated fix is available.
