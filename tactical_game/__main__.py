import sys

if __package__ in (None, ""):                 # started as a plain file (e.g. a Run button): make the package importable
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tactical_game.ui.app import main
else:
    from .ui.app import main

sys.exit(main())
