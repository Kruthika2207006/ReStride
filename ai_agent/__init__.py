# Make ai_agent package importable and ensure submodules can resolve direct imports
import os
import sys

ai_agent_dir = os.path.dirname(os.path.abspath(__file__))
if ai_agent_dir not in sys.path:
    sys.path.insert(0, ai_agent_dir)

