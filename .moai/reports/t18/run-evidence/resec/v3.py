import sys, time, subprocess
sys.path.insert(0, ".moai/state/verify/t18-resec")
from lib import *

def chrome_count():
    out = subprocess.run(["pgrep", "-f", "goose-shot-"], capture_output=True, text=True).stdout.split()
    return len(out)

cases = {
 "big_40mb": "<html><body>" + ("<p>x</p>" * 5_000_000) + "</body></html>",
 "deep_nest": "<html><body>" + ("<div>" * 200000) + "deep" + "</body></html>",
 "heavy_css": "<html><style>div{width:2000px;height:2000px;filter:blur(200px) drop-shadow(0 0 100px red);box-shadow:0 0 500px 500px #000;border-radius:50%;transform:rotate(3deg)} </style><body>" + ("<div></div>" * 400) + "</body></html>",
 "huge_height": "<html><body style='height:100000000px'>x</body></html>",
 "zero_height": "<html><body style='margin:0;height:0'></body></html>",
 "offscreen_hide": "<html><body><div style='position:absolute;left:-99999px'>HIDDEN</div></body></html>",
}
for k, v in cases.items():
    t = time.time()
    run(k, v)
    print("   elapsed %.1fs, leftover browser procs: %d" % (time.time() - t, chrome_count()), flush=True)
print("ALLHITS", hits)
