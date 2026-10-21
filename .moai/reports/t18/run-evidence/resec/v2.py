import sys, os, base64, shutil
sys.path.insert(0, ".moai/state/verify/t18-resec")
from lib import *

B = BASE
S = SECRET.as_uri()
inner = f'<h2>INNER</h2><iframe src="{S}" width=600 height=80></iframe><img src="{B}/innerimg"><embed src="file:///etc/hosts" width=600 height=100>'
b64 = base64.b64encode(inner.encode()).decode()
css = f'@import url("{S}"); body{{background:url({B}/cssdata)}}'
nested = {
 "data_iframe_nested": f'<iframe src="data:text/html;base64,{b64}" width=800 height=400></iframe><object data="data:text/html;base64,{b64}" width=800 height=300></object>',
 "data_css_import": f'<link rel=stylesheet href="data:text/css,{css}">x',
 "svg_data_image": f'<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 xmlns:xlink=%27http://www.w3.org/1999/xlink%27 width=200 height=100%3E%3Cimage href=%27{B}/svgdata%27 width=100 height=100/%3E%3Cimage href=%27{S}%27/%3E%3C/svg%3E">',
}
for relaxed in (False, True):
    for k, v in nested.items():
        run(k, "<html><body>" + v + "</body></html>", relaxed=relaxed)


# filesystem-level tricks
def hardlink(root):
    os.link("/etc/hosts", root / "draft" / "report.html")

def symlink(root):
    os.symlink("/etc/hosts", root / "draft" / "report.html")

def dirlink(root):
    (root / "real").mkdir()
    (root / "real" / "report.html").write_text("<html><body>real</body></html>")
    shutil.rmtree(root / "draft")
    os.symlink("/private/tmp", root / "draft")

def hardlink_secret(root):
    os.link(SECRET, root / "draft" / "report.html")

for name, fn in (("hardlink_etc_hosts", hardlink), ("symlink", symlink), ("dirlink", dirlink), ("hardlink_secret", hardlink_secret)):
    try:
        run(name, "", extra=fn)
    except Exception as e:
        print(name, "SETUP/RUN EXC", repr(e))
print("ALLHITS", hits)
