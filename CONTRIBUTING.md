# Contributing

Thanks for your interest in this repository.

## Before opening a pull request

1. **Open an issue** to discuss the angle, except for trivial fixes (typos,
   broken links, spelling). This avoids duplicated effort.
2. **Read the corresponding article series** on
   [blog-des-telecoms.com](https://blog-des-telecoms.com) to understand the
   through-line and the tone.
3. **Respect the `tdd-skill/` doctrine** in the examples — in particular:
   - No mocks on internal code.
   - Test through the public interface only.
   - One property = one file, no combined properties.

## Style

- Python code: clean `ruff`, passing `pytest`.
- TypeScript code: clean `eslint` (config in `examples/billing-react-go/frontend/`),
  passing `vitest`.
- Go code: clean `golangci-lint run`, passing `go test -race ./...`.
- Markdown documentation: one H1 title per file, H2 sections, optional
  frontmatter.

## Contributions that are appreciated

- **Stack porting**: adapt the demos to Vue, Svelte, FastAPI, Spring Boot,
  Rust + Axum, etc.
- **New PBT patterns**: invariants or metamorphic relations not covered in the
  examples.
- **Field feedback**: reports of applying the workflow in production, as a
  `case-studies/<topic>.md` file.
- **Bug fixes** in the examples (other than the **intentional** bugs flagged
  `# BUG:` in the code).

## What will not be accepted

- PRs that turn the demos into abstract frameworks — the educational value comes
  from them being short and explicit.
- Adding heavy dependencies (full frameworks) to the examples.
- Stylistic rewrites with no substantial improvement.

## License of contributions

By submitting a PR, you agree that your contribution is published under the same
MIT license as the repository.
