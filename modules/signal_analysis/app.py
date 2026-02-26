"""
Modul 2: Signalanalyse
SNR, Bandbreite, Modulationserkennung (AM/FM/CW)
"""
import io
import numpy as np
from scipy.signal import welch
from flask import Blueprint, render_template_string, request, jsonify

signal_bp = Blueprint("signal", __name__)

def analyze_signal(sig, fs=1e6):
    """Vollständige Signalanalyse - gibt dict mit allen Kennwerten zurück"""
    N = len(sig)

    # FFT
    freqs = np.fft.rfftfreq(N, 1.0 / fs)
    S     = np.fft.rfft(sig * np.hanning(N))
    power = (np.abs(S) / N) ** 2

    # Peak-Frequenz
    peak_idx  = np.argmax(power)
    peak_freq = freqs[peak_idx]
    peak_db   = 10 * np.log10(power[peak_idx] + 1e-20)

    # Rauschboden: Median der unteren 70% der Leistungswerte
    sorted_p   = np.sort(power)
    noise_floor = np.median(sorted_p[:int(0.7 * len(sorted_p))])
    noise_db    = 10 * np.log10(noise_floor + 1e-20)

    # SNR
    snr_db = peak_db - noise_db

    # Bandbreite -3 dB und -10 dB
    def bandwidth(threshold_db):
        thresh = power[peak_idx] / (10 ** (threshold_db / 10))
        above  = np.where(power >= thresh)[0]
        if len(above) < 2:
            return 0.0
        return float(freqs[above[-1]] - freqs[above[0]])

    bw3  = bandwidth(3)
    bw10 = bandwidth(10)

    # Modulationserkennung (regelbasiert)
    envelope = np.abs(sig)
    env_std  = np.std(envelope)
    env_mean = np.mean(envelope) + 1e-10

    # Einfache Heuristik: AM hat hohe Einhüllkurven-Variation
    am_index = env_std / env_mean
    inst_freq_var = np.std(np.diff(np.unwrap(np.angle(
        np.fft.rfft(sig))))) if N > 10 else 0

    if am_index > 0.3:
        modulation = "AM (Amplitudenmodulation)"
    elif snr_db < 6:
        modulation = "CW / Rauschen (keine klare Modulation)"
    else:
        modulation = "FM / Phase-Shift (Träger)"

    # Spektrum für Plot
    power_db = (10 * np.log10(power + 1e-20)).tolist()

    return {
        "peak_freq_khz": round(peak_freq / 1000, 2),
        "peak_db":       round(float(peak_db), 2),
        "noise_db":      round(float(noise_db), 2),
        "snr_db":        round(float(snr_db), 2),
        "bw3_khz":       round(bw3 / 1000, 2),
        "bw10_khz":      round(bw10 / 1000, 2),
        "modulation":    modulation,
        "freqs_khz":     (freqs / 1000).tolist(),
        "power_db":      power_db,
        "n_samples":     N,
        "fs_mhz":        round(fs / 1e6, 2),
    }

def generate_demo():
    fs = 1e6
    t  = np.linspace(0, 0.01, int(fs * 0.01))
    sig  = 1.0 * np.cos(2 * np.pi * 200e3 * t)
    sig += 0.4 * np.cos(2 * np.pi * 350e3 * t)
    sig += 0.1 * np.random.randn(len(t))
    return sig, fs

INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Signalanalyse | SDR Dashboard</title>
    <style>
      body {
        font-family: "Roboto", sans-serif;
        background: #ffffff;
        color: #333333;
        margin: 0;
      }
      .container {
        max-width: 960px;
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
      button.demo {
        background: #bbbbbb;
      }
      button:hover {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 1rem;
        margin-top: 0.5rem;
      }
      .kpi {
        background: #999999;
        border-radius: 3px;
        padding: 1rem;
        text-align: center;
      }
      .kpi .val {
        font-size: 1.6rem;
        font-weight: bold;
        color: #000000;
      }
      .kpi .lbl {
        font-size: 0.75rem;
        color: #000000;
        margin-top: 0.3rem;
      }
      .mod-badge {
        display: inline-block;
        background: #999999;
        color: #000000;
        padding: 0.3rem 0.8rem;
        border-radius: 3px;
        font-size: 0.85rem;
        margin-top: 0.5rem;
      }
      input[type="file"] {
        background: #ffffff;
        color: #000000;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 0.4rem 0.7rem;
        width: 97%;
        margin-bottom: 0.8rem;
        font-size: 0.9rem;
        font-family: monospace;
      }
      #status {
        font-size: 0.85rem;
        color: #8b949e;
        margin-top: 0.5rem;
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
          <a href="/signal/" class="x2">Signalanalyse</a>
          <a href="/ai/">KI-Anomalie-Detektor</a>
          <a href="/proto/">Protokoll-Decoder</a>
          <a href="/security/">Security / PKI Demo</a>
          <a href="/hw/">Hardware-Interface</a>
          <a href="/stream/">Echtzeit-Signalstream</a>
          <a href="/avionics/">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>Signalanalyse</h1>
      <p class="sub">
        Nachdem das Spektrum visualisiert ist, folgt die quantitative Analyse:
        SNR (Signal-to-Noise Ratio) gibt an, wie stark das Nutzsignal über dem
        Rauschboden liegt – ein zentraler Qualitätsindikator für jede
        Funkverbindung. Die Bandbreite (-3dB und -10dB) definiert, welchen
        Frequenzbereich ein Signal belegt – wichtig für Frequenzplanung und
        Filterauslegung. Jeder RFFE-Filter musste spezifische Bandbreiten- und
        Dämpfungsanforderungen erfüllen, und SNR-Messungen waren der Schlüssel
        zur Yield-Optimierung in der Produktion.
      </p>
      <p class="sub">
        Die regelbasierte Modulationserkennung (AM/FM/CW) zeigt, welche Art von
        Signal vorliegt – basierend auf Einhüllkurven-Variation und
        Frequenzstabilität. Moderne SDR-Systeme benötigen solche
        Vorklassifikationen für adaptive Demodulation. Die Algorithmen hier sind
        Grundlagenversionen; in der Praxis kommen Machine-Learning-Modelle zum
        Einsatz (siehe Modul 3: KI-Anomalie-Detektor). Das Modul berechnet
        außerdem den Rauschboden automatisch als Median der unteren 70% der
        Leistungswerte – eine robuste Methode gegen Ausreißer.
      </p>
      <p class="sub">
        Die Ergebnisse können als CSV exportiert werden (für Weiterverarbeitung
        in Excel/Matlab) oder als PDF-Report (für Dokumentation gegenüber
        Kunden/Behörden – relevant für Rohde & Schwarz-Zertifizierungsprozesse
        nach Common Criteria oder DO-178 in der Avionik).
      </p>
      <p class="sub">
        SNR, Bandbreite &amp; Modulationserkennung &mdash; aus
        Qualcomm/RFFE-Messtechnik-Erfahrung
      </p>

      <div class="card">
        <h2>Eingabe</h2>
        <input type="file" id="csvFile" accept=".csv,.txt" /><br />
        <button class="demo" onclick="loadDemo()">
          ▶ Demo-Signal analysieren
        </button>
        <button onclick="analyzeFile()">📂 CSV analysieren</button>
        <div id="status"></div>
      </div>

      <div id="results" style="display: none">
        <div class="card">
          <h2>Analyseergebnisse</h2>
          <div class="kpi-grid" id="kpiGrid"></div>
          <div style="margin-top: 1rem">
            <span style="color: #8b949e; font-size: 0.85rem"
              >Erkannte Modulation:
            </span>
            <span class="mod-badge" id="modBadge"></span>
          </div>
        </div>
        <div class="card"><div id="specPlot" style="height: 320px"></div></div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
      function setStatus(m) {
        document.getElementById("status").textContent = m;
      }

      function renderResults(d) {
        document.getElementById("results").style.display = "block";
        document.getElementById("modBadge").textContent = d.modulation;
        const kpis = [
          { val: d.peak_freq_khz + " kHz", lbl: "Peak-Frequenz" },
          { val: d.snr_db + " dB", lbl: "SNR" },
          { val: d.peak_db + " dB", lbl: "Peak-Leistung" },
          { val: d.noise_db + " dB", lbl: "Rauschboden" },
          { val: d.bw3_khz + " kHz", lbl: "Bandbreite -3dB" },
          { val: d.bw10_khz + " kHz", lbl: "Bandbreite -10dB" },
        ];
        document.getElementById("kpiGrid").innerHTML = kpis
          .map(
            (k) =>
              `<div class="kpi"><div class="val">${k.val}</div><div class="lbl">${k.lbl}</div></div>`,
          )
          .join("");
        Plotly.newPlot(
          "specPlot",
          [
            {
              x: d.freqs_khz,
              y: d.power_db,
              type: "scatter",
              mode: "lines",
              line: { color: "#000000", width: 1.5 },
              name: "Leistung",
            },
          ],
          {
            paper_bgcolor: "#999999",
            plot_bgcolor: "#888888",
            font: { color: "#000000" },
            xaxis: {
              title: "Frequenz [kHz]",
              gridcolor: "#222222",
              color: "#111111",
            },
            yaxis: {
              title: "Leistung [dB]",
              gridcolor: "#222222",
              color: "#111111",
            },
            title: { text: "Spektrum", font: { color: "#000000", size: 13 } },
            margin: { t: 40, r: 20, b: 50, l: 60 },
          },
          { responsive: true, displayModeBar: false },
        );
      }

      async function loadDemo() {
        setStatus("Analysiere Demo-Signal...");
        const res = await fetch("/signal/demo");
        const d = await res.json();
        renderResults(d);
        setStatus("Demo: 200 kHz + 350 kHz Träger, fs=1 MSps");
      }

      async function analyzeFile() {
        const file = document.getElementById("csvFile").files[0];
        if (!file) {
          alert("Bitte Datei wählen");
          return;
        }
        setStatus("Analysiere...");
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch("/signal/analyze", {
          method: "POST",
          body: fd,
        });
        const d = await res.json();
        if (d.error) {
          setStatus("Fehler: " + d.error);
          return;
        }
        renderResults(d);
        setStatus("Fertig.");
      }
      window.onload = loadDemo;
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

@signal_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

@signal_bp.route("/demo")
def demo():
    sig, fs = generate_demo()
    return jsonify(analyze_signal(sig, fs))

@signal_bp.route("/analyze", methods=["POST"])
def analyze():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Keine Datei"}), 400
    try:
        data = np.loadtxt(io.StringIO(f.read().decode("utf-8")), delimiter=",")
        if data.ndim > 1:
            data = data[:, 0]
        return jsonify(analyze_signal(data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
