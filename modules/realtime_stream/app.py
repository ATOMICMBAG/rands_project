"""
Modul 7: Echtzeit-Signalstream
Live-SDR-Spektrum via WebSocket – Aktualisierung alle 500ms
"""
import numpy as np
from flask import Blueprint, render_template_string
from flask_socketio import SocketIO, emit
import time
import threading

realtime_bp = Blueprint("realtime", __name__)

# ── Globale SocketIO-Referenz (wird von main.py gesetzt) ───────────────────
socketio = None

def set_socketio(sio):
    """Wird von main.py aufgerufen, um SocketIO-Instanz zu setzen"""
    global socketio
    socketio = sio

# ── Signal-Generator ─────────────────────────────────────────────────────────
class SignalGenerator:
    def __init__(self):
        self.running = False
        self.thread = None
        self.fs = 1e6  # 1 MHz Sample-Rate
        self.carrier_freq = 200e3  # 200 kHz
        self.noise_level = 0.2
        self.duration_per_frame = 0.01  # 10ms pro Frame
        
    def generate_frame(self):
        """Generiert ein Frame mit synthetischem Signal + FFT"""
        n_samples = int(self.fs * self.duration_per_frame)
        t = np.linspace(0, self.duration_per_frame, n_samples, endpoint=False)
        
        # Träger + wandernde Interferenz + Rauschen
        phase_shift = (time.time() % 10) / 10.0  # Langsam wandernde Phase
        sig  = 1.0 * np.cos(2 * np.pi * self.carrier_freq * t)
        sig += 0.5 * np.cos(2 * np.pi * (350e3 + phase_shift * 50e3) * t)
        sig += self.noise_level * np.random.randn(len(t))
        
        # FFT berechnen
        nfft = 512
        window = np.hanning(min(nfft, len(sig)))
        sig_windowed = sig[:nfft] * window
        S = np.fft.rfft(sig_windowed)
        freqs = np.fft.rfftfreq(nfft, 1.0 / self.fs)
        power_db = 20 * np.log10(np.abs(S) / nfft + 1e-12)
        
        return {
            'freqs': (freqs / 1000).tolist(),  # kHz
            'power_db': power_db.tolist(),
            'timestamp': time.time()
        }
    
    def stream_loop(self):
        """Streaming-Loop: Sendet alle 500ms neue Daten"""
        while self.running:
            if socketio:
                frame = self.generate_frame()
                socketio.emit('spectrum_update', frame, namespace='/stream')
            socketio.sleep(0.5)  # 500ms
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = socketio.start_background_task(self.stream_loop)
    
    def stop(self):
        self.running = False

# Globale Generator-Instanz
signal_gen = SignalGenerator()

# ── Templates ────────────────────────────────────────────────────────────────
INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Echtzeit-Stream | SDR Dashboard</title>
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
      input[type="range"] {
        background: #bbbbbb;
        color: #000000;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 0.4rem 0.7rem;
        width: 100%;
        margin-bottom: 0.8rem;
      }
      .param-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 1rem;
      }
      .param-value {
        color: #56d364;
        font-weight: bold;
        font-size: 0.9rem;
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
      button.stop {
        background: #da3633;
      }
      button.stop.selected {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      button.start {
        background: #bbbbbb;
      }
      button.start.selected {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      button:hover {
        opacity: 0.85;
      }
      button:disabled {
        background: #30363d;
        cursor: not-allowed;
        opacity: 0.5;
      }
      #status {
        display: inline-block;
        margin-left: 1rem;
        font-size: 0.85rem;
        padding: 0.3rem 0.8rem;
        border-radius: 3px;
        background: #6cc78f;
        border: 1px solid #30363d;
      }
      #status.live {
        background: #1a472a;
        border-color: #2ea043;
        color: #56d364;
      }
      #plots {
        margin-top: 1rem;
      }
      .info-text {
        font-size: 0.8rem;
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
          <a href="/signal/">Signalanalyse</a>
          <a href="/ai/">KI-Anomalie-Detektor</a>
          <a href="/proto/">Protokoll-Decoder</a>
          <a href="/security/">Security / PKI Demo</a>
          <a href="/hw/">Hardware-Interface</a>
          <a href="/stream/" class="x2">Echtzeit-Signalstream</a>
          <a href="/avionics/">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>Echtzeit-Signalstream</h1>
      <p class="sub">
        Traditionelle SDR-Software (z.B. SDR#, GNURadio) zeigt das Spektrum in
        Echtzeit: Der FFT-Plot aktualisiert sich 10-20 Mal pro Sekunde, man
        sieht Signale wandern, Pegel schwanken, Interferenzen aufblitzen. Dieses
        Modul simuliert genau das: Ein synthetisches SDR-Signal (Träger +
        Rauschen + zufällige Interferenzen) wird alle 500ms neu generiert und
        via WebSocket an den Browser gesendet. Der Plotly-Plot aktualisiert sich
        ohne Page-Reload – echtes "Live-Feeling".
      </p>
      <p class="sub">
        Technisch nutzt das Modul flask-socketio (Server-Seite) und
        socket.io-client (Browser-Seite): Der Server sendet kontinuierlich neue
        FFT-Daten, der Client empfängt sie und rendert das Spektrum mit
        Plotly.react (effizienter als newPlot, da nur Daten aktualisiert werden,
        nicht die komplette Grafik). Das entspricht dem Datenfluss in echter
        SDR-Hardware: IQ-Samples vom ADC → FFT in FPGA/DSP → Darstellung in
        Host-Software.
      </p>
      <p class="sub">
        Das Demo-Signal zeigt ein typisches Szenario: Ein Träger "driftet"
        langsam (simulierte Frequenzinstabilität), eine Interferenz taucht
        intermittierend auf (simuliert Bluetooth-Störung oder Radar-Sweep), und
        der Rauschboden schwankt leicht (thermisches Rauschen). In der Praxis
        kommt so etwas ständig vor – SDR-Entwickler müssen diese Dynamik im Auge
        behalten. Die Echtzeit-Visualisierung macht das sofort sichtbar.
      </p>
      <p class="sub">
        Optional: Slider für Signal-Parameter (Trägerfrequenz, Rausch-Level,
        Interferenz-Stärke) ermöglichen interaktive Experimente – ideal für
        Demonstrationen oder Schulungen.
      </p>
      <p class="sub">
        Live-SDR-Spektrum-Simulation &mdash; Aktualisierung alle 500ms via
        WebSocket
      </p>

      <div class="card">
        <h2>Stream-Steuerung</h2>
        <button class="start" id="btnStart" onclick="startStream()">
          ▶ Stream starten
        </button>
        <button class="stop" id="btnStop" onclick="stopStream()" disabled>
          ⬛ Stream stoppen
        </button>
        <span id="status">Bereit</span>
        <p class="info-text">
          Frames empfangen: <span id="frameCount">0</span> | Latenz:
          <span id="latency">--</span> ms
        </p>
      </div>

      <div class="card">
        <h2>Signal-Parameter</h2>
        <div class="param-row">
          <div>
            <label
              >Trägerfrequenz:
              <span class="param-value" id="valCarrier">200</span> kHz</label
            >
            <input
              type="range"
              id="sliderCarrier"
              min="100"
              max="400"
              value="200"
              step="10"
              oninput="updateParams()"
            />
          </div>
          <div>
            <label
              >Rausch-Level:
              <span class="param-value" id="valNoise">0.2</span></label
            >
            <input
              type="range"
              id="sliderNoise"
              min="0"
              max="1"
              value="0.2"
              step="0.05"
              oninput="updateParams()"
            />
          </div>
        </div>
        <p class="info-text">
          Parameter werden in Echtzeit angewendet (nur bei aktivem Stream).
        </p>
      </div>

      <div id="plots">
        <div class="card">
          <div id="spectrumPlot" style="width: 100%; height: 400px"></div>
        </div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
      let socket = null;
      let frameCount = 0;
      let isStreaming = false;
      let plotInitialized = false;

      function startStream() {
        if (isStreaming) return;
        socket = io("/stream");

        socket.on("connect", () => {
          console.log("WebSocket verbunden");
          socket.emit("start_stream", {
            carrier_freq:
              parseFloat(document.getElementById("sliderCarrier").value) * 1000,
            noise_level: parseFloat(
              document.getElementById("sliderNoise").value,
            ),
          });
          isStreaming = true;
          frameCount = 0;
          document.getElementById("btnStart").disabled = true;
          document.getElementById("btnStop").disabled = false;
          document.getElementById("status").textContent = "LIVE";
          document.getElementById("status").className = "live";
        });

        socket.on("spectrum_update", (data) => {
          frameCount++;
          document.getElementById("frameCount").textContent = frameCount;

          const latency = Date.now() - data.timestamp * 1000;
          document.getElementById("latency").textContent = Math.round(latency);

          updatePlot(data);
        });

        socket.on("disconnect", () => {
          console.log("WebSocket getrennt");
        });
      }

      function stopStream() {
        if (!isStreaming || !socket) return;
        socket.emit("stop_stream");
        socket.disconnect();
        socket = null;
        isStreaming = false;
        document.getElementById("btnStart").disabled = false;
        document.getElementById("btnStop").disabled = true;
        document.getElementById("status").textContent = "Gestoppt";
        document.getElementById("status").className = "";
      }

      function updateParams() {
        document.getElementById("valCarrier").textContent =
          document.getElementById("sliderCarrier").value;
        document.getElementById("valNoise").textContent =
          document.getElementById("sliderNoise").value;

        if (isStreaming && socket) {
          socket.emit("update_params", {
            carrier_freq:
              parseFloat(document.getElementById("sliderCarrier").value) * 1000,
            noise_level: parseFloat(
              document.getElementById("sliderNoise").value,
            ),
          });
        }
      }

      function updatePlot(data) {
        const trace = {
          x: data.freqs,
          y: data.power_db,
          type: "scatter",
          mode: "lines",
          line: { color: "#000000", width: 2 },
          name: "Live-Spektrum",
        };

        const layout = {
          paper_bgcolor: "#999999",
          plot_bgcolor: "#888888",
          font: { color: "#000000" },
          xaxis: {
            title: "Frequenz [kHz]",
            gridcolor: "#222222",
            color: "#111111",
            range: [0, 500],
          },
          yaxis: {
            title: "Amplitude [dB]",
            gridcolor: "#222222",
            color: "#111111",
          },
          title: {
            text: "Live-FFT-Spektrum (Aktualisierung: 500ms)",
            font: { color: "#000000", size: 14 },
          },
          margin: { t: 40, r: 20, b: 50, l: 60 },
        };

        const config = { responsive: true, displayModeBar: false };

        if (!plotInitialized) {
          Plotly.newPlot("spectrumPlot", [trace], layout, config);
          plotInitialized = true;
        } else {
          Plotly.react("spectrumPlot", [trace], layout, config);
        }
      }

      // Auto-Start beim Laden
      window.onload = () => {
        startStream();
      };

      // Cleanup beim Verlassen
      window.onbeforeunload = () => {
        if (isStreaming) stopStream();
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

# ── Routes ────────────────────────────────────────────────────────────────────
@realtime_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

# ── SocketIO Handlers ────────────────────────────────────────────────────────
def register_socketio_handlers(sio):
    """Registriert WebSocket-Handler (wird von main.py aufgerufen)"""
    
    @sio.on('start_stream', namespace='/stream')
    def handle_start_stream(data):
        if data:
            signal_gen.carrier_freq = data.get('carrier_freq', 200e3)
            signal_gen.noise_level = data.get('noise_level', 0.2)
        signal_gen.start()
        emit('status', {'message': 'Stream gestartet'})
    
    @sio.on('stop_stream', namespace='/stream')
    def handle_stop_stream():
        signal_gen.stop()
        emit('status', {'message': 'Stream gestoppt'})
    
    @sio.on('update_params', namespace='/stream')
    def handle_update_params(data):
        if data:
            signal_gen.carrier_freq = data.get('carrier_freq', signal_gen.carrier_freq)
            signal_gen.noise_level = data.get('noise_level', signal_gen.noise_level)
