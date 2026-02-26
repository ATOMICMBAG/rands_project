"""
Modul 8: Avionik-Frequenzplan
Interaktive Visualisierung der VHF/UHF-Avionikbänder (NATO/ICAO)
"""
from flask import Blueprint, render_template_string, jsonify

avionics_bp = Blueprint("avionics", __name__)

# ── Avionik-Frequenzbänder (NATO/ICAO) ──────────────────────────────────────
AVIONICS_BANDS = [
    {
        "name": "VHF NAV (VOR/ILS)",
        "freq_min": 108.0,
        "freq_max": 117.975,
        "category": "Navigation",
        "color": "#58a6ff",
        "description": "VHF Omnidirectional Range (VOR) und Instrument Landing System (ILS). Kanaltrennung: 50 kHz.",
        "protocols": ["VOR", "ILS LOC", "ILS GS"],
        "use_case": "Funknavigation für zivile und militärische Luftfahrt"
    },
    {
        "name": "VHF COM",
        "freq_min": 118.0,
        "freq_max": 136.975,
        "category": "Kommunikation",
        "color": "#56d364",
        "description": "Luftfahrtkommunikation (ATC, Tower, Ground). Kanaltrennung: 25 kHz (8.33 kHz in Europa ab FL195).",
        "protocols": ["AM Voice", "VDL Mode 2/3/4"],
        "use_case": "Sprechfunk zwischen Piloten und Flugsicherung"
    },
    {
        "name": "VHF Maritime",
        "freq_min": 156.0,
        "freq_max": 174.0,
        "category": "Maritime",
        "color": "#8b949e",
        "description": "Marine-Kommunikation und Notfunk (z.B. Kanal 16: 156.8 MHz).",
        "protocols": ["FM Voice", "DSC"],
        "use_case": "Schiffs- und Küstenfunk (nicht Luftfahrt, zur Referenz)"
    },
    {
        "name": "UHF MIL",
        "freq_min": 225.0,
        "freq_max": 400.0,
        "category": "Militär",
        "color": "#f0883e",
        "description": "NATO-Militärfunk (Luftfahrt, taktische Kommunikation). Kanaltrennung: 25 kHz.",
        "protocols": ["AM Voice", "SATURN", "HAVE QUICK II"],
        "use_case": "Militärische Luftfahrtkommunikation (verschlüsselt/frequenzspringend)"
    },
    {
        "name": "DME",
        "freq_min": 960.0,
        "freq_max": 1215.0,
        "category": "Navigation",
        "color": "#58a6ff",
        "description": "Distance Measuring Equipment – Entfernungsmessung zur Bodenstation.",
        "protocols": ["DME Pulse"],
        "use_case": "Ergänzung zu VOR für präzise Positionsbestimmung"
    },
    {
        "name": "ATC Transponder (Mode A/C/S)",
        "freq_min": 1030.0,
        "freq_max": 1030.0,
        "category": "Überwachung",
        "color": "#da3633",
        "description": "Secondary Surveillance Radar (SSR) – Abfrage von Flugsicherung (1030 MHz Downlink, 1090 MHz Uplink).",
        "protocols": ["Mode A/C", "Mode S"],
        "use_case": "Identifikation und Höhenüberwachung von Luftfahrzeugen"
    },
    {
        "name": "ADS-B / Mode S",
        "freq_min": 1090.0,
        "freq_max": 1090.0,
        "category": "Überwachung",
        "color": "#da3633",
        "description": "Automatic Dependent Surveillance-Broadcast – Echtzeit-Positionsdaten.",
        "protocols": ["Mode S Extended Squitter", "ADS-B", "TIS-B", "FIS-B"],
        "use_case": "Kollisionsvermeidung, Flugverkehrsmanagement, Flightradar24"
    },
    {
        "name": "TCAS",
        "freq_min": 1030.0,
        "freq_max": 1090.0,
        "category": "Sicherheit",
        "color": "#bc8cff",
        "description": "Traffic Collision Avoidance System – Airborne Kollisionsvermeidung.",
        "protocols": ["Mode S", "ACAS"],
        "use_case": "Automatische Warnungen bei Kollisionsgefahr"
    },
    {
        "name": "GPS L1",
        "freq_min": 1575.42,
        "freq_max": 1575.42,
        "category": "Navigation",
        "color": "#58a6ff",
        "description": "GPS L1 C/A – Zivile GPS-Signale für Navigation.",
        "protocols": ["C/A Code", "P(Y) Code", "M-Code"],
        "use_case": "Satellitengestützte Positionsbestimmung"
    }
]

# ── Templates ────────────────────────────────────────────────────────────────
INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Avionik-Frequenzplan | SDR Dashboard</title>
    <style>
      body {
        font-family: "Roboto", sans-serif;
        background: #ffffff;
        color: #333333;
        margin: 0;
        padding: 0;
      }
      .container {
        max-width: 1100px;
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
      .filter-bar {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
      }
      .filter-btn {
        background: #bbbbbb;
        border: 1px solid #30363d;
        color: #000000;
        padding: 0.5rem 1rem;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: border-color 0.2s;
      }
      .filter-btn:hover {
        border-color: #808080;
      }
      .filter-btn.active {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      #bandChart {
        width: 100%;
        height: 500px;
      }
      #detailPanel {
        display: none;
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 1.2rem;
        margin-top: 1rem;
      }
      #detailPanel h3 {
        color: #58a6ff;
        margin-top: 0;
        font-size: 1.1rem;
      }
      #detailPanel .detail-row {
        display: grid;
        grid-template-columns: 150px 1fr;
        gap: 0.5rem;
        margin-bottom: 0.6rem;
        font-size: 0.85rem;
      }
      #detailPanel .detail-label {
        color: #8b949e;
        font-weight: bold;
      }
      #detailPanel .detail-value {
        color: #e6edf3;
      }
      .badge {
        display: inline-block;
        background: #21262d;
        color: #58a6ff;
        padding: 0.2rem 0.6rem;
        border-radius: 3px;
        font-size: 0.75rem;
        margin-right: 0.3rem;
        border: 1px solid #30363d;
      }
      .info-box {
        background: #ffffff;
        border-left: 3px solid #555555;
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 3px;
        font-size: 0.85rem;
        color: #333333;
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
          <a href="/stream/">Echtzeit-Signalstream</a>
          <a href="/avionics/" class="x2">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>Avionik-Frequenzplan</h1>
      <p class="sub">
        Flugzeuge nutzen ein komplexes Geflecht von Funkfrequenzen für
        Kommunikation, Navigation und Überwachung. Dieses Modul visualisiert die
        wichtigsten Bänder und erklärt ihre Funktion:
      </p>
      <p class="sub">
        VHF COM (118–136.975 MHz): Sprach-Kommunikation zwischen Piloten und
        Fluglotsen (Air Traffic Control). Modulation: AM (Amplitudenmodulation).
        Kanalabstand: 25 kHz (alt) bzw. 8.33 kHz (neu, Europa). Beispiel:
        Frequenz 121.5 MHz ist die internationale Notfrequenz. Rohde & Schwarz
        SDRs müssen diese Bänder empfangen, dekodieren und mit hoher
        Sprachqualität wiedergeben können.
      </p>
      <p class="sub">
        VHF NAV (108–117.975 MHz): Navigationshilfen wie ILS (Instrument Landing
        System) und VOR (VHF Omnidirectional Range). Diese Systeme senden
        kontinuierliche Signale, die das Flugzeug zur Positionsbestimmung nutzt.
        Modulation: AM + FM (je nach System). Rohde & Schwarz-Geräte testen die
        Empfangsqualität und Dekodiergenauigkeit.
      </p>
      <p class="sub">
        UHF MIL (225–400 MHz): Militärische Luftfahrt-Kommunikation (NATO STANAG
        4246, 4285). Modulation: AM (alt), PSK (neu, verschlüsselt). Diese
        Bänder sind besonders relevant für Rohde & Schwarz-Avionik-Lösungen im
        militärischen Bereich (z.B. Eurofighter, NH90). Anforderung:
        Verschlüsselte Kommunikation, schneller Frequenzwechsel (Frequency
        Hopping), Störfestigkeit.
      </p>
      <p class="sub">
        ATC Transponder (1030 MHz Interrogation / 1090 MHz Response):
        Sekundär-Radar-System. Bodenstationen senden Abfragen auf 1030 MHz,
        Flugzeuge antworten auf 1090 MHz mit Identifikation, Höhe,
        Geschwindigkeit. Modulation: PPM (Pulse Position Modulation). Protokoll:
        Mode A/C (alt), Mode S (neu, adressierbar).
      </p>
      <p class="sub">
        ADS-B (1090 MHz): Automatic Dependent Surveillance – Broadcast.
        Flugzeuge senden automatisch Position, Geschwindigkeit, Flugnummer. Wird
        zunehmend Pflicht weltweit. Modulation: PPM. Protokoll: Mode S Extended
        Squitter. ADS-B ist die Zukunft der Luftraumüberwachung – und Rohde &
        Schwarz baut Testgeräte dafür.
      </p>
      <p class="sub">
        Die interaktive Timeline zeigt alle Bänder auf einer Frequenzachse,
        farblich codiert (COM=Blau, NAV=Grün, MIL=Orange, Transponder=Rot).
        Klick auf ein Band → Detail-Panel mit Protokoll-Info, Modulation,
        Anwendungsbeispielen. Die JSON-Konfiguration ist erweiterbar: Neue
        Bänder (z.B. SATCOM, DME, TCAS) können ohne Code-Änderung hinzugefügt
        werden.
      </p>
      <p class="sub">
        VHF/UHF-Frequenzbänder für Luftfahrt-Kommunikation, Navigation &amp;
        Überwachung (NATO/ICAO)
      </p>

      <div class="info-box">
        <strong>Relevanz für Rohde &amp; Schwarz:</strong> Integration Engineer
        Avionik – Funknavigation, ATC-Kommunikation, Mode S Transponder, ADS-B
        Surveillance. Diese Bänder sind kritisch für Zertifizierung von
        Avionik-Systemen nach DO-160/DO-178 und EMV-Konformität.
      </div>

      <div class="card">
        <h2>Filter nach Kategorie</h2>
        <div class="filter-bar">
          <button class="filter-btn active" onclick="filterBands('all')">
            Alle Bänder
          </button>
          <button class="filter-btn" onclick="filterBands('Navigation')">
            Navigation
          </button>
          <button class="filter-btn" onclick="filterBands('Kommunikation')">
            Kommunikation
          </button>
          <button class="filter-btn" onclick="filterBands('Überwachung')">
            Überwachung
          </button>
          <button class="filter-btn" onclick="filterBands('Militär')">
            Militär
          </button>
          <button class="filter-btn" onclick="filterBands('Sicherheit')">
            Sicherheit
          </button>
        </div>
      </div>

      <div class="card">
        <div id="bandChart"></div>
      </div>

      <div id="detailPanel" class="card">
        <h3 id="detailTitle">Band-Details</h3>
        <div class="detail-row">
          <div class="detail-label">Frequenzbereich:</div>
          <div class="detail-value" id="detailFreq">--</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Kategorie:</div>
          <div class="detail-value" id="detailCategory">--</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Beschreibung:</div>
          <div class="detail-value" id="detailDesc">--</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Protokolle:</div>
          <div class="detail-value" id="detailProtocols">--</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Anwendung:</div>
          <div class="detail-value" id="detailUseCase">--</div>
        </div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script>
      let allBands = [];
      let currentFilter = "all";

      async function loadBands() {
        const res = await fetch("/avionics/bands");
        allBands = await res.json();
        renderChart();
      }

      function filterBands(category) {
        currentFilter = category;
        document
          .querySelectorAll(".filter-btn")
          .forEach((btn) => btn.classList.remove("active"));
        event.target.classList.add("active");
        renderChart();
      }

      function renderChart() {
        const filtered =
          currentFilter === "all"
            ? allBands
            : allBands.filter((b) => b.category === currentFilter);

        // Für Timeline-Chart: Start/Ende pro Band
        const traces = filtered.map((band) => {
          const yPos = band.name;
          const xStart = band.freq_min;
          const xEnd = band.freq_max;

          return {
            x: [xStart, xEnd],
            y: [yPos, yPos],
            mode: "lines+markers",
            type: "scatter",
            line: { color: band.color, width: 12 },
            marker: { size: 8, color: band.color },
            name: band.name,
            hovertemplate: "<b>%{y}</b><br>%{x} MHz<extra></extra>",
            customdata: [band, band],
          };
        });

        const layout = {
          paper_bgcolor: "#999999",
          plot_bgcolor: "#888888",
          font: { color: "#000000", size: 11 },
          xaxis: {
            title: "Frequenz [MHz]",
            gridcolor: "#222222",
            color: "#111111",
            type: "log",
            tickformat: ".0f",
          },
          yaxis: {
            gridcolor: "#222222",
            color: "#111111",
            automargin: true,
          },
          title: {
            text: "Avionik-Frequenzbänder (Klick auf Band für Details)",
            font: { color: "#000000", size: 14 },
          },
          margin: { t: 50, r: 20, b: 60, l: 200 },
          showlegend: false,
          hovermode: "closest",
        };

        const config = { responsive: true, displayModeBar: false };

        Plotly.newPlot("bandChart", traces, layout, config);

        // Click-Handler für Details
        document.getElementById("bandChart").on("plotly_click", (data) => {
          const point = data.points[0];
          if (point && point.customdata) {
            showDetails(point.customdata);
          }
        });
      }

      function showDetails(band) {
        document.getElementById("detailPanel").style.display = "block";
        document.getElementById("detailTitle").textContent = band.name;

        const freqRange =
          band.freq_min === band.freq_max
            ? `${band.freq_min} MHz (Einzelfrequenz)`
            : `${band.freq_min} – ${band.freq_max} MHz`;
        document.getElementById("detailFreq").textContent = freqRange;
        document.getElementById("detailCategory").textContent = band.category;
        document.getElementById("detailDesc").textContent = band.description;

        const protocols = band.protocols
          .map((p) => `<span class="badge">${p}</span>`)
          .join(" ");
        document.getElementById("detailProtocols").innerHTML = protocols;

        document.getElementById("detailUseCase").textContent = band.use_case;

        // Scroll zu Details
        document
          .getElementById("detailPanel")
          .scrollIntoView({ behavior: "smooth", block: "nearest" });
      }

      window.onload = loadBands;
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
@avionics_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

@avionics_bp.route("/bands")
def get_bands():
    return jsonify(AVIONICS_BANDS)
