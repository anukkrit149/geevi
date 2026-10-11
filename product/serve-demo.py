"""Serve only the public prototype and research artifacts on loopback."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = [ROOT / "product", ROOT / "research"]


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        resolved = Path(self.translate_path(self.path)).resolve()
        if not any(resolved.is_relative_to(directory) for directory in ALLOWED):
            self.send_error(404)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404)
        return None


if __name__ == "__main__":
    print("Demo: http://127.0.0.1:8765/product/aml-screen-walkthrough.html", flush=True)
    with ThreadingHTTPServer(("127.0.0.1", 8765), DemoHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
