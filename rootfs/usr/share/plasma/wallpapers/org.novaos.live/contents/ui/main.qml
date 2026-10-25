/*
 * NovaOS Live wallpaper.
 *
 * Kept light on the processor on purpose:
 *  - no QML animations: one Timer redraws at a capped frame rate (default 15 fps);
 *  - the effects are drawn at a fraction of the screen resolution (default 30 %)
 *    and smoothly scaled up, so even software rendering stays cheap;
 *  - everything pauses while a maximized or full-screen window covers the desktop.
 *
 * SPDX-License-Identifier: MIT
 */
import QtQuick 2.15
import org.kde.plasma.core 2.0 as PlasmaCore
import org.kde.taskmanager 0.1 as TaskManager

Rectangle {
    id: root
    color: "#07090f"

    readonly property var cfg: wallpaper.configuration
    readonly property string mode: cfg.Mode || "aurora"
    readonly property string effect: cfg.Effect || "none"
    readonly property real quality: Math.max(0.15, Math.min(1.0, cfg.Quality || 0.3))
    readonly property int fps: Math.max(5, Math.min(30, cfg.Fps || 15))
    // Processor budget (percent of the whole processor, like Task Manager shows).
    readonly property real budget: Math.max(5, Math.min(20, cfg.MaxCpu || 15))
    // Frame rate actually used: lowered automatically when drawing costs more than the budget
    // (for example without graphics acceleration on a big screen).
    property int effFps: fps
    onFpsChanged: effFps = fps
    readonly property real speed: cfg.Speed || 1.0
    property real t: 0
    property bool covered: false
    readonly property bool running: visible && !(covered && cfg.PauseWhenCovered)

    readonly property var palettes: ({
        "nova":   ["#6d7bff", "#b44dff", "#5ee7ff"],
        "aurora": ["#2cff9a", "#3fb8ff", "#b44dff"],
        "ocean":  ["#1e90ff", "#00c2c7", "#0b3d91"],
        "sunset": ["#ff7a59", "#ff3d81", "#ffc145"],
        "forest": ["#3ddc84", "#0f9d58", "#c6ff00"],
        "mono":   ["#c8ccdc", "#7d849c", "#ffffff"]
    })
    readonly property var pal: palettes[cfg.Palette] || palettes["nova"]

    Timer {
        interval: Math.round(1000 / root.effFps)
        repeat: true
        running: root.running
        onTriggered: root.t = (root.t + interval / 1000 * root.speed) % 3600
    }

    // --- processor governor ---------------------------------------------------------------
    property int cores: 1
    property real lastTicks: -1
    property real lastMs: 0
    function readFile(url, done) {
        var x = new XMLHttpRequest();
        x.onreadystatechange = function () {
            if (x.readyState === XMLHttpRequest.DONE) done(x.responseText || "");
        };
        x.open("GET", url);
        x.send();
    }
    Component.onCompleted: {
        readFile("file:///proc/stat", function (txt) {
            var n = (txt.match(/^cpu[0-9]+ /mg) || []).length;
            root.cores = Math.max(1, n);
        });
    }
    Timer {
        interval: 3000
        repeat: true
        running: root.running
        onRunningChanged: root.lastTicks = -1
        onTriggered: root.readFile("file:///proc/self/stat", function (txt) {
            var i = txt.lastIndexOf(")");
            if (i < 0) return;
            var f = txt.substring(i + 2).split(" ");
            var ticks = parseInt(f[11]) + parseInt(f[12]);  // utime + stime
            var now = Date.now();
            if (root.lastTicks >= 0 && now > root.lastMs) {
                var used = (ticks - root.lastTicks) / 100 / ((now - root.lastMs) / 1000) / root.cores * 100;
                if (used > root.budget)
                    root.effFps = Math.max(2, Math.min(root.fps, Math.floor(root.effFps * root.budget / used * 0.9)));
                else if (used < root.budget * 0.6 && root.effFps < root.fps)
                    root.effFps = Math.min(root.fps, root.effFps + 1);
            }
            root.lastTicks = ticks;
            root.lastMs = now;
        })
    }

    // --- pause while a window covers the desktop ---------------------------------
    TaskManager.VirtualDesktopInfo { id: vdInfo }
    TaskManager.ActivityInfo { id: actInfo }
    TaskManager.TasksModel {
        id: tasks
        groupMode: TaskManager.TasksModel.GroupDisabled
        filterByVirtualDesktop: true
        filterByActivity: true
        virtualDesktop: vdInfo.currentDesktop
        activity: actInfo.currentActivity
    }
    Timer {
        interval: 1500
        repeat: true
        running: true
        onTriggered: {
            var c = false;
            for (var i = 0; i < tasks.count; i++) {
                var idx = tasks.makeModelIndex(i);
                if (tasks.data(idx, TaskManager.AbstractTasksModel.IsMinimized))
                    continue;
                if (tasks.data(idx, TaskManager.AbstractTasksModel.IsMaximized) ||
                    tasks.data(idx, TaskManager.AbstractTasksModel.IsFullScreen)) {
                    c = true;
                    break;
                }
            }
            root.covered = c;
        }
    }

    // --- picture mode ------------------------------------------------------------------
    Image {
        id: picture
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        visible: root.mode === "picture"
        asynchronous: true
        cache: false
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(root.width, root.height)
        source: visible ? (root.cfg.Image ? root.cfg.Image
                           : "file:///usr/share/novaos/live-default.jpg") : ""
        // Very slow zoom in and out (one cycle per two minutes).
        scale: root.cfg.SlowZoom ? 1.0 + 0.06 * (0.5 - 0.5 * Math.cos(root.t * Math.PI / 60)) : 1.0
        smooth: true
    }

    // --- shared GLSL ---------------------------------------------------------------------------
    readonly property string glslHead: "
        varying highp vec2 qt_TexCoord0;
        uniform lowp float qt_Opacity;
        uniform highp float time;
        uniform highp vec2 res;
        uniform lowp vec4 c1;
        uniform lowp vec4 c2;
        uniform lowp vec4 c3;
        highp float hash(highp vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        highp float noise(highp vec2 p) { highp vec2 i = floor(p); highp vec2 f = fract(p); highp vec2 u = f * f * (3.0 - 2.0 * f);
            return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y); }
        highp float fbm(highp vec2 p) { highp float v = 0.0; highp float a = 0.5;
            for (int i = 0; i < 4; i++) { v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return v; }
        highp float stars(highp vec2 p, highp float density) { highp vec2 g = floor(p * density); highp float h = hash(g);
            highp vec2 f = fract(p * density) - 0.5 - (vec2(hash(g + 3.1), hash(g + 7.7)) - 0.5) * 0.6;
            highp float tw = 0.55 + 0.45 * sin(time * (1.0 + 2.0 * h) + h * 40.0);
            return step(0.985, h) * tw * smoothstep(0.18, 0.0, length(f)); }
        highp float shooting(highp vec2 uv, highp float aspect) { highp float period = 9.0; highp float k = floor(time / period);
            highp float ph = fract(time / period) * period; if (ph > 1.2) return 0.0;
            highp vec2 q = vec2(uv.x * aspect, uv.y);
            highp vec2 a = vec2(aspect * (0.1 + 0.6 * hash(vec2(k, 1.0))), 0.05 + 0.3 * hash(vec2(k, 2.0)));
            highp vec2 dir = normalize(vec2(0.9, 0.4)); highp vec2 d = a + dir * ph * 0.6 - q;
            highp float along = dot(d, dir); highp float across = length(d - dir * along);
            return smoothstep(0.004, 0.0, across) * step(0.0, along) * smoothstep(0.2, 0.0, along) * (1.0 - ph / 1.2); }
    "

    readonly property var scenes: ({
        "aurora": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp vec3 col = mix(vec3(0.01, 0.02, 0.06), vec3(0.04, 0.03, 0.10), uv.y);
                col += stars(p, 70.0) * 0.9 * (1.1 - uv.y);
                for (int i = 0; i < 3; i++) {
                    highp float fi = float(i);
                    highp float y = 0.30 + 0.11 * fi + 0.07 * sin(p.x * 1.2 + time * 0.12 * (1.0 + 0.3 * fi) + fi * 2.1)
                                    + 0.10 * (fbm(vec2(p.x * 1.4 + time * 0.04, fi * 3.0)) - 0.5);
                    highp float d = uv.y - y;
                    highp float inten = d < 0.0 ? exp(d * 7.0) : exp(-d * 45.0);
                    inten *= 0.35 + 0.9 * fbm(vec2(p.x * 7.0 + time * 0.25, fi * 5.0 + time * 0.05));
                    highp vec3 c = i == 0 ? c1.rgb : (i == 1 ? c2.rgb : c3.rgb);
                    col += c * inten * 0.55;
                }
                col += c1.rgb * 0.08 * (1.0 - uv.y);
                gl_FragColor = vec4(col, 1.0) * qt_Opacity;
            }",
        "nebula": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp float n = fbm(p * 2.2 + vec2(time * 0.015, time * 0.008));
                highp float n2 = fbm(p * 3.1 - vec2(time * 0.01, 0.0) + n * 1.5);
                highp vec3 col = vec3(0.01, 0.01, 0.04);
                col += c1.rgb * pow(n, 2.6) * 1.3 + c2.rgb * pow(n2, 3.2) * 1.5 + c3.rgb * pow(n * n2, 3.0) * 1.2;
                col += vec3(stars(p, 90.0) + 0.6 * stars(p + 17.0, 45.0));
                col += vec3(0.9, 0.95, 1.0) * shooting(uv, aspect);
                gl_FragColor = vec4(col, 1.0) * qt_Opacity;
            }",
        "waves": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp vec3 col = mix(c2.rgb * 0.25, vec3(0.02, 0.03, 0.08), uv.y);
                for (int i = 0; i < 5; i++) {
                    highp float fi = float(i);
                    highp float y = 0.45 + 0.1 * fi + 0.035 * sin(p.x * (1.6 + 0.4 * fi) + time * (0.35 + 0.08 * fi) + fi * 1.7)
                                    + 0.015 * sin(p.x * 4.5 - time * 0.6 + fi);
                    highp vec3 c = mix(c1.rgb, c3.rgb, fi / 4.0) * (0.95 - 0.13 * fi);
                    highp float edge = smoothstep(y - 0.004, y + 0.004, uv.y);
                    col = mix(col, c, edge * 0.9);
                    col += c * 0.25 * exp(-abs(uv.y - y) * 60.0);
                }
                gl_FragColor = vec4(col, 1.0) * qt_Opacity;
            }",
        "lava": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp float f = 0.0;
                for (int i = 0; i < 7; i++) {
                    highp float fi = float(i);
                    highp vec2 c = vec2(aspect * (0.5 + 0.38 * sin(time * (0.07 + 0.013 * fi) + fi * 1.9)),
                                        0.5 + 0.42 * sin(time * (0.05 + 0.011 * fi) + fi * 2.7));
                    highp float r = 0.09 + 0.035 * sin(fi * 3.3);
                    highp vec2 d = p - c; f += r * r / dot(d, d);
                }
                highp vec3 bg = mix(vec3(0.03, 0.02, 0.07), c2.rgb * 0.18, uv.y);
                highp vec3 blob = mix(c1.rgb, c3.rgb, clamp(uv.y * 1.2 - 0.1, 0.0, 1.0));
                highp vec3 col = mix(bg, blob, smoothstep(0.95, 1.08, f));
                col += blob * 0.18 * clamp(f, 0.0, 1.0);
                gl_FragColor = vec4(col, 1.0) * qt_Opacity;
            }",
        "flow": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp float n = fbm(p * 1.3 + vec2(time * 0.03, -time * 0.02));
                highp float a = 0.5 + 0.5 * sin(p.x * 1.4 + p.y * 0.8 + time * 0.12 + n * 3.0);
                highp float b = 0.5 + 0.5 * sin(p.y * 1.7 - time * 0.09 + n * 2.0);
                highp vec3 col = mix(mix(c1.rgb, c2.rgb, a), c3.rgb, b * 0.45) * (0.55 + 0.35 * n);
                col *= 0.85 + 0.15 * (1.0 - uv.y);
                gl_FragColor = vec4(col, 1.0) * qt_Opacity;
            }"
    })

    readonly property var effects: ({
        "snow": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp float a = 0.0;
                for (int i = 0; i < 3; i++) {
                    highp float fi = float(i); highp float sc = 7.0 + 6.0 * fi;
                    highp vec2 q = p * sc + vec2(sin(time * 0.4 + fi * 2.0 + p.y * 3.0) * 0.6, -time * (0.9 + 0.4 * fi));
                    highp vec2 g = floor(q); highp float h = hash(g + fi * 13.0);
                    highp vec2 f = fract(q) - 0.5 - (vec2(h, fract(h * 17.0)) - 0.5) * 0.6;
                    a += step(0.45, h) * smoothstep(0.11 - 0.025 * fi, 0.0, length(f)) * (0.95 - 0.25 * fi);
                }
                a = clamp(a, 0.0, 1.0);
                gl_FragColor = vec4(vec3(a), a) * qt_Opacity;
            }",
        "rain": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                p.x += p.y * 0.12;
                highp float a = 0.0;
                for (int i = 0; i < 2; i++) {
                    highp float fi = float(i);
                    highp vec2 q = vec2(p.x * (70.0 + 40.0 * fi), p.y * 3.0 - time * (3.0 + fi));
                    highp float h = hash(vec2(floor(q.x), fi));
                    highp float y = fract(q.y + h * 7.0);
                    highp float fx = fract(q.x) - 0.5;
                    a += step(0.55, h) * smoothstep(0.0, 0.05, y) * smoothstep(0.35, 0.05, y) * exp(-fx * fx * 60.0) * (0.55 - 0.2 * fi);
                }
                highp vec3 c = vec3(0.75, 0.85, 1.0);
                highp float dim = 0.18;
                highp float al = clamp(a + dim, 0.0, 1.0);
                gl_FragColor = vec4(c * a, al) * qt_Opacity;
            }",
        "fireflies": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp float a = 0.0;
                for (int i = 0; i < 14; i++) {
                    highp float fi = float(i); highp float h = hash(vec2(fi, 3.0));
                    highp vec2 c = vec2(aspect * fract(h * 7.3 + 0.03 * time * (0.5 + h) + 0.08 * sin(time * 0.3 + fi)),
                                        0.35 + 0.6 * fract(h * 3.7 + 0.04 * sin(time * (0.2 + 0.1 * h) + fi * 1.3)));
                    highp vec2 d = p - c;
                    highp float pulse = 0.5 + 0.5 * sin(time * (1.2 + h) + fi * 2.0);
                    a += exp(-dot(d, d) * 2200.0) * pulse + exp(-dot(d, d) * 260.0) * 0.25 * pulse;
                }
                a = clamp(a, 0.0, 1.0);
                highp vec3 c = mix(vec3(1.0, 0.85, 0.35), vec3(0.75, 1.0, 0.45), 0.4);
                gl_FragColor = vec4(c * a, a) * qt_Opacity;
            }",
        "stars": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y; highp vec2 p = vec2(uv.x * aspect, uv.y);
                highp float a = (stars(p, 80.0) + 0.7 * stars(p + 11.0, 40.0)) * smoothstep(1.0, 0.2, uv.y);
                a += shooting(uv, aspect);
                a = clamp(a, 0.0, 1.0);
                gl_FragColor = vec4(vec3(a), a) * qt_Opacity;
            }",
        "rays": "
            void main() {
                highp vec2 uv = qt_TexCoord0; highp float aspect = res.x / res.y;
                highp vec2 d = vec2((uv.x + 0.15) * aspect, uv.y + 0.25);
                highp float ang = atan(d.y, d.x);
                highp float r = noise(vec2(ang * 18.0, time * 0.15)) * 0.6 + noise(vec2(ang * 41.0, time * 0.25 + 4.0)) * 0.4;
                highp float a = pow(r, 2.2) * 0.55 * smoothstep(1.6, 0.2, length(d));
                gl_FragColor = vec4(vec3(1.0, 0.93, 0.78) * a, a) * qt_Opacity;
            }"
    })

    // --- animated scene (low-resolution layer, scaled up) ------------------------------------------
    Item {
        anchors.fill: parent
        visible: root.mode !== "picture"
        layer.enabled: visible
        layer.smooth: true
        layer.textureSize: Qt.size(Math.max(64, Math.round(root.width * root.quality)),
                                   Math.max(36, Math.round(root.height * root.quality)))
        ShaderEffect {
            anchors.fill: parent
            property real time: root.t
            property size res: Qt.size(root.width, root.height)
            property color c1: root.pal[0]
            property color c2: root.pal[1]
            property color c3: root.pal[2]
            fragmentShader: root.glslHead + (root.scenes[root.mode] || root.scenes["aurora"])
        }
    }

    // --- effect on top of the picture or scene ------------------------------------------------------
    Item {
        anchors.fill: parent
        visible: root.effect !== "none" && root.effects[root.effect] !== undefined
        layer.enabled: visible
        layer.smooth: true
        layer.textureSize: Qt.size(Math.max(64, Math.round(root.width * Math.min(1.0, root.quality * 1.4))),
                                   Math.max(36, Math.round(root.height * Math.min(1.0, root.quality * 1.4))))
        ShaderEffect {
            anchors.fill: parent
            blending: true
            property real time: root.t
            property size res: Qt.size(root.width, root.height)
            property color c1: root.pal[0]
            property color c2: root.pal[1]
            property color c3: root.pal[2]
            fragmentShader: root.glslHead + (root.effects[root.effect] || root.effects["stars"])
        }
    }

}
