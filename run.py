"""Backward-compatible local server entry point."""

from server.cli import main


if __name__ == "__main__":
    main(["serve"])
