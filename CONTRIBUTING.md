## How to Contribute

For large changes (new features, design changes), please open an issue before submitting a PR.
Small bug fixes and typos can be submitted directly as a PR.

## Development Setup

See [README.md](README.md) for setup instructions.

## Code Style

- Formatter/linter: `ruff` (configured in `pyproject.toml`)
- Type checker: `mypy`
- Follow the principles in [docs/dev-charter/CODE_STYLE.md](docs/dev-charter/CODE_STYLE.md)

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format (e.g. `fix: ...`, `feat: ...`).

## Pull Request Checklist

- [ ] No secrets or credentials included
- [ ] Lint passes (`uv run ruff check .`)
- [ ] Type checks pass (`uv run mypy matplotlib_extension`)
- [ ] Tests pass (`uv run pytest`)
- [ ] Build succeeds (`uv sync && python -c "import matplotlib_extension"`)
- [ ] New features include tests
- [ ] User-facing changes are documented
