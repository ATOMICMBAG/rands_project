"""
Modul 1: Spektrum-Viewer
FFT-Berechnung + Wasserfall-Diagramm aus IQ/CSV-Daten
"""
import io, os, json
import numpy as np
from flask import Blueprint, render_template_string, request, jsonify

spectrum_bp = Blueprint("spectrum", __name__)

# ── Demo-Signal generieren ───────────────────────────────────────────────────
def generate_demo_signal(fs=1e6, duration=0.01):
    """Synthetisches Signal: Träger 200kHz + Interferenz 350kHz + Rauschen"""
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sig  = 1.0 * np.cos(2 * np.pi * 200e3 * t)
    sig += 0.4 * np.cos(2 * np.pi * 350e3 * t)
    sig += 0.15 * np.random.randn(len(t))
    return t, sig, fs

def compute_fft(signal, fs, window="hann", nfft=2048):
    win_funcs = {"hann": np.hanning, "hamming": np.hamming, "blackman": np.blackman, "rect": np.ones}
    w   = win_funcs.get(window, np.hanning)(len(signal))
    sig = signal * w
    N   = min(nfft, len(sig))
    S   = np.fft.rfft(sig[:N], n=N)
    freqs = np.fft.rfftfreq(N, 1.0 / fs)
    power_db = 20 * np.log10(np.abs(S) / N + 1e-12)
    return freqs.tolist(), power_db.tolist()

def compute_waterfall(signal, fs, nfft=512, n_slices=40):
    step = max(1, len(signal) // n_slices)
    slices = []
    for i in range(n_slices):
        start = i * step
        chunk = signal[start: start + nfft]
        if len(chunk) < nfft:
            break
        S = np.fft.rfft(chunk * np.hanning(len(chunk)))
        slices.append((20 * np.log10(np.abs(S) + 1e-12)).tolist())
    freqs = np.fft.rfftfreq(nfft, 1.0 / fs).tolist()
    return freqs, slices

# ── Templates ────────────────────────────────────────────────────────────────
INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Spektrum-Viewer | SDR Dashboard</title>
    <style>
      body {
        font-family: "Roboto", sans-serif;
        background: #ffffff;
        color: #333333;
        margin: 0;
        padding: 0;
      }
      .container {
        max-width: 900px;
        margin: 0 auto;
        margin-bottom: 50px;
        padding: 220px 20px 40px;
      }
      h1 {
        color: #000000;
        font-size: 1.6rem;
        margin-bottom: 0.3rem;
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
      label {
        display: block;
        font-size: 0.85rem;
        color: #8b949e;
        margin-bottom: 0.3rem;
      }
      select,
      input[type="file"] {
        background: #ffffff;
        color: #000000;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 0.4rem 0.7rem;
        width: 100%;
        margin-bottom: 0.8rem;
      }
      .row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
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
      button.demo.selected {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      button:hover {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      #status {
        font-size: 0.85rem;
        color: #8b949e;
        margin-top: 0.8rem;
      }
      #plots {
        margin-top: 1rem;
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
          <a href="/spectrum/" class="x2">Spektrum-Viewer</a>
          <a href="/signal/">Signalanalyse</a>
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
      <h1>Spektrum-Viewer</h1>
      <p class="sub">
        Dieses Modul wandelt Zeitbereichssignale (IQ-Daten, CSV) mittels Fast
        Fourier Transform (FFT) in den Frequenzbereich um und visualisiert sie
        als interaktives Spektrum-Diagramm. Das Wasserfall-Diagramm zeigt
        zusätzlich die zeitliche Entwicklung des Spektrums – ideal um
        intermittierende Störungen oder Frequenzsprünge zu erkennen. Solchen
        Darstellungen: S-Parameter-Messungen, Filtercharakterisierung und
        Signalqualitätsprüfung für RFFE-Komponenten liefen über ähnliche
        Visualisierungen auf Rohde & Schwarz-Vektornetzwerkanalysatoren (VNA)
        und Spektrumanalysatoren.
      </p>
      <p class="sub">
        Die Auswahl verschiedener Fensterfunktionen (Hann, Hamming, Blackman,
        Rechteck) zeigt Verständnis für das Bias-Variance-Trade-off bei der
        Spektralanalyse: Hann bietet einen guten Kompromiss zwischen
        Frequenzauflösung und Nebenkeulendämpfung, während Blackman noch
        stärkere Dämpfung liefert – wichtig bei der Analyse von Signalen mit
        stark unterschiedlichen Leistungspegeln. Die interaktive
        Plotly.js-Visualisierung ermöglicht Zoom, Pan und Datenpunkt-Inspektion
        – genau wie bei kommerziellen Messgeräten. Das Demo-Signal zeigt ein
        typisches Szenario: Träger bei 200 kHz (Nutzsignal) mit einer
        Interferenz bei 350 kHz plus Rauschboden – ein klassischer Fall aus der
        SDR-Testpraxis.
      </p>
      <p class="sub">
        IQ-Daten hochladen oder Demo-Signal analysieren &mdash; FFT &amp;
        Wasserfall-Plot
      </p>

      <div class="card">
        <h2>Signal-Eingabe</h2>
        <div class="row">
          <div>
            <label>CSV-Datei (eine Spalte: Amplitudenwerte)</label>
            <input type="file" id="csvFile" accept=".csv,.txt" />
          </div>
          <div>
            <label>Fensterfunktion</label>
            <select id="window">
              <option value="hann">Hann (empfohlen)</option>
              <option value="hamming">Hamming</option>
              <option value="blackman">Blackman</option>
              <option value="rect">Rechteck</option>
            </select>
          </div>
        </div>
        <label>FFT-Größe</label>
        <select id="nfft" style="width: auto">
          <option value="512">512</option>
          <option value="1024">1024</option>
          <option value="2048" selected>2048</option>
          <option value="4096">4096</option>
        </select>
        <br />
        <button class="demo" onclick="loadDemo()">▶ Demo-Signal laden</button>
        <button onclick="analyzeFile()">▶ CSV analysieren</button>
        <div id="status"></div>
      </div>

      <div id="plots">
        <div class="card">
          <div id="fftPlot" style="width: 100%; height: 350px"></div>
        </div>
        <div class="card">
          <div id="waterfallPlot" style="width: 100%; height: 280px"></div>
        </div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
      function setStatus(msg) {
        document.getElementById("status").textContent = msg;
      }

      async function loadDemo() {
        setStatus("Lade Demo-Signal...");
        const res = await fetch(
          "/spectrum/demo?window=" +
            encodeURIComponent(document.getElementById("window").value) +
            "&nfft=" +
            document.getElementById("nfft").value,
        );
        const data = await res.json();
        renderPlots(data);
        setStatus(
          "Demo-Signal geladen: 200 kHz Träger + 350 kHz Interferenz + Rauschen",
        );
      }

      async function analyzeFile() {
        const file = document.getElementById("csvFile").files[0];
        if (!file) {
          alert("Bitte CSV-Datei auswählen");
          return;
        }
        setStatus("Analysiere...");
        const fd = new FormData();
        fd.append("file", file);
        fd.append("window", document.getElementById("window").value);
        fd.append("nfft", document.getElementById("nfft").value);
        const res = await fetch("/spectrum/analyze", {
          method: "POST",
          body: fd,
        });
        const data = await res.json();
        if (data.error) {
          setStatus("Fehler: " + data.error);
          return;
        }
        renderPlots(data);
        setStatus("Analyse abgeschlossen.");
      }

      function renderPlots(data) {
        // FFT-Plot
        Plotly.newPlot(
          "fftPlot",
          [
            {
              x: data.freqs.map((f) => (f / 1000).toFixed(2)),
              y: data.power_db,
              type: "scatter",
              mode: "lines",
              line: { color: "#000000", width: 1.5 },
              name: "Leistung [dB]",
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
              title: "Amplitude [dB]",
              gridcolor: "#222222",
              color: "#111111",
            },
            title: {
              text: "FFT-Spektrum",
              font: { color: "#000000", size: 14 },
            },
            margin: { t: 40, r: 20, b: 50, l: 60 },
          },
          { responsive: true, displayModeBar: false },
        );

        // Wasserfall
        if (data.waterfall && data.waterfall.length > 0) {
          Plotly.newPlot(
            "waterfallPlot",
            [
              {
                z: data.waterfall,
                x: data.wf_freqs.map((f) => (f / 1000).toFixed(1)),
                type: "heatmap",
                colorscale: "Viridis",
                colorbar: { title: "dB", tickfont: { color: "#555555" } },
                name: "Wasserfall",
              },
            ],
            {
              paper_bgcolor: "#999999",
              plot_bgcolor: "#888888",
              font: { color: "#000000" },
              xaxis: { title: "Frequenz [kHz]", color: "#8b949e" },
              yaxis: {
                title: "Zeit →",
                color: "#8b949e",
                showticklabels: false,
              },
              title: {
                text: "Wasserfall-Diagramm",
                font: { color: "#000000", size: 14 },
              },
              margin: { t: 40, r: 80, b: 50, l: 50 },
            },
            { responsive: true, displayModeBar: false },
          );
        }
      }

      // Demo direkt beim Laden
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

# ── Routes ────────────────────────────────────────────────────────────────────
@spectrum_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

@spectrum_bp.route("/demo")
def demo():
    window = request.args.get("window", "hann")
    nfft   = int(request.args.get("nfft", 2048))
    _, sig, fs = generate_demo_signal()
    freqs, power_db = compute_fft(sig, fs, window, nfft)
    wf_freqs, waterfall = compute_waterfall(sig, fs)
    return jsonify({"freqs": freqs, "power_db": power_db,
                    "wf_freqs": wf_freqs, "waterfall": waterfall})

@spectrum_bp.route("/analyze", methods=["POST"])
def analyze():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Keine Datei"}), 400
    window = request.form.get("window", "hann")
    nfft   = int(request.form.get("nfft", 2048))
    try:
        data = np.loadtxt(io.StringIO(f.read().decode("utf-8")), delimiter=",")
        if data.ndim > 1:
            data = data[:, 0]
        fs = 1e6  # Default: 1 MSps
        freqs, power_db = compute_fft(data, fs, window, nfft)
        wf_freqs, waterfall = compute_waterfall(data, fs)
        return jsonify({"freqs": freqs, "power_db": power_db,
                        "wf_freqs": wf_freqs, "waterfall": waterfall})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
