# Contributing

## Scope

This project collects, verifies, and preserves entries and definitions related to Iranian opposition slang and dissent. Contributions should improve data quality, moderation safety, and archival durability.

## Open Source and Crowdsourced Contributions

- Source code contributions are open source and licensed under `MIT` (`LICENSE`).
- Website content contributions are crowdsourced and licensed under `CC BY-SA 4.0` (`docs/CONTENT_LICENSE.md`).
- By contributing, you agree your submission is distributed under the applicable license.
- If a contribution includes both code and public content, both licensing tracks apply.

## Getting Started

1. Read `README.md` for setup and local run instructions.
2. Create a feature branch for your change.
3. Implement scoped changes with tests.
4. Open a pull request with a clear description of behavior changes.

## Development Standards

- Keep apps cohesive by domain.
- Use split settings and environment variables only.
- Preserve RTL semantics in templates.
- Add tests for all business logic and background tasks.

## Pull Request Checklist

- [ ] Code is formatted and linted.
- [ ] New logic is tested with `pytest`.
- [ ] Security-sensitive changes are documented.
- [ ] Migrations are included for model changes.

## Documentation Expectations

- Update `README.md` when developer workflows change.
- Update `docs/API.md` when endpoint contracts are added or modified.
- Document moderation, verification, and notification behaviors when they change.
- Update `docs/CONTENT_LICENSE.md` when policy or rights handling changes.

## Next Steps

- Add new lexicon categories for memes and chants.
- Implement entry and definition flag/report flows for community moderation.
- Send notification email to entry creators when their entries are verified.
- Add internal admin comments on entries for moderation context and auditability.
- Expand versioned API coverage in `apps.api` for core lexicon and moderation workflows.
- Add MCP integration documentation and implementation notes for external tool interoperability.
