"""
Modul 6: Hardware-Interface Stub
R&S SCPI Mock: VNA (ZVA-Klasse) + Spektrumanalysator (FSW-Klasse)
Erweiterbar auf echte PyVISA-Anbindung durch Austausch der Mock-Klassen
"""
import json, random, time
from flask import Blueprint, render_template_string, request, jsonify

hw_bp = Blueprint("hw", __name__)

# ── SCPI Mock Devices ─────────────────────────────────────────────────────────
class RnS_VNA_Mock:
    """Simuliert R&S ZVA / ZNB Vektornetzwerkanalysator"""
    model = "R&S ZNB20 (Mock)"
    def idn(self):
        return "Rohde&Schwarz,ZNB20,1234567890,3.30"
    def query(self, cmd):
        cmd = cmd.strip().upper()
        if cmd == "*IDN?":
            return self.idn()
        if cmd == ":SENS:FREQ:START?":
            return "100000"      # 100 kHz
        if cmd == ":SENS:FREQ:STOP?":
            return "20000000000" # 20 GHz
        if cmd == ":SENS:SWE:POIN?":
            return "401"
        if "S11" in cmd or "S21" in cmd:
            # Simulierter S-Parameter-Sweep (401 Punkte)
            import numpy as np
            pts = 401
            f   = np.linspace(1e8, 6e9, pts)
            # S11: simuliertes Bandpassfilter um 2.4 GHz
            s11 = -30 + 25 * np.exp(-((f - 2.4e9) / 200e6)**2) + np.random.randn(pts) * 0.3
            s21 = -3  - 20 * np.exp(-((f - 2.4e9) / 200e6)**2) + np.random.randn(pts) * 0.2
            param = "S21" if "S21" in cmd else "S11"
            vals  = s21 if param == "S21" else s11
            return {
                "param": param,
                "freqs_ghz": (f / 1e9).tolist(),
                "values_db": vals.tolist(),
                "unit": "dB",
            }
        if cmd == ":SYST:ERR?":
            return "0,No error"
        return f"Unknown command: {cmd}"

class RnS_FSW_Mock:
    """Simuliert R&S FSW Spektrumanalysator"""
    model = "R&S FSW26 (Mock)"
    def idn(self):
        return "Rohde&Schwarz,FSW26,9876543210,4.20"
    def query(self, cmd):
        cmd = cmd.strip().upper()
        if cmd == "*IDN?":
            return self.idn()
        if cmd == ":SENS:FREQ:CENT?":
            return "2400000000"   # 2.4 GHz
        if cmd == ":SENS:FREQ:SPAN?":
            return "1000000000"   # 1 GHz Span
        if cmd == ":SENS:BAND:RES?":
            return "1000000"      # RBW 1 MHz
        if "TRAC" in cmd or "SWEEP" in cmd:
            import numpy as np
            pts   = 501
            f_mhz = np.linspace(1900, 2900, pts)
            # Simuliertes Spektrum: LTE-Band-Signale bei 2.1 und 2.6 GHz
            spec  = -80 + np.random.randn(pts) * 2
            spec += 30 * np.exp(-((f_mhz - 2100) / 20)**2)  # 2.1 GHz
            spec += 25 * np.exp(-((f_mhz - 2600) / 15)**2)  # 2.6 GHz
            return {
                "freqs_mhz":   f_mhz.tolist(),
                "power_dbm":   spec.tolist(),
                "ref_level":   -10,
                "rbw_mhz":     1,
                "unit": "dBm",
            }
        if cmd == ":SYST:ERR?":
            return "0,No error"
        return f"Unknown command: {cmd}"

# Device Registry
DEVICES = {
    "vna":  {"instance": RnS_VNA_Mock(),  "label": "VNA – R&S ZNB20 (Mock)"},
    "fsw":  {"instance": RnS_FSW_Mock(),  "label": "Spektrumanalysator – R&S FSW26 (Mock)"},
}

INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Hardware-Interface | SDR Dashboard</title>
    <style>
      body {
        font-family: "Roboto", sans-serif;
        background: #ffffff;
        color: #333333;
        margin: 0;
      }
      .container {
        max-width: 1000px;
        margin: 0 auto;
        margin-bottom: 50px;
        padding: 220px 20px 40px;
      }
      h1 {
        color: #000000;
        font-size: 1.6rem;
      }
      p.sub {
        color: #2b3036;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
      }
      .card {
        background: #ffffff;
        color: #000000;
        border: 1px solid #555555;
        border-radius: 3px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
      }
      .card h2 {
        font-size: 1rem;
        color: #000000;
        margin-bottom: 1rem;
      }
      .device-row {
        display: flex;
        gap: 1rem;
        align-items: center;
        margin-bottom: 0.5rem;
      }
      .device-btn {
        background: #bbbbbb;
        border: 1px solid #30363d;
        color: #000000;
        padding: 0.5rem 1rem;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: border-color 0.2s;
      }
      .device-btn.selected {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      .device-btn:hover {
        border-color: #808080;
      }
      .scpi-row {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
      }
      input[type="text"] {
        flex: 1;
        background: #ffffff;
        color: #000000;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 0.5rem 0.8rem;
        font-family: monospace;
        font-size: 0.88rem;
      }
      button {
        background: #bbbbbb;
        border: 1px solid #30363d;
        color: #000000;
        padding: 0.5rem 1rem;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: border-color 0.2s;
      }
      button.green {
        background: #2ea043;
      }
      button:hover {
        border-color: #808080;
      }
      .terminal {
        background: #111111;
        border: 1px solid #888888;
        border-radius: 3px;
        padding: 0.8rem;
        font-family: monospace;
        font-size: 0.82rem;
        min-height: 120px;
        max-height: 240px;
        overflow-y: auto;
      }
      .terminal .line {
        margin: 0.15rem 0;
      }
      .terminal .cmd {
        color: #999999;
      }
      .terminal .resp {
        color: #56d364;
      }
      .terminal .err {
        color: #f85149;
      }
      .presets {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 0.8rem;
      }
      .preset {
        background: #111111;
        border: 1px solid #30363d;
        color: #999999;
        padding: 0.2rem 0.6rem;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.78rem;
        font-family: monospace;
      }
      .preset:hover {
        border-color: #58a6ff;
        color: #58a6ff;
      }
      .plot-info {
        font-size: 0.78rem;
        color: #8b949e;
        margin-bottom: 0.5rem;
        font-style: italic;
      }
      footer {
        text-align: center;
        padding: 2rem;
        color: #999999;
        font-size: 0.82rem;
        border-top: 1px solid #e0e0e0;
        background: #fafafa;
        font-weight: 300;
      }
      footer a {
        color: #000000;
        text-decoration: none;
        font-weight: 500;
      }
      footer a:hover {
        color: #777777;
      }
      header {
        position: fixed;
        top: 0;
        width: 100%;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        z-index: 1000;
      }
      header h1 {
        font-size: 2rem;
        color: #000000;
        letter-spacing: 1px;
        font-weight: 300;
      }
      header p {
        color: #c9c9c9;
        margin-top: 0.5rem;
        font-size: 1rem;
        font-weight: 300;
      }
      .main-nav {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        background: #ffffff;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        padding: 1rem 5%;
        display: flex;
        justify-content: flex-start;
        align-items: center;
        box-sizing: border-box;
        max-width: 100%;
        margin: 0 auto;
      }
      .menu-toggle {
        display: none;
        cursor: pointer;
        background: none;
        border: none;
        padding: 10px;
      }
      .menu-toggle span {
        display: block;
        width: 25px;
        height: 3px;
        background: #333333;
        margin: 5px 0;
        transition: 0.3s;
        border-radius: 2px;
      }
      .logo a {
        font-size: 2rem;
        font-weight: 700;
        color: #000000;
        text-decoration: none;
        letter-spacing: 2px;
      }
      .nav-links {
        display: flex;
        align-items: center;
        gap: 2rem;
        margin-left: 3%;
        border-left: 2mm ridge #000000;
        padding-left: 3%;
      }
      .nav-links a {
        color: #333333;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.3s ease;
      }
      .nav-links a:hover {
        color: #777777;
      }
      @media screen and (max-width: 768px) {
        .menu-toggle {
          display: block;
          margin-right: 1rem;
          order: 1;
        }

        .logo {
          order: 2;
        }

        .nav-links {
          display: none;
          position: fixed;
          top: 60px;
          left: 0;
          right: 0;
          width: 100vw;
          background: #ffffff;
          flex-direction: column;
          padding: 0.5rem;
          box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
          gap: 0.5rem;
          box-sizing: border-box;
          margin: 0;
        }

        .nav-links.active {
          display: flex;
        }

        .nav-links a {
          padding: 0.3rem 0;
          width: 100%;
          text-align: center;
          font-size: 0.9rem;
        }

        .language-selector {
          margin-top: 1rem;
          width: 100%;
          text-align: center;
        }

        .language-selector select {
          width: 80%;
          max-width: 200px;
        }
      }
      .x1 {
        color: #000000;
        font-weight: bold;
        transition:
          transform 0.2s,
          text-shadow 0.2s;
        text-shadow: 0 4px 4px rgba(0, 3, 44, 0.4);
      }
      .x2 {
        color: #000000;
        font-weight: bold;
        transition:
          transform 0.2s,
          text-shadow 0.2s;
        text-shadow: 0 4px 4px rgba(0, 3, 44, 0.4);
      }
    </style>
  </head>
  <body>
    <header>
      <nav class="main-nav">
        <div class="menu-toggle">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div class="logo">
          <a href="https://maazi.de">maazi.de</a>
        </div>
        <div class="nav-links">
          <a href="/" class="x1">SDR Spectrum Intelligence Dashboard</a>
          <a href="/spectrum/">Spektrum-Viewer</a>
          <a href="/signal/">Signalanalyse</a>
          <a href="/ai/">KI-Anomalie-Detektor</a>
          <a href="/proto/">Protokoll-Decoder</a>
          <a href="/security/">Security / PKI Demo</a>
          <a href="/hw/" class="x2">Hardware-Interface</a>
          <a href="/stream/">Echtzeit-Signalstream</a>
          <a href="/avionics/">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>Hardware-Interface – R&amp;S SCPI Mock</h1>
      <p class="sub">
        Moderne HF-Messgeräte von Rohde & Schwarz (VNA, Spektrumanalysatoren,
        Signalgeneratoren) werden über SCPI gesteuert: Ein textbasiertes
        Protokoll über LAN, USB oder GPIB. Beispiel: `*IDN?` gibt Gerät-ID
        zurück, `:SENS:FREQ:CENT?` liefert die Center-Frequenz des
        Spektrumanalysators. Dieses Modul simuliert zwei Rohde & Schwarz-Geräte:
      </p>
      <p class="sub">
        Rohde & Schwarz ZNB20 (VNA-Mock): Vektornetzwerkanalysatoren messen
        S-Parameter (Reflexion S11, Transmission S21) über einen
        Frequenzbereich. Diese Messungen sind essentiell für
        Filtercharakterisierung, Antennen-Matching und HF-Schaltungsdesign.
        S-Parameter-Messungen von RFFE-Filtern, Vergleich mit Simulationsdaten,
        Optimierung von Anpassnetzwerken. Das Modul simuliert einen S11-Sweep
        (Bandpassfilter um 2.4 GHz) – genau das, was ein echter VNA liefern
        würde.
      </p>
      <p class="sub">
        Rohde & Schwarz FSW26 (Spektrumanalysator-Mock): Misst Signalleistung
        über Frequenz (Spektrum-Sweep). Das Demo zeigt simulierte LTE-Signale
        bei 2.1 GHz und 2.6 GHz – typisch für Mobilfunk-Testing. Die
        SCPI-Befehle entsprechen den echten Rohde & Schwarz-Kommandos (z.B.
        `:TRAC:DATA? TRACE1` für Messdaten-Abruf).
      </p>
      <p class="sub">
        Die Web-UI bietet ein Terminal-artiges Interface: SCPI-Befehl eingeben →
        Antwort sehen → Plot aktualisiert sich automatisch. Das ist genau der
        Workflow, den Rohde & Schwarz-Testingenieure kennen – nur in einer
        Web-App statt in LabView/Python-Skripten. Die Mock-Klassen sind so
        gebaut, dass sie durch echte PyVISA-Objekte ersetzt werden können (eine
        Zeile Code-Änderung) – dann steuert das Modul echte Rohde &
        Schwarz-Hardware.
      </p>
      <p class="sub">
        Simulierte R&amp;S Messgeräte via SCPI &mdash; erweiterbar auf echte
        PyVISA-Anbindung
      </p>

      <div class="card">
        <h2>Gerät auswählen</h2>
        <div class="device-row">
          <button
            class="device-btn selected"
            id="btn-vna"
            onclick="selectDevice('vna')"
          >
            VNA – R&S ZNB20 (Mock)
          </button>
          <button class="device-btn" id="btn-fsw" onclick="selectDevice('fsw')">
            Spektrumanalysator – R&S FSW26 (Mock)
          </button>
        </div>
      </div>

      <div class="card">
        <h2>SCPI-Terminal</h2>
        <p style="font-size: 1rem; color: #111111; margin-bottom: 0.5rem">
          Schnellbefehle:
        </p>
        <div class="presets" id="presets"></div>
        <div class="scpi-row">
          <input
            type="text"
            id="scpiCmd"
            placeholder="SCPI-Befehl eingeben, z.B. *IDN?"
            value="*IDN?"
          />
          <button onclick="sendSCPI()">▶ Senden</button>
          <button class="green" onclick="runWorkflow()">
            ▶ Messung starten
          </button>
        </div>
        <div class="terminal" id="terminal">
          <div class="line" style="color: #999999">
            // SCPI-Terminal bereit...
          </div>
        </div>
      </div>

      <div class="card">
        <h2>Messergebnis</h2>
        <div class="plot-info" id="plotInfo">
          Klicke "Messung starten" für einen Sweep-Plot.
        </div>
        <div id="measurePlot" style="height: 320px"></div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
      let currentDevice = "vna";
      const PRESETS = {
        vna: [
          "*IDN?",
          ":SENS:FREQ:START?",
          ":SENS:FREQ:STOP?",
          ":SENS:SWE:POIN?",
          ":CALC1:DATA? S11",
          ":CALC1:DATA? S21",
          ":SYST:ERR?",
        ],
        fsw: [
          "*IDN?",
          ":SENS:FREQ:CENT?",
          ":SENS:FREQ:SPAN?",
          ":SENS:BAND:RES?",
          ":TRAC:DATA? TRACE1",
          ":SYST:ERR?",
        ],
      };

      function selectDevice(dev) {
        currentDevice = dev;
        document
          .querySelectorAll(".device-btn")
          .forEach((b) => b.classList.remove("selected"));
        document.getElementById("btn-" + dev).classList.add("selected");
        renderPresets();
        log(
          "// Gerät gewechselt: " +
            document.getElementById("btn-" + dev).textContent.trim(),
          "cmd",
        );
      }

      function renderPresets() {
        document.getElementById("presets").innerHTML = PRESETS[currentDevice]
          .map(
            (p) => `<span class="preset" onclick="setCmd('${p}')">${p}</span>`,
          )
          .join("");
      }

      function setCmd(c) {
        document.getElementById("scpiCmd").value = c;
      }

      function log(txt, cls = "resp") {
        const t = document.getElementById("terminal");
        const d = document.createElement("div");
        d.className = "line " + cls;
        d.textContent = txt;
        t.appendChild(d);
        t.scrollTop = t.scrollHeight;
      }

      async function sendSCPI() {
        const cmd = document.getElementById("scpiCmd").value.trim();
        if (!cmd) return;
        log(">> " + cmd, "cmd");
        const res = await fetch("/hw/scpi", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device: currentDevice, command: cmd }),
        });
        const data = await res.json();
        if (data.error) {
          log("ERR: " + data.error, "err");
          return;
        }
        if (typeof data.response === "object") {
          log(
            "<< [Messdaten: " +
              JSON.stringify(data.response).substring(0, 80) +
              "...]",
            "resp",
          );
          if (data.response.freqs_ghz) {
            plotSParams(data.response);
          } else if (data.response.freqs_mhz) {
            plotSpectrum(data.response);
          }
        } else {
          log("<< " + data.response, "resp");
        }
      }

      async function runWorkflow() {
        const sweepCmd =
          currentDevice === "vna" ? ":CALC1:DATA? S11" : ":TRAC:DATA? TRACE1";
        log("// Starte Sweep-Messung...", "cmd");
        document.getElementById("scpiCmd").value = sweepCmd;
        await sendSCPI();
      }

      function plotSParams(d) {
        document.getElementById("plotInfo").textContent =
          "S-Parameter Sweep &ndash; simuliertes Bandpassfilter um 2.4 GHz";
        Plotly.newPlot(
          "measurePlot",
          [
            {
              x: d.freqs_ghz,
              y: d.values_db,
              type: "scatter",
              mode: "lines",
              line: { color: "#000000", width: 1.5 },
              name: d.param + " [dB]",
            },
          ],
          {
            paper_bgcolor: "#999999",
            plot_bgcolor: "#888888",
            font: { color: "#000000" },
            xaxis: {
              title: "Frequenz [GHz]",
              gridcolor: "#222222",
              color: "#111111",
            },
            yaxis: {
              title: "Amplitude [dB]",
              gridcolor: "#222222",
              color: "#111111",
            },
            title: {
              text: d.param + " – R&S ZNB20 (Mock)",
              font: { color: "#000000", size: 13 },
            },
            margin: { t: 40, r: 20, b: 50, l: 60 },
          },
          { responsive: true, displayModeBar: false },
        );
      }

      function plotSpectrum(d) {
        document.getElementById("plotInfo").textContent =
          "Spektrum-Sweep &ndash; simulierte LTE-Signale bei 2.1 & 2.6 GHz";
        Plotly.newPlot(
          "measurePlot",
          [
            {
              x: d.freqs_mhz,
              y: d.power_dbm,
              type: "scatter",
              mode: "lines",
              line: { color: "#000000", width: 1.5 },
              name: "Leistung [dBm]",
            },
          ],
          {
            paper_bgcolor: "#999999",
            plot_bgcolor: "#888888",
            font: { color: "#000000" },
            xaxis: {
              title: "Frequenz [MHz]",
              gridcolor: "#222222",
              color: "#111111",
            },
            yaxis: {
              title: "Leistung [dBm]",
              gridcolor: "#222222",
              color: "#111111",
            },
            title: {
              text: "Spektrum – R&S FSW26 (Mock)",
              font: { color: "#000000", size: 13 },
            },
            margin: { t: 40, r: 20, b: 50, l: 60 },
          },
          { responsive: true, displayModeBar: false },
        );
      }

      window.onload = () => {
        renderPresets();
        // Auto IDN
        document.getElementById("scpiCmd").value = "*IDN?";
        sendSCPI();
      };
    </script>
    <script>
      // Mobile Navigation
      document.addEventListener("DOMContentLoaded", function () {
        // Navigation Menu Toggle
        const menuToggle = document.querySelector(".menu-toggle");
        const navLinks = document.querySelector(".nav-links");

        menuToggle.addEventListener("click", function (event) {
          event.stopPropagation();
          navLinks.classList.toggle("active");
        });

        // AI Dropdown Menu
        const aiDropdownButton = document.querySelector(".ai-dropdown-button");
        const aiDropdownContent = document.querySelector(
          ".ai-dropdown-content",
        );

        if (aiDropdownButton && aiDropdownContent) {
          aiDropdownButton.addEventListener("click", function (event) {
            event.stopPropagation();
            aiDropdownButton.classList.toggle("active");
            aiDropdownContent.classList.toggle("active");
          });

          // Close dropdown when clicking outside
          document.addEventListener("click", function (event) {
            if (!event.target.closest(".ai-dropdown")) {
              aiDropdownButton.classList.remove("active");
              aiDropdownContent.classList.remove("active");
            }
          });
        }

        // Close menu when clicking outside
        document.addEventListener("click", function (event) {
          if (!event.target.closest(".main-nav")) {
            navLinks.classList.remove("active");
          }
        });

        // Close menu when clicking a link
        navLinks.addEventListener("click", function (event) {
          if (event.target.tagName === "A") {
            navLinks.classList.remove("active");
          }
        });

        // Close menu when window is resized above mobile breakpoint
        window.addEventListener("resize", function () {
          if (window.innerWidth > 768) {
            navLinks.classList.remove("active");
          }
        });
      });
      // Header Scroll Effect
      let lastScroll = 0;
      window.addEventListener("scroll", () => {
        const header = document.querySelector("header");
        const currentScroll = window.pageYOffset;

        if (currentScroll <= 0) {
          header.classList.remove("scroll-up");
          return;
        }

        if (
          currentScroll > lastScroll &&
          !header.classList.contains("scroll-down")
        ) {
          header.classList.remove("scroll-up");
          header.classList.add("scroll-down");
        } else if (
          currentScroll < lastScroll &&
          header.classList.contains("scroll-down")
        ) {
          header.classList.remove("scroll-down");
          header.classList.add("scroll-up");
        }
        lastScroll = currentScroll;
      });
      // Smooth Scrolling
      document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener("click", function (e) {
          e.preventDefault();
          document.querySelector(this.getAttribute("href")).scrollIntoView({
            behavior: "smooth",
          });
        });
      });
    </script>
  </body>
</html>
"""

@hw_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

@hw_bp.route("/scpi", methods=["POST"])
def scpi():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Kein Request-Body"}), 400
    dev_key = data.get("device", "vna")
    command = data.get("command", "*IDN?")
    if dev_key not in DEVICES:
        return jsonify({"error": f"Unbekanntes Gerät: {dev_key}"}), 400
    try:
        result = DEVICES[dev_key]["instance"].query(command)
        return jsonify({"device": dev_key, "command": command, "response": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@hw_bp.route("/devices")
def devices():
    return jsonify([{"key": k, "label": v["label"]} for k, v in DEVICES.items()])
