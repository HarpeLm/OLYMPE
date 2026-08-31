import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.bridge._handlers import Handler
from http.server import ThreadingHTTPServer



