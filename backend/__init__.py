import os
import sys

# Add the framework directory to sys.path to allow importing designlab_core directly
framework_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../framework"))
if framework_path not in sys.path:
    sys.path.insert(0, framework_path)
