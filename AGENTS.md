# Repository Guidelines

## Project Structure & Module Organization

- `cookBook` is the SQLite database containing recipes, ingredients, stock, planning, and menu history. `cookingBook.odb` provides the LibreOffice interface.
- `scripts/` contains Python modules for menu selection, transactional updates, shopping exports, and HTML generation. `principal.py` is the command-line entry point; `commun.py` provides shared configuration and database access.
- `sql/vues.sql` defines database views. `regles.toml` controls menu selection.
- `templates/index.html` is the page template; `docs/` contains generated site files; `menus/historique.json` is exported history.
- `tests/` contains unittest cases and `fixtures.sql`. `documentation/` contains usage and deployment guides; `.github/workflows/` runs checks and publication.

## Build, Test, and Development Commands

Use Python 3.11+ from the repository root; dependencies are standard-library only.

- `python3 -m unittest discover -s tests -v`: run the test suite using temporary databases.
- `python3 scripts/generer_menu.py`: preview a random menu without modifying the database.
- `python3 scripts/principal.py generer`: generate or apply the week's menu and refresh exports; modifies the database and creates a backup.
- `python3 scripts/principal.py publier`: refresh exports for the current menu without redrawing dinners; can also update database schema and views.

Use `--base` with a database copy for development that should preserve personal data.

## Coding Style & Naming Conventions

Use four-space indentation, snake_case functions and variables, and French domain terminology consistent with existing modules. Keep imports explicit and SQL parameterized. Preserve transactional updates and foreign-key enforcement. No formatter or linter is configured.

## Testing Guidelines

Use standard-library `unittest`, `test_*.py` files, and `test_*` methods. Add regression tests for behavioral changes using isolated fixtures. Cover menu constraints, breakfast exclusion, next-day lunches, and shopping calculations when relevant. No numerical coverage threshold is configured; CI runs the full suite.

## Commit & Pull Request Guidelines

Use short French action phrases, following existing commits such as “Adapter le menu de la semaine”; follow that convention. Work is maintained on `main`. For pull requests, explain the resulting behavior, affected data or exports, and validation performed; link relevant issues and include screenshots for visible page changes.

## Database & Recipe Changes

Close LibreOffice before database edits. Back up SQLite, use transactions, and verify integrity and foreign keys. Never overwrite existing personal changes or attempt to merge binary databases. Keep breakfasts categorized as `Petit-Dej`; only `Dejeuner/Diner` recipes enter the weekly draw. New main dishes should be economical, use the available saucepan and small frying pan, and specify two reference portions plus preparation and storage instructions.
