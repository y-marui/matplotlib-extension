# Roadmap

GitHub [issue #28](https://github.com/y-marui/python-matplotlib-extension/issues/28) is the canonical roadmap. Sub-issues are outcome-sized; implementation checklists remain in pull requests and do not become one issue per task.

## Version 1 Foundation

- [#30 Canonical safe package and core round-trip](https://github.com/y-marui/python-matplotlib-extension/issues/30)
- [#29 Editable PDF, PNG, and SVG bindings](https://github.com/y-marui/python-matplotlib-extension/issues/29)

This release also writes and reads the canonical payload as a generic CFB/OLE Package. It is a passive data carrier: a separate Python process or console extracts it with `loadfig()` and performs all editing through Matplotlib.

## Coverage and Hardening

- [#31 Expanded artist allowlist and numeric data recovery](https://github.com/y-marui/python-matplotlib-extension/issues/31)
- [#32 Parser fuzzing and compatibility fixtures](https://github.com/y-marui/python-matplotlib-extension/issues/32)

## OLE and Presentation Interoperability

- [#33 Python-centered OLE and presentation interoperability](https://github.com/y-marui/python-matplotlib-extension/issues/33)

This phase keeps the canonical package unchanged and improves workflows for placing editable graphics or OLE objects in presentation files, extracting their payload, restoring the `Figure` in a separate Python console, and writing an updated graphic or object.

PowerPoint editing UI, Office add-ins, COM/OLE editing verbs, and an application-specific OLE server are out of scope. Python-side PPTX scanning may be added as convenience tooling, but it is not the editing runtime and is not required by the canonical format.
