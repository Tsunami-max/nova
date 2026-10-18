#!/usr/bin/env python3
"""Tiny QMP client used to drive the NovaOS test VM.

  vmctl.py SOCK shot FILE.png          take a screenshot
  vmctl.py SOCK keys "ctrl-alt-t"      press a key combo (QEMU key names, '-' separated)
  vmctl.py SOCK type "some text"       type text (US layout)
  vmctl.py SOCK click X Y [right]      click at absolute pixel position
  vmctl.py SOCK quit
"""
import json
import socket
import subprocess
import sys
import time

SPECIAL = {" ": "spc", "\n": "ret", "-": "minus", "=": "equal", ".": "dot", ",": "comma",
           "/": "slash", ";": "semicolon", "'": "apostrophe", "[": "bracket_left",
           "]": "bracket_right", "\\": "backslash", "`": "grave_accent", "\t": "tab"}
SHIFTED = {"_": "minus", "+": "equal", ">": "dot", "<": "comma", "?": "slash", ":": "semicolon",
           '"': "apostrophe", "{": "bracket_left", "}": "bracket_right", "|": "backslash",
           "~": "grave_accent", "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
           "&": "7", "*": "8", "(": "9", ")": "0"}


class QMP:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX)
        self.s.connect(path)
        self.f = self.s.makefile("rw")
        self.f.readline()
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        self.f.write(json.dumps({"execute": name, "arguments": args}) + "\n")
        self.f.flush()
        while True:
            r = json.loads(self.f.readline())
            if "return" in r or "error" in r:
                return r

    def keys(self, combo):
        ks = [{"type": "qcode", "data": k} for k in combo.split("-")] if combo != "minus" else \
            [{"type": "qcode", "data": "minus"}]
        return self.cmd("send-key", keys=ks, **{"hold-time": 80})

    def type(self, text):
        for ch in text:
            if ch.isalpha() and ch.isupper():
                self.keys("shift-" + ch.lower())
            elif ch.isalnum():
                self.keys(ch)
            elif ch in SPECIAL:
                self.cmd("send-key", keys=[{"type": "qcode", "data": SPECIAL[ch]}])
            elif ch in SHIFTED:
                self.cmd("send-key", keys=[{"type": "qcode", "data": "shift"},
                                           {"type": "qcode", "data": SHIFTED[ch]}])
            time.sleep(0.04)

    def click(self, x, y, w, h, button="left"):
        ax, ay = int(x * 32767 / w), int(y * 32767 / h)
        ev = [{"type": "abs", "data": {"axis": "x", "value": ax}},
              {"type": "abs", "data": {"axis": "y", "value": ay}}]
        self.cmd("input-send-event", events=ev)
        time.sleep(0.2)
        for down in (True, False):
            self.cmd("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": button}}])
            time.sleep(0.1)


def main():
    q = QMP(sys.argv[1])
    op = sys.argv[2]
    if op == "shot":
        ppm = sys.argv[3] + ".ppm"
        q.cmd("screendump", filename=ppm)
        time.sleep(0.5)
        subprocess.run(["convert", ppm, sys.argv[3]], check=True)
    elif op == "keys":
        q.keys(sys.argv[3])
    elif op == "type":
        q.type(sys.argv[3])
    elif op == "click":
        # screen size taken from a fresh screendump
        q.cmd("screendump", filename="/tmp/_size.ppm")
        time.sleep(0.4)
        with open("/tmp/_size.ppm", "rb") as f:
            f.readline()
            w, h = map(int, f.readline().split())
        q.click(int(sys.argv[3]), int(sys.argv[4]), w, h, sys.argv[5] if len(sys.argv) > 5 else "left")
    elif op == "quit":
        q.cmd("quit")
    else:
        print(q.cmd(op))


if __name__ == "__main__":
    main()
