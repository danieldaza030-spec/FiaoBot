# AGENTS.md

This file provides context to any coding agent (Claude Code, Cursor,
Copilot Workspace, etc.) working on this repository. Read it in full
before generating, modifying, or reviewing any code.

## 1. Project context

**Project name:** fiadobot

**Problem it solves:** A small retail vendor sells products on
informal credit ("fiado") and manages customer debts by writing them
down in each customer's chat on his phone, as if it were a ledger. At
the end of each month/biweekly period, he has to manually calculate
(using a calculator and a notebook) how much each customer owes,
which takes him several hours and is prone to human error. This
project replaces that manual calculation with a conversational bot
connected to a database, which records sales and payments in natural
language, computes balances deterministically, and generates payment
summaries and analytics on demand.

**Core design principle (do not break this):** the LLM never decides
business logic or performs money calculations. Its only
responsibility is to translate natural language into a structured
function call (tool call). All calculations, validations, and
persistence happen in deterministic backend code.

## 2. Required reading

Before writing or modifying any code, the agent must read, in this
order, the following documents located in `/docs`:

| Order | File                             | Contents                                                        |
|-------|----------------------------------|------------------------------------------------------------------|
| 1     | `docs/01-requisitos.md`          | Problem description, functional (RFxx) and non-functional (RNFxx) requirements |
| 2     | `docs/02-diseno-solucion.md`     | Architecture, conversational flow, LLM provider abstraction, state handling |
| 3     | `docs/03-modelo-datos.md`        | Tables, columns, relationships, and business rules of the database |
| 4     | `docs/04-decisiones-tecnicas.md` | ADRs documenting technical decisions already made and their rationale (if the file exists) |

If any of these files do not yet exist in the repository, the agent
must flag this before assuming any undocumented design decisions.

Every requirement (RF/RNF) referenced in the code must be traceable
back to its definition in `docs/01-requisitos.md`. If the agent
implements something not covered by an existing requirement, it must
explicitly flag this before proceeding.

## 3. Code standards (mandatory, no exceptions)

### Language and version
- Python **3.11**. Do not use syntax or libraries exclusive to later
  versions.
- Use type hints on every function and method (parameters and return
  value), including `Optional`, `Union` (or `|` with `from __future__
  import annotations` if applicable), and generic types from
  `typing`.

### Style and formatting
- Follow **PEP 8** strictly (naming, line length, spacing, import
  ordering, etc.).
- Names of variables, functions, classes, and modules: always in
  **English**, following PEP 8 conventions:
  - `snake_case` for variables and functions.
  - `PascalCase` for classes.
  - `UPPER_SNAKE_CASE` for constants.
- Names must be descriptive and explicit; avoid ambiguous
  abbreviations (e.g., use `customer_id` instead of `cid`).

### Docstrings
- Every public function, method, class, and module must have a
  docstring in **English**, following the **Google Python Style
  Guide** format:

```python
def calculate_pending_balance(customer_id: int) -> float:
    """Calculate the pending balance for a given customer.

    The balance is computed as the sum of active transactions minus
    the sum of registered payments. Annulled transactions are
    excluded from the calculation.

    Args:
        customer_id: The unique identifier of the customer.

    Returns:
        The pending balance as a float, in the same currency unit
        used across the system.

    Raises:
        CustomerNotFoundError: If no customer exists with the given
            customer_id.
    """
```

- Modules must include a header docstring explaining their purpose.
- Inline comments (`#`) must also be written in English and used only
  when the code is not self-explanatory.

### Linters (mandatory to pass both before marking a task as done)
- **flake8**: zero warnings/errors. Expected configuration in
  `setup.cfg` or `.flake8` (max-line-length=88, compatible with Black
  if used).
- **pylint**: minimum accepted score of 9.0/10. Any punctual `disable`
  of a rule must be justified with an inline comment explaining why.
- If the agent generates code that fails either linter, it must fix
  it before presenting the task as complete — not leave it as a TODO.

### Additional structure and best practices
- No business logic (balance calculations, domain decisions) inside
  LLM adapters (`LLMProvider` and its implementations). That logic
  lives in the backend (services/use cases), not in the LLM or its
  integration layer.
- No direct database access from LLM providers.
- Explicit exception handling; do not use a bare `except:` without
  specifying the exception type.
- Prefer small, pure functions over long functions with multiple
  responsibilities.
- All monetary values are handled as `Decimal` or `NUMERIC` in the
  database, never `float`, to avoid rounding errors.

## 4. Language of the agent's responses

- **Code, variable names, comments, and docstrings**: always in
  English.
- **Conversational responses to the developer** (explanations, change
  summaries, clarifying questions) may remain in Spanish unless
  stated otherwise.

## 5. Before marking a task as complete

The agent must confirm that:
1. The code complies with PEP 8, flake8, and pylint (score ≥ 9.0/10).
2. All public functions/classes have a Google-style docstring, in
   English.
3. Variable and function names are in English.
4. The implementation is consistent with what is defined in
   `docs/01-requisitos.md`, `docs/02-diseno-solucion.md`, and
   `docs/03-modelo-datos.md`.
5. No business logic was introduced inside the LLM layer.