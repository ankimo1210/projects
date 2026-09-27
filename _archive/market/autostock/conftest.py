import os
import sys

# prepare.py / strategy.py live at the project root (flat layout, like
# autoresearch). Put that root on sys.path so tests can import them under
# pytest's importlib mode.
sys.path.insert(0, os.path.dirname(__file__))
