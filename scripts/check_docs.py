"""Verify README translations against the English source and runtime facts."""

from pathlib import Path

from clinic_agent_lab.doccheck import check_docs


def main():
    errors = check_docs(Path(__file__).resolve().parents[1])
    if errors:
        print("\n".join(errors))
        return 1
    print("Documentation consistency passed: 6 READMEs; "
          "states, counts, commands, boundaries, links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
