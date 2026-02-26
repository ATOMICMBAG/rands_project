"""
Modul 3: KI-Anomalie-Detektor (VERBESSERT mit Debug-Output)
Isolation Forest erkennt Interferenzen/Anomalien im Spektrum
"""
import io
import numpy as np
from flask import Blueprint, render_template_string, request, jsonify

ai_bp = Blueprint("ai_anomaly", __name__)

# ── Modell (wird lazy initialisiert) ─────────────────────────────────────────
_model = None

def get_model():
    global _model
    if _model is None:
        from sklearn.ensemble import IsolationForest
        np.random.seed(42)
        X_train = np.random.randn(500, 5)
        _model  = IsolationForest(contamination=0.08, random_state=42)
        _model.fit(X_train)
    return _model

def extract_features(power_db, n_slices=30):
    arr    = np.array(power_db)
    slices = np.array_split(arr, n_slices)
    feats  = []
    for s in slices:
        if len(s) == 0:
            continue
        feats.append([
            float(np.mean(s)),
            float(np.std(s)),
            float(np.max(s)),
            float(np.min(s)),
            float(np.max(s) - np.min(s)),
        ])
    return np.array(feats)

def detect_anomalies(power_db, freqs_khz):
    model = get_model()
    feats = extract_features(power_db, n_slices=30)
    preds = model.predict(feats)
    scores = model.decision_function(feats)

    n = len(freqs_khz)
    step = n // len(feats)
    anomaly_ranges = []
    for i, p in enumerate(preds):
        if p == -1:
            start = freqs_khz[min(i * step, n-1)]
            end   = freqs_khz[min((i+1)*step-1, n-1)]
            anomaly_ranges.append({"start": start, "end": end,
                                   "score": round(float(scores[i]), 3)})

    n_anom  = int(np.sum(preds == -1))
    n_total = len(preds)
    return {
        "anomaly_ranges": anomaly_ranges,
        "n_anomalies":    n_anom,
        "n_total":        n_total,
        "anomaly_pct":    round(100 * n_anom / max(n_total, 1), 1),
        "verdict":        "Interferenzen erkannt!" if n_anom > 0 else "Spektrum unauffällig!"
    }

def generate_demo_with_interference():
    fs = 1e6
    t  = np.linspace(0, 0.01, int(fs * 0.01))
    sig  = 1.0 * np.cos(2 * np.pi * 200e3 * t)
    sig += 0.15 * np.random.randn(len(t))
    sig += 1.8 * np.cos(2 * np.pi * 420e3 * t + np.pi / 4)
    return sig, fs

INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>KI-Anomalie-Detektor | SDR Dashboard</title>
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
      .verdict {
        font-size: 1rem;
        font-weight: bold;
        padding: 0.7rem 1rem;
        border-radius: 3px;
        display: inline-block;
        margin-bottom: 0.8rem;
      }
      .ok {
        background: #999999;
        color: #000000;
        border: 1px solid #2ea043;
      }
      .warn {
        background: #999999;
        color: #000000;
        border: 1px solid #da3633;
      }
      .stat {
        display: inline-block;
        background: #999999;
        border-radius: 3px;
        padding: 0.5rem 1rem;
        margin: 0.3rem;
        font-size: 0.85rem;
        color: #000000;
      }
      .stat b {
        color: #000000;
      }
      #status {
        font-size: 0.85rem;
        color: #646a72;
        margin-top: 0.5rem;
      }
      #info {
        color: #646a72;
        font-size: 0.82rem;
        margin-top: 0.5rem;
        font-style: italic;
      }
      .error {
        color: #f85149;
        font-size: 0.9rem;
        background: #3a1a1a;
        padding: 0.7rem;
        border-radius: 3px;
        border-left: 3px solid #f85149;
        margin-top: 0.8rem;
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
          <a href="/ai/" class="x2">KI-Anomalie-Detektor</a>
          <a href="/proto/">Protokoll-Decoder</a>
          <a href="/security/">Security / PKI Demo</a>
          <a href="/hw/">Hardware-Interface</a>
          <a href="/stream/">Echtzeit-Signalstream</a>
          <a href="/avionics/">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>KI-Anomalie-Detektor</h1>
      <p class="sub">
        Traditionelle Spektrum-Überwachung arbeitet mit festen Schwellwerten:
        Wenn die Leistung in einem Frequenzbereich X dB über dem Rauschboden
        liegt, wird Alarm ausgelöst. Problem: Zu niedrige Schwellwerte → zu
        viele Fehlalarme. Zu hohe Schwellwerte → echte Interferenzen werden
        übersehen. Machine Learning löst das: Das Isolation Forest-Modell (aus
        scikit-learn) lernt, was "normales" Spektrum ist, und erkennt
        automatisch Abweichungen – ohne manuelle Kalibrierung.
      </p>
      <p class="sub">
        Der Algorithmus teilt das Spektrum in Scheiben (Slices) und berechnet je
        Scheibe 5 statistische Features: Mittelwert, Standardabweichung, Max,
        Min, Spannweite. Das Modell wird auf synthetischen "sauberen" Spektren
        trainiert (Gauß'sches Rauschen) und erkennt dann Abweichungen wie
        schmalbandige Interferenzen, Harmonische oder plötzliche
        Leistungsspitzen. Die farblich markierten Bereiche im Spektrum zeigen,
        wo das Modell Anomalien detektiert hat – inkl. Konfidenz-Score (je
        negativer, desto stärker die Anomalie).
      </p>
      <p class="sub">
        Automatische Klassifikation von Messergebnissen (Pass/Fail ohne manuelle
        Inspektion), Vorhersage von Wafer-Yield basierend auf Testdaten, und
        Erkennung von Produktionsausreißern.
      </p>
      <p class="sub">
        Isolation Forest erkennt Interferenzen und Anomalien im Funkspektrum
      </p>

      <div class="card">
        <h2>Signal-Eingabe</h2>
        <input type="file" id="csvFile" accept=".csv,.txt" /><br />
        <button class="demo" onclick="loadDemo()">
          ▶ Demo mit Interferenz
        </button>
        <button onclick="analyzeFile()">📂 CSV analysieren</button>
        <div id="status"></div>
        <div id="errorBox" class="error" style="display: none"></div>
        <div id="info">
          Modell: Isolation Forest (scikit-learn) &bull; Trainiert auf
          synthetischen Referenzsignalen
        </div>
      </div>

      <div id="results" style="display: none">
        <div class="card">
          <h2>Ergebnis</h2>
          <div id="verdict" class="verdict"></div>
          <br />
          <span class="stat">Anomalie-Bereiche: <b id="nAnom">-</b></span>
          <span class="stat">Gesamt-Slices: <b id="nTotal">-</b></span>
          <span class="stat">Anomalie-Anteil: <b id="aPct">-</b></span>
        </div>
        <div class="card"><div id="specPlot" style="height: 350px"></div></div>
      </div>
    </div>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
      let lastData = null;
      function setStatus(m) {
        document.getElementById("status").textContent = m;
      }
      function showError(msg) {
        const box = document.getElementById("errorBox");
        box.textContent = "❌ Fehler: " + msg;
        box.style.display = "block";
        console.error("KI-Anomalie Fehler:", msg);
      }
      function hideError() {
        document.getElementById("errorBox").style.display = "none";
      }

      function renderResults(d) {
        hideError();
        document.getElementById("results").style.display = "block";
        const vEl = document.getElementById("verdict");
        vEl.textContent = d.verdict;
        vEl.className = "verdict " + (d.n_anomalies > 0 ? "warn" : "ok");
        document.getElementById("nAnom").textContent = d.n_anomalies;
        document.getElementById("nTotal").textContent = d.n_total;
        document.getElementById("aPct").textContent = d.anomaly_pct + "%";

        const traces = [
          {
            x: lastData.freqs_khz,
            y: lastData.power_db,
            type: "scatter",
            mode: "lines",
            line: { color: "#000000", width: 1.5 },
            name: "Spektrum",
          },
        ];
        const shapes = d.anomaly_ranges.map((r) => ({
          type: "rect",
          xref: "x",
          yref: "paper",
          x0: r.start,
          x1: r.end,
          y0: 0,
          y1: 1,
          fillcolor: "rgba(255, 0, 0, 0.3)",
          line: { color: "#999999", width: 0.4 },
          layer: "below",
        }));

        try {
          Plotly.newPlot(
            "specPlot",
            traces,
            {
              shapes,
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
              title: {
                text: "Spektrum mit Anomalie-Markierungen",
                font: { color: "#000000", size: 13 },
              },
              margin: { t: 45, r: 20, b: 50, l: 60 },
            },
            { responsive: true, displayModeBar: false },
          );
        } catch (e) {
          showError("Plotly-Render-Fehler: " + e.message);
        }
      }

      async function loadDemo() {
        setStatus("Analysiere Demo-Signal mit Interferenz...");
        hideError();
        try {
          console.log("Fetching /ai/demo...");
          const res = await fetch("/ai/demo");
          console.log("Response status:", res.status);

          if (!res.ok) {
            throw new Error("HTTP " + res.status + ": " + res.statusText);
          }

          const full = await res.json();
          console.log("Data received:", full);

          if (!full.spectrum || !full.anomalies) {
            throw new Error("Invalid response structure");
          }

          lastData = full.spectrum;
          renderResults(full.anomalies);
          setStatus(
            "Demo: 200 kHz Träger + 420 kHz Interferenz (Isolation Forest)",
          );
        } catch (e) {
          showError(e.message);
          setStatus("Demo fehlgeschlagen - siehe Fehlerbox");
          console.error("loadDemo error:", e);
        }
      }

      async function analyzeFile() {
        const file = document.getElementById("csvFile").files[0];
        if (!file) {
          alert("Bitte Datei wählen");
          return;
        }
        setStatus("Analysiere...");
        hideError();
        try {
          const fd = new FormData();
          fd.append("file", file);
          const res = await fetch("/ai/analyze", { method: "POST", body: fd });
          if (!res.ok) {
            throw new Error("HTTP " + res.status);
          }
          const full = await res.json();
          if (full.error) {
            showError(full.error);
            return;
          }
          lastData = full.spectrum;
          renderResults(full.anomalies);
          setStatus("Fertig.");
        } catch (e) {
          showError(e.message);
          setStatus("Analyse fehlgeschlagen");
        }
      }

      // Check Plotly
      if (typeof Plotly === "undefined") {
        showError("Plotly.js nicht geladen - CDN-Problem?");
      } else {
        console.log("Plotly loaded:", Plotly.version);
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

@ai_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

@ai_bp.route("/demo")
def demo():
    try:
        sig, fs  = generate_demo_with_interference()
        N        = len(sig)
        freqs    = np.fft.rfftfreq(N, 1.0 / fs)
        S        = np.fft.rfft(sig * np.hanning(N))
        power_db = (20 * np.log10(np.abs(S) / N + 1e-12)).tolist()
        freqs_khz= (freqs / 1000).tolist()
        return jsonify({
            "spectrum":  {"freqs_khz": freqs_khz, "power_db": power_db},
            "anomalies": detect_anomalies(power_db, freqs_khz)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ai_bp.route("/analyze", methods=["POST"])
def analyze():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Keine Datei"}), 400
    try:
        import io as _io
        data = np.loadtxt(_io.StringIO(f.read().decode("utf-8")), delimiter=",")
        if data.ndim > 1:
            data = data[:, 0]
        fs       = 1e6
        N        = len(data)
        freqs    = np.fft.rfftfreq(N, 1.0 / fs)
        S        = np.fft.rfft(data * np.hanning(N))
        power_db = (20 * np.log10(np.abs(S) / N + 1e-12)).tolist()
        freqs_khz= (freqs / 1000).tolist()
        return jsonify({
            "spectrum":  {"freqs_khz": freqs_khz, "power_db": power_db},
            "anomalies": detect_anomalies(power_db, freqs_khz)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
