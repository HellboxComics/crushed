"""THE CHECK SHOTS: the finished model photographed in the very same 3D viewer your phone page uses (model-viewer,
neutral studio light), from all around plus close-ups of the ends, seams and edges - so the judge looks at exactly
what you will see, up close, the way a buyer would.

    sheets = shoot(model.glb, out_dir)   ->  (all_around.jpg, closeups.jpg)
"""
import functools
import http.server
import os
import shutil
import threading
import urllib.request

WORK = os.path.expanduser(os.environ.get("CRUSHED_REMASTER_WORK", "~/crushed-render/remaster"))
MV = "https://unpkg.com/@google/model-viewer@4.0.0/dist/model-viewer.min.js"
AROUND = ["0deg 75deg auto", "90deg 75deg auto", "180deg 75deg auto", "270deg 75deg auto"]
CLOSE = ["20deg 15deg 45%", "15deg 165deg 45%", "185deg 80deg 50%", "45deg 60deg 40%"]   # top, bottom, back seam, an edge


def _viewer():
    d = os.path.join(WORK, "viewer")
    os.makedirs(d, exist_ok=True)
    js = os.path.join(d, "mv.js")
    if not os.path.exists(js) or os.path.getsize(js) < 100000:
        urllib.request.urlretrieve(MV, js + ".part")
        os.replace(js + ".part", js)
    return d


def _page(orbits):
    cells = "".join(
        f'<model-viewer src="m.glb" camera-orbit="{o}" shadow-intensity="1" exposure="1.05" '
        f'environment-image="neutral" tone-mapping="aces" interaction-prompt="none" '
        f'style="width:600px;height:600px;background:radial-gradient(circle at 50% 45%,#2b2d32 0%,#1b1c20 72%)">'
        f'</model-viewer>' for o in orbits)
    return (f'<!doctype html><body style="margin:0;display:flex;background:#1b1c20">'
            f'<script type=module src="mv.js"></script>{cells}</body>')


def shoot(glb, out_dir, port=0):
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    root = _viewer()
    shutil.copy(glb, os.path.join(root, "m.glb"))
    for name, orbits in (("around", AROUND), ("close", CLOSE)):
        open(os.path.join(root, name + ".html"), "w").write(_page(orbits))
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    H = functools.partial(Quiet, directory=root)
    # a free port the system picks (port 0), never a fixed one: a viewer left running by a stopped build held 8791
    # and the judge got Blender's small studio pictures instead (2026-10-10 05:40: "text smeared", "body gray")
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    outs = []
    try:
        with sync_playwright() as p:
            import sys
            b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
                                  if sys.platform.startswith("linux") else [])
            pg = b.new_page(viewport={"width": 2400, "height": 600})
            for name in ("around", "close"):
                pg.goto(f"http://127.0.0.1:{port}/{name}.html")
                pg.wait_for_function("[...document.querySelectorAll('model-viewer')].every(m => m.loaded)",
                                     timeout=180000)
                pg.wait_for_timeout(3000)
                o = os.path.join(out_dir, f"viewer_{name}.jpg")
                pg.screenshot(path=o, type="jpeg", quality=90)
                outs.append(o)
            b.close()
    finally:
        srv.shutdown()
    return tuple(outs)


if __name__ == "__main__":
    import sys
    print(shoot(sys.argv[1], sys.argv[2]))
