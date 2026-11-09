"""One-click launcher: run this file (Run button, double-click, or `python launcher.py`).

It works from any folder, installs missing packages on request, passes options through to the game
(for example `python launcher.py --view front --demo`) and keeps the window open if something goes wrong.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)                      # so `tactical_game` is found whatever folder this was started from

REQUIRED = [("pygame", "pygame>=2.5")]
OPTIONAL = [("numpy", "numpy>=1.23")]         # only needed for the view change (V)


def _missing(packages):
    out = []
    for module, spec in packages:
        try:
            __import__(module)
        except ImportError:
            out.append(spec)
    return out


def _install(specs) -> bool:
    print("Installing:", ", ".join(specs))
    return subprocess.call([sys.executable, "-m", "pip", "install", *specs]) == 0


def _ask(question: str) -> bool:
    try:
        return input(question + " [Y/n] ").strip().lower() in ("", "y", "yes")
    except EOFError:
        return False


def check_packages() -> bool:
    missing = _missing(REQUIRED)
    if missing:
        print("The game needs:", ", ".join(missing))
        if not (_ask("Install it now?") and _install(missing)):
            return False
    optional = _missing(OPTIONAL)
    if optional and _ask("numpy is missing, so the view change (V) will be off. Install it now?"):
        _install(optional)
    return True


def main() -> int:
    if not check_packages():
        print("Cannot start without pygame. Run:  pip install -r requirements.txt")
        return 1
    from tactical_game.ui.app import main as run_game
    return run_game(sys.argv[1:]) or 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    if code and sys.stdin and sys.stdin.isatty():
        input("\nPress Enter to close...")
    sys.exit(code)
