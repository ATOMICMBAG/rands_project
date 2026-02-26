"""
SDR Spectrum Intelligence Dashboard
Hiring Project - Rohde & Schwarz | Besem Maazi
main.py - Haupt-App, registriert alle Module als Blueprints
"""

from flask import Flask, render_template_string, send_from_directory
from flask_socketio import SocketIO
import os

app = Flask(__name__)
app.secret_key = "sdr-dashboard-secret-2025"
app.config['SECRET_KEY'] = "sdr-dashboard-secret-2025"

# ── Statische Route für Modul-Bilder ─────────────────────────────────────────
@app.route('/modules/<path:filename>')
def serve_module_images(filename):
    """Serviert Bilder aus dem modules-Verzeichnis"""
    return send_from_directory('modules', filename)

# ── SocketIO initialisieren ──────────────────────────────────────────────────
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ── Blueprints registrieren ──────────────────────────────────────────────────
from modules.spectrum_viewer.app import spectrum_bp
from modules.signal_analysis.app import signal_bp
from modules.ai_anomaly.app import ai_bp
from modules.protocol_decoder.app import proto_bp
from modules.security_checker.app import sec_bp
from modules.hw_interface.app import hw_bp
from modules.realtime_stream.app import realtime_bp, register_socketio_handlers, set_socketio
from modules.avionics_bands.app import avionics_bp

app.register_blueprint(spectrum_bp, url_prefix="/spectrum")
app.register_blueprint(signal_bp,   url_prefix="/signal")
app.register_blueprint(ai_bp,       url_prefix="/ai")
app.register_blueprint(proto_bp,    url_prefix="/proto")
app.register_blueprint(sec_bp,      url_prefix="/security")
app.register_blueprint(hw_bp,       url_prefix="/hw")
app.register_blueprint(realtime_bp, url_prefix="/stream")
app.register_blueprint(avionics_bp, url_prefix="/avionics")

# SocketIO-Handler registrieren
set_socketio(socketio)
register_socketio_handlers(socketio)

# ── Landing Page ─────────────────────────────────────────────────────────────
LANDING = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SDR Spectrum Intelligence Dashboard</title>
    <style>
      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }
      body {
        font-family: "Roboto", sans-serif;
        background: #ffffff;
        color: #333333;
        min-height: 100vh;
      }
      .badge {
        display: inline-block;
        background: #777777;
        color: #fff;
        padding: 0.3rem 0.8rem;
        border-radius: 3px;
        font-size: 0.75rem;
        margin: 0.5rem 0.2rem;
        font-weight: 400;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
        padding: 2.5rem;
        max-width: 1200px;
        margin: 0 auto;
        margin-bottom: 50px;
        padding: 220px 20px 40px;
      }
      .card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 3px;
        padding: 1.5rem;
        transition:
          transform 0.2s,
          box-shadow 0.2s;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      }
      .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
      }
      .card h2 {
        font-size: 1.1rem;
        color: #000000;
        margin-bottom: 0.5rem;
        font-weight: 500;
      }
      .card .num {
        font-size: 2rem;
        float: right;
        opacity: 0.08;
        color: #000000;
        font-weight: 300;
      }
      .card p {
        font-size: 0.88rem;
        color: #2b3036;
        margin: 0.5rem 0 1rem;
        line-height: 1.6;
        font-weight: 400;
      }
      .card a {
        display: inline-block;
        background: #000000;
        color: #ffffff;
        border: none;
        padding: 0.5rem 1.2rem;
        border-radius: 3px;
        text-decoration: none;
        font-size: 0.85rem;
        transition: background 0.2s;
        font-weight: 500;
      }
      .card a:hover {
        background: #333333;
      }
      .tag {
        display: inline-block;
        background: #f5f5f5;
        color: #666666;
        padding: 0.2rem 0.6rem;
        border-radius: 2px;
        font-size: 0.72rem;
        margin: 0.2rem 0.1rem;
        border: 1px solid #e0e0e0;
        font-weight: 400;
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
        font-weight: bold;
        transition:
          transform 0.2s,
          text-shadow 0.2s;
        text-shadow: 0 4px 4px rgba(0, 3, 44, 0.4);
      }
      .x2 {
        font-weight: lighter;
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
          <a href="/signal/" class="x2">Signalanalyse</a>
          <a href="/ai/" class="x2">KI-Anomalie-Detektor</a>
          <a href="/proto/" class="x2">Protokoll-Decoder</a>
          <a href="/security/" class="x2">Security / PKI Demo</a>
          <a href="/hw/" class="x2">Hardware-Interface</a>
          <a href="/stream/" class="x2">Echtzeit-Signalstream</a>
          <a href="/avionics/" class="x2">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <h3>SDR Spectrum Intelligence Dashboard</h3>

    <div class="grid">
      <div class="card">
        <span class="num">1</span>
        <h2>Spektrum-Viewer</h2>
        <p>
          IQ-Daten oder CSV-Signale hochladen und in Echtzeit als FFT-Spektrum
          und Wasserfall-Diagramm visualisieren. Dieses Tool entspricht exakt
          den Darstellungen moderner Rohde & Schwarz-Spektrumanalysatoren (FSW,
          FSVR) und zeigt, wie Signale im Frequenzbereich analysiert werden. Aus
          meiner Erfahrung mit RFFE-Filtercharakterisierung und
          Frontendmessungen weiß ich: Die richtige Visualisierung ist der erste
          Schritt zur Fehlerdiagnose. Unterstützt verschiedene Fensterfunktionen
          (Hann, Hamming, Blackman) für präzise Spektralanalyse – wie bei
          professionellen Messgeräten.
        </p>
        <br><br>
        <img src="/modules/modul_1.jpeg" style="width: 100%;" alt="spectrum"></img>
        <p>
          IQ-Daten / CSV-Upload &rarr; FFT-Plot &amp; Wasserfall-Diagramm.
          Interaktiv mit Plotly.js.
        </p>
        <span class="tag">FFT</span><span class="tag">Wasserfall</span
        ><span class="tag">IQ-Daten</span><br /><br />
        <a href="/spectrum/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">2</span>
        <h2>Signalanalyse</h2>
        <p>
          Automatische Berechnung von Signal-to-Noise Ratio (SNR),
          Signalbandbreite (-3dB/-10dB) und regelbasierte Modulationserkennung
          (AM/FM/CW). Diese Kennwerte sind essentiell für jede HF-Messung und
          Qualitätssicherung – SNR-Optimierungen und Bandbreitenanalysen sind
          tägliche Aufgaben der Charakterisierung von RFFE-Filtern. Das Modul
          zeigt, die zugrundeliegende Signalverarbeitung in Python implementiert
          und Export Funktion Bereitstellt als CSV für Weiterverarbeitung oder
          PDF-Report für Dokumentation.
        </p>
        <br><br>
        <img src="/modules/modul_2.jpeg" style="width: 100%;" alt="signal"></img>
        <p>
          SNR, Bandbreite (-3dB/-10dB), Modulationserkennung (AM/FM/CW).
          CSV-Export.
        </p>
        <span class="tag">SNR</span><span class="tag">Bandbreite</span
        ><span class="tag">Modulation</span><br /><br />
        <a href="/signal/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">3</span>
        <h2>KI-Anomalie-Detektor</h2>
        <p>
          Machine-Learning-Modell (Isolation Forest, scikit-learn) erkennt
          Interferenzen, Störsignale und Anomalien im Funkspektrum ohne
          manuelles Schwellwert-Tuning. Noch in der Entwicklung, dass Modell
          visualisiert anomale Frequenzbereiche farblich markiert im Spektrum
          und gibt Konfidenz-Scores aus. KI-gestützte Testautomatisierung ist
          ein wachsendes Feld bei Rohde & Schwarz – dieser Use-Case zeigt, wie
          KI die SDR-Testpraxis revolutionieren kann.
        </p>
        <br><br>
        <img src="/modules/modul_3.jpeg" style="width: 100%;" alt="ai"></img>
        <p>
          ML-Modell (Isolation Forest) erkennt Interferenzen und Anomalien im
          Spektrum.
        </p>
        <span class="tag">sklearn</span><span class="tag">IsolationForest</span
        ><span class="tag">KI</span><br /><br />
        <a href="/ai/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">4</span>
        <h2>Protokoll-Decoder</h2>
        <p>
          OSI-Layer 2/3/4 Demo: Ethernet-Frames, IPv4-Header und TCP/UDP-Pakete
          werden dekodiert und hierarchisch visualisiert – ohne externe
          Libraries (reines Python struct-Parsing). Bei Rohde & Schwarz
          Avionik-SDRs müssen Protokollstacks (z.B. NATO-Verfahren,
          DO-178-konforme Kommunikation) getestet und validiert werden. Dieses
          Modul zeigt Verständnis für Netzwerkprotokolle auf Bit-Ebene und die
          Fähigkeit, binäre Datenströme zu parsen – essentiell für
          Protokoll-Implementierung und Debugging. Die interaktive Layer-Ansicht
          macht Header-Felder sofort verständlich, auch für nicht-Experten.
        </p>
        <br><br>
        <img src="/modules/modul_4.jpeg" style="width: 100%;" alt="proto"></img>
        <p>
          OSI Layer 2/3/4 Demo: Ethernet, IPv4, TCP/UDP Header-Parsing &amp;
          Visualisierung.
        </p>
        <span class="tag">OSI L2-L4</span><span class="tag">Ethernet</span
        ><span class="tag">IPv4</span><br /><br />
        <a href="/proto/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">5</span>
        <h2>Security / PKI Demo</h2>
        <p>
          PKI-Zertifikatskette (Root CA → Intermediate CA → End-Entity),
          RSA-PSS-Signatur und AES-256-CBC-Verschlüsselung – Schritt für Schritt
          visualisiert. Die Rohde & Schwarz-Stelle "Software Developer Security
          Protocol" verlangt Expertise in Kryptographie, SmartCards, PKI und
          deren Theorien – genau das wird hier demonstriert. Das Modul zeigt die
          komplette PKI-Hierarchie für SDR-Gerätezertifikate (relevant für ISO
          27001 und Common Criteria Evaluierungen) und führt echte
          RSA-Signaturen sowie AES-Ver-/Entschlüsselung durch
          (pyca/cryptography-Library). Für nicht-Kryptographie-Experten:
          Verständlich aufbereitet mit Erklärungen.
        </p>
        <br><br>
        <img src="/modules/modul_5.jpeg" style="width: 100%;" alt="security"></img>
        <p>
          X.509-Zertifikate, RSA-Signatur, AES-Verschlüsselung &ndash;
          Schritt-für-Schritt visualisiert.
        </p>
        <span class="tag">PKI</span><span class="tag">RSA</span
        ><span class="tag">AES</span><br /><br />
        <a href="/security/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">6</span>
        <h2>Hardware-Interface</h2>
        <p>
          Rohde & Schwarz SCPI-Mock: Simuliert Vektornetzwerkanalysator (VNA
          ZNB20) und Spektrumanalysator (FSW26) mit SCPI-Befehlen (Standard
          Commands for Programmable Instruments). Zeigt Verständnis der Rohde &
          Schwarz-Messgeräte-Schnittstellen und ermöglicht Testautomatisierung
          ohne echte Hardware. Demo: S-Parameter-Messungen (S11/S21) und
          Spektrum-Sweeps werden als Plotly-Diagramme visualisiert – genau wie
          bei echten Rohde & Schwarz-Geräten. Erweiterbar auf echte
          PyVISA-Anbindung durch Austausch der Mock-Klassen. Relevant für:
          Testingenieur SDR, Integration Engineer Avionik.
        </p>
        <br><br>
        <img src="/modules/modul_6.jpeg" style="width: 100%;" alt="hw"></img>
        <p>
          R&amp;S SCPI Mock: VNA &amp; Spektrumanalysator simuliert.
          SCPI-Befehle absenden &amp; Antwort sehen.
        </p>
        <span class="tag">SCPI</span><span class="tag">R&S Mock</span
        ><span class="tag">PyVISA-ready</span><br /><br />
        <a href="/hw/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">7</span>
        <h2>Echtzeit-Signalstream</h2>
        <p>
          Live-SDR-Simulation: Das Spektrum aktualisiert sich alle 500ms
          automatisch über WebSocket (flask-socketio). Simuliert ein echtes
          SDR-Gerät, das kontinuierlich IQ-Daten liefert – wie bei einem Rohde &
          Schwarz FSW im "Continuous Sweep"-Modus. Das ist der WOW-Effekt für
          Besucher: Spektrum bewegt sich, Signale wandern, Interferenzen tauchen
          auf und verschwinden – alles in Echtzeit im Browser. Asynchrone
          Datenströme und Event-Driven-Architecture – wichtig für moderne
          SDR-Software-Architekturen (z.B. GNURadio, SDR#).
        </p>
        <br><br>
        <img src="/modules/modul_7.jpeg" style="width: 100%;" alt="stream"></img>
        <p>
          Live-SDR-Spektrum via WebSocket. Aktualisierung alle 500ms,
          interaktive Parameter-Steuerung.
        </p>
        <span class="tag">WebSocket</span><span class="tag">Live-FFT</span
        ><span class="tag">Echtzeit</span><br /><br />
        <a href="/stream/">Öffnen &rarr;</a>
      </div>
      <div class="card">
        <span class="num">8</span>
        <h2>Avionik-Frequenzplan</h2>
        <p>
          Interaktive Visualisierung der VHF/UHF-Frequenzbänder für
          Luftfahrtkommunikation und Navigation: VHF COM (118–137 MHz), VHF NAV
          (108–118 MHz, ILS/VOR), UHF MIL (225–400 MHz, NATO), ATC Transponder
          (1030/1090 MHz), ADS-B (1090 MHz). Zeigt direkten Bezug zur Rohde &
          Schwarz-Stelle "Integration Engineer Avionik SDR" und
          "Softwareentwickler Protokollsoftware Avionik". Die
          Frequenzplan-Darstellung (Timeline-Chart) macht komplexe
          Bandallokationen sofort verständlich – relevant für Frequenzplanung,
          Interferenzanalyse und SDR-Konfiguration in Avionik-Systemen. Klick
          auf Band → Details zu Protokoll, Modulation, Anwendung.
        </p>
        <br><br>
        <img src="/modules/modul_8.jpeg" style="width: 100%;" alt="avionics"></img>
        <p>
          VHF/UHF-Bänder für Luftfahrt: Navigation, ATC-Kommunikation, Mode S,
          ADS-B. NATO/ICAO-Standard.
        </p>
        <span class="tag">Avionik</span><span class="tag">VHF/UHF</span
        ><span class="tag">ADS-B</span><br /><br />
        <a href="/avionics/">Öffnen &rarr;</a>
      </div>
    </div>

    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
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

@app.route("/")
def index():
    return render_template_string(LANDING)

if __name__ == "__main__":
    os.makedirs("modules/spectrum_viewer/static/uploads", exist_ok=True)
    os.makedirs("modules/signal_analysis/static/plots", exist_ok=True)
    print("🚀 SDR Spectrum Intelligence Dashboard")
    print("📡 Server läuft auf http://localhost:5001")
    print("✅ WebSocket-Support aktiviert für Echtzeit-Stream")
    socketio.run(app, host="0.0.0.0", port=5001, debug=False, allow_unsafe_werkzeug=True)
