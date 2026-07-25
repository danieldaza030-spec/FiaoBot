"""Application entry point."""

from __future__ import annotations

from .config import load_config


def main() -> int:
    """Run the application bootstrap sequence."""

    config = load_config()
    print(f"{config.app_name} ready in {config.environment} mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
