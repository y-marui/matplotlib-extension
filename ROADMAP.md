# Roadmap

GitHub [issue #28](https://github.com/y-marui/python-matplotlib-extension/issues/28) is the canonical roadmap. Sub-issues are outcome-sized; implementation checklists remain in pull requests and do not become one issue per task.

## Version 1 Foundation

- [#30 Canonical safe package and core round-trip](https://github.com/y-marui/python-matplotlib-extension/issues/30)
- [#29 Editable PDF, PNG, and SVG bindings](https://github.com/y-marui/python-matplotlib-extension/issues/29)

This release also writes and reads the canonical payload as a generic CFB/OLE Package. That storage layer does not claim to be an Office editing server.

## Coverage and Hardening

- [#31 Expanded artist allowlist and numeric data recovery](https://github.com/y-marui/python-matplotlib-extension/issues/31)
- [#32 Parser fuzzing and compatibility fixtures](https://github.com/y-marui/python-matplotlib-extension/issues/32)

## Office Integration

- [#33 Windows OLE server and PowerPoint export bridge](https://github.com/y-marui/python-matplotlib-extension/issues/33)

The Office phase keeps the canonical package unchanged, adds application-specific OLE verbs and export behavior on Windows, and does not prioritize Python-side PPTX scanning.
