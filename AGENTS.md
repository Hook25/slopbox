# Slopbox

## Project

Python project managed with `uv`. See `pyproject.toml` for dependencies and
tool configuration.

## Linting & Formatting

This project uses **ruff** for linting/formatting and **ty** for type
checking. Line length is 79 characters.

```bash
# Format check (does not modify files)
uvx ruff format --check .

# Lint check
uvx ruff check .

# Auto-fix lint issues
uvx ruff check --fix .

# Auto-format
uvx ruff format .

# Type check
uvx ty check .
```

**Before marking any task as done, all linting and type checking must pass.**
Run `uvx ruff format --check . && uvx ruff check . && uvx ty check .` and fix
any issues before finishing.

## Testing

- Use **pytest** for all unit and integration tests.
- Write tests that verify **functionality and correctness**, not to inflate
  coverage numbers. Every test should have a clear reason to exist.
- Run tests with: `uv run pytest`

## Dependencies

- Do **not** add new dependencies unless explicitly instructed. Prefer the
  standard library and existing dependencies.

## CI

- When adding new functionality that would benefit from automated checks
  (e.g. tests), **propose adding or updating CI** to cover it.
