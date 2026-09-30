import sys
from pathlib import Path

# The action script lives alongside this conftest and is not part of the
# installed `model_config_tests` package, so make it importable by path.
sys.path.insert(0, str(Path(__file__).parent))
