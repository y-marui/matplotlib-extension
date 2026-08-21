# Editable Figure Format

## Status

This document defines format version 1 and figure schema version 1. Both versions are integers and are validated independently. Readers reject unknown versions; they do not guess or fall back to object deserialization.

## Canonical Package

The canonical payload is a ZIP file with stored, uncompressed entries in this order:

1. `manifest.json`
2. `figure.json`
3. zero or more `arrays/NNNNNNNN.npy` entries in lexical order

ZIP metadata is deterministic: the timestamp is `1980-01-01T00:00:00`, entries use fixed regular-file permissions, and no extra fields or comments are written. JSON is UTF-8 with sorted keys, compact separators, no non-finite JSON numbers, and one trailing line feed.

`manifest.json` contains:

- `format`: `org.matplotlib-extension.figure-package`
- `format_version`: canonical package version
- `figure_schema_version`: figure specification version
- `files`: path, media type, byte size, and SHA-256 for every other entry
- `warnings`: stable descriptions of objects skipped while saving

`figure.json` is a data-only tree. It describes the figure, axes, allowlisted artists, text styling, scales, limits, legends, tick locators, and tick formatters. Large numeric values are references to `.npy` entries rather than inline JSON arrays.

NumPy entries have these requirements:

- Writers call `numpy.save(..., allow_pickle=False)`.
- Readers call `numpy.load(..., allow_pickle=False)`.
- Only plain boolean, signed integer, unsigned integer, floating-point, and complex dtypes are accepted.
- Object, structured, string, Unicode, datetime, and timedelta dtypes are rejected.
- Arrays are C-contiguous and canonicalized to little-endian byte order before writing.

## Restore Model

The reader constructs a new exact `matplotlib.figure.Figure`. The file cannot select a module, Python class, callable, backend, or constructor. Restore handlers are compiled into the library and map schema tags to explicit Matplotlib constructors.

Restoration and editing always occur in a Python process. "Editable" means that a plot saved in one process can be passed to another Python process or console, restored with `loadfig()`, and modified using normal Matplotlib APIs. A container is never an editing runtime and cannot request execution of code.

Schema version 1 supports:

- exact `Figure` and `Axes` classes;
- exact `Line2D` and `Text` classes;
- basic legends and figure/axes labels;
- linear, log, symlog, logit, and asinh scale names using Matplotlib's built-in scale selection;
- explicit allowlists for common built-in locators and formatters.

Subclasses and unsupported transforms are skipped while saving and recorded as `UnsupportedFigureWarning` plus manifest warnings. They are never restored by importing their class name. Schema version 1 stores numeric recovery records for exact `PathCollection` and `AxesImage` instances; `recover_data()` returns those arrays without constructing the unsupported artist. Future schemas may add more explicit recovery records.

## Container Bindings

Every binding stores the exact canonical package bytes:

- PDF: an embedded file named `matplotlib-extension.mplpkg` in a normal Matplotlib PDF.
- PNG: a private ancillary, safe-to-copy `mpFg` chunk immediately before `IEND`.
- SVG: base64 in `mplex:package` metadata under the namespace `https://github.com/y-marui/python-matplotlib-extension`.
- OLE: a generic Package CFB object with one `\x01Ole10Native` stream whose native payload is `figure.mplpkg`.
- MPLPKG: the canonical ZIP bytes without an outer container.

`loadfig()` detects the binding from file signatures and extracts the package before running the same validation and restore path.

`extract_package(source, destination)` performs the same extraction and validation but writes the exact canonical bytes to an independent `.mplpkg` file instead of constructing a `Figure`. Its default exclusive-create mode prevents an accidentally selected OLE object from overwriting an existing package.

The OLE binding is a portable, passive storage object, not an OLE application server. It does not register a COM class, expose PowerPoint verbs, provide an Office editing UI, or run embedded code. To edit it, a user or integration passes the OLE object to a Python process, which extracts the canonical package and calls the same safe restore path as every other binding.

Presentation software may display the rendered PDF, PNG, or SVG and may carry the corresponding OLE object, but presentation software is not the editor. Office add-ins, application-specific OLE servers, and in-place editing are outside this format and this project's editing model.

For Windows presentation workflows, the OLE Package native file is `figure.mplpkg`. An exported native file is therefore directly accepted by `loadfig()`. An OOXML presentation can instead expose the complete CFB object as a part such as `ppt/embeddings/oleObject1.bin`; because input detection is signature-based, that `.bin` file is also accepted directly and can be converted to a standalone `.mplpkg` with `extract_package()`.

## Resource Limits

Version 1 enforces limits before or during parsing:

- canonical package: 256 MiB;
- JSON entry: 16 MiB;
- individual NumPy entry: 128 MiB;
- array count: 10,000;
- axes count: 1,000;
- artists per supported axes list: 100,000;
- text value: 1,000,000 Unicode code points.

ZIP compression and unlisted, duplicate, absolute, parent-relative, empty, or backslash-separated paths are rejected. Each listed file must match its declared byte size and SHA-256 digest.

## Compatibility

Adding optional semantics requires a new figure schema version when an old reader could misinterpret them. Changing package layout, integrity rules, or canonical encoding requires a new package version. Readers must reject rather than partially interpret unknown versions.

Legacy files containing live Python object streams are outside this format. The library never automatically restores them.
