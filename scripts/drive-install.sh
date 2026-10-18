#!/usr/bin/env bash
# Drives the Calamares installer in the test VM through to the summary page.
set -u
Q="${Q:-/tmp/novaos-inst/qmp.sock}"
OUT="${OUT:-/tmp/claude-0/inst}"
mkdir -p "$OUT"
V="python3 $(dirname "$0")/vmctl.py $Q"
W() { timeout "$1" tail -f /dev/null; }
$V click 74 330; W 2; $V keys ret; W 75; $V shot "$OUT/01-welcome.png"
$V click 1008 753; W 20      # -> location
$V click 1008 753; W 20      # -> keyboard
$V click 1008 753; W 25      # -> partitions
$V click 334 208; W 20; $V shot "$OUT/04-partitions.png"
$V click 1008 753; W 20      # -> users
slow() { for c in $(echo "$1" | sed 's/./& /g'); do $V keys "$c"; W 0.4; done; }
$V click 427 182; W 2; slow tester; W 4
$V click 427 302; W 2; $V keys ctrl-a; W 1; slow novatest; W 3
for xy in "427 362" "633 362"; do $V click $xy; W 2; slow nova1234; W 3; done
W 4; $V shot "$OUT/05-users.png"
$V click 1008 753; W 20; $V shot "$OUT/06-summary.png"
