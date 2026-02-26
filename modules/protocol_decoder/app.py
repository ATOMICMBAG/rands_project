"""
Modul 4: Protokoll-Decoder Demo
OSI Layer 2 (Ethernet), Layer 3 (IPv4), Layer 4 (TCP/UDP)
Kein Scapy – reines Python struct-Parsing
"""
import struct, binascii
from flask import Blueprint, render_template_string, request, jsonify

proto_bp = Blueprint("proto", __name__)

# ── Parser ────────────────────────────────────────────────────────────────────
def mac_str(b):
    return ":".join(f"{x:02X}" for x in b)

def parse_ethernet(raw: bytes):
    if len(raw) < 14:
        return None, raw
    dst = mac_str(raw[0:6])
    src = mac_str(raw[6:12])
    etype = struct.unpack("!H", raw[12:14])[0]
    etype_names = {0x0800: "IPv4", 0x0806: "ARP", 0x86DD: "IPv6", 0x8100: "VLAN"}
    return {
        "layer": "Layer 2 – Ethernet",
        "dst_mac":   dst,
        "src_mac":   src,
        "ethertype": f"0x{etype:04X} ({etype_names.get(etype, 'Unknown')})",
        "payload_bytes": len(raw) - 14,
    }, raw[14:], etype

def parse_ipv4(raw: bytes):
    if len(raw) < 20:
        return None, raw, None
    ihl    = (raw[0] & 0x0F) * 4
    tos    = raw[1]
    length = struct.unpack("!H", raw[2:4])[0]
    ttl    = raw[8]
    proto  = raw[9]
    src_ip = ".".join(str(b) for b in raw[12:16])
    dst_ip = ".".join(str(b) for b in raw[16:20])
    proto_names = {6: "TCP", 17: "UDP", 1: "ICMP", 89: "OSPF"}
    flags_raw = struct.unpack("!H", raw[6:8])[0]
    flags = {
        "DF": bool(flags_raw & 0x4000),
        "MF": bool(flags_raw & 0x2000),
    }
    return {
        "layer": "Layer 3 – IPv4",
        "src_ip":    src_ip,
        "dst_ip":    dst_ip,
        "ttl":       ttl,
        "protocol":  f"{proto} ({proto_names.get(proto, 'Unknown')})",
        "length":    length,
        "flags":     f"DF={flags['DF']}, MF={flags['MF']}",
        "tos":       tos,
    }, raw[ihl:], proto

def parse_tcp(raw: bytes):
    if len(raw) < 20:
        return None
    src_port, dst_port = struct.unpack("!HH", raw[0:4])
    seq  = struct.unpack("!I", raw[4:8])[0]
    ack  = struct.unpack("!I", raw[8:12])[0]
    flags_byte = raw[13]
    flags = {
        "FIN": bool(flags_byte & 0x01),
        "SYN": bool(flags_byte & 0x02),
        "RST": bool(flags_byte & 0x04),
        "PSH": bool(flags_byte & 0x08),
        "ACK": bool(flags_byte & 0x10),
        "URG": bool(flags_byte & 0x20),
    }
    active = [k for k, v in flags.items() if v]
    return {
        "layer": "Layer 4 – TCP",
        "src_port": src_port,
        "dst_port": dst_port,
        "seq":      seq,
        "ack":      ack,
        "flags":    ", ".join(active) if active else "none",
        "payload_bytes": max(0, len(raw) - 20),
    }

def parse_udp(raw: bytes):
    if len(raw) < 8:
        return None
    src_port, dst_port, length, checksum = struct.unpack("!HHHH", raw[0:8])
    return {
        "layer": "Layer 4 – UDP",
        "src_port": src_port,
        "dst_port": dst_port,
        "length":   length,
        "checksum": f"0x{checksum:04X}",
        "payload_bytes": max(0, length - 8),
    }

def decode_packet(hex_str: str):
    hex_clean = hex_str.replace(" ", "").replace("\n", "").replace(":", "")
    try:
        raw = binascii.unhexlify(hex_clean)
    except Exception:
        return {"error": "Ungültiger Hex-String"}

    layers = []
    eth, payload, etype = parse_ethernet(raw)
    if eth:
        layers.append(eth)
        if etype == 0x0800:
            ipv4, payload2, proto = parse_ipv4(payload)
            if ipv4:
                layers.append(ipv4)
                if proto == 6:
                    tcp = parse_tcp(payload2)
                    if tcp:
                        layers.append(tcp)
                elif proto == 17:
                    udp = parse_udp(payload2)
                    if udp:
                        layers.append(udp)
    return {"layers": layers, "total_bytes": len(raw)}

# Demo-Pakete
DEMO_PACKETS = {
    "tcp_syn": {
        "label": "TCP SYN (HTTP-Verbindungsaufbau)",
        "hex": (
            "FFFFFFFFFFFF"   # DST MAC (Broadcast)
            "AABBCCDDEEFF"   # SRC MAC
            "0800"           # EtherType: IPv4
            "45000028"       # IP: Version/IHL, TOS, Total Length
            "00010000"       # ID, Flags+FragOffset
            "4006"           # TTL=64, Protocol=TCP
            "0000"           # Checksum (vereinfacht)
            "C0A80101"       # SRC IP: 192.168.1.1
            "C0A80102"       # DST IP: 192.168.1.2
            "C3500050"       # SRC Port: 50000, DST Port: 80 (HTTP)
            "00000001"       # SEQ
            "00000000"       # ACK
            "5002"           # Data Offset + Flags (SYN)
            "FFFF"           # Window
            "0000"           # Checksum
            "0000"           # Urgent Pointer
        )
    },
    "udp_dns": {
        "label": "UDP DNS-Anfrage",
        "hex": (
            "FFFFFFFFFFFF"
            "112233445566"
            "0800"
            "45000035"
            "00020000"
            "4011"
            "0000"
            "C0A80101"
            "08080808"       # DST: 8.8.8.8 (Google DNS)
            "C3510035"       # SRC Port: 50001, DST Port: 53 (DNS)
            "00210000"       # Length=33, Checksum
        )
    }
}

INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Protokoll-Decoder | SDR Dashboard</title>
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
      textarea {
        width: 97%;
        color: #999999;
        min-height: 80px;
        resize: vertical;
        background: #111111;
        border: 1px solid #888888;
        border-radius: 3px;
        padding: 0.8rem;
        font-family: monospace;
        font-size: 0.82rem;
        overflow-y: auto;
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
      .layer-card {
        background: #999999;
        border-radius: 3px;
        padding: 1rem;
        position: relative;
        border-left: 4px solid;
        margin-bottom: 0.5rem;
      }
      .l2 {
        border-color: #888888;
      }
      .l3 {
        border-color: #777777;
      }
      .l4 {
        border-color: #666666;
      }
      .layer-title {
        font-weight: bold;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
      }
      .l2 .layer-title {
        color: #000000;
      }
      .l3 .layer-title {
        color: #111111;
      }
      .l4 .layer-title {
        color: #222222;
      }
      .kv {
        display: grid;
        grid-template-columns: 160px 1fr;
        gap: 0.2rem 0.5rem;
        font-size: 0.83rem;
      }
      .kv .k {
        color: #222222;
      }
      .kv .v {
        color: #222222;
        font-family: monospace;
      }
      .summary {
        background: #999999;
        border-radius: 3px;
        padding: 0.5rem 0.8rem;
        font-size: 0.82rem;
        font-weight: bold;
        color: #111111;
        margin-bottom: 1rem;
      }
      #error {
        color: #f85149;
        font-size: 0.85rem;
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
          <a href="/proto/" class="x2">Protokoll-Decoder</a>
          <a href="/security/">Security / PKI Demo</a>
          <a href="/hw/">Hardware-Interface</a>
          <a href="/stream/">Echtzeit-Signalstream</a>
          <a href="/avionics/">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>Protokoll-Decoder</h1>
      <p class="sub">
        Moderne Kommunikationssysteme arbeiten in Schichten (OSI-Modell): Layer
        2 (Ethernet) transportiert Daten zwischen Geräten im gleichen Netzwerk,
        Layer 3 (IPv4/IPv6) routet über Netzwerkgrenzen hinweg, Layer 4
        (TCP/UDP) stellt Verbindungen her oder sendet zustandslos. Dieses Modul
        dekodiert echte Netzwerkpakete (als Hex-String) und zeigt die
        Header-Felder hierarchisch an: MAC-Adressen, EtherType, IP-Adressen,
        TTL, Protokoll-Flags (TCP SYN/ACK/FIN), Ports usw.
      </p>
      <p class="sub">
        Die Implementierung verwendet reines Python (struct-Modul) – ohne Scapy
        oder andere externe Libraries. Bei Rohde & Schwarz sind solche
        Kenntnisse wichtig für: (1) Protokoll-Implementierung in SDR-Firmware,
        (2) Debugging von Funkübertragungsverfahren, (3) Testautomatisierung
        (Paket-Injektion, Validierung), (4) Compliance-Testing (z.B. NATO
        STANAG, Avionik DO-178).
      </p>
      <p class="sub">
        Das Demo-Paket zeigt einen TCP-SYN-Verbindungsaufbau (Port 80, HTTP) –
        typisch für Netzwerk-Analysen. Die Visualisierung ist bewusst einfach
        gehalten: Layer-Karten mit farblicher Codierung (L2=Orange, L3=Blau,
        L4=Grün) machen die Hierarchie sofort erkennbar.
      </p>
      <p class="sub">
        OSI Layer 2 / 3 / 4 &mdash; Ethernet, IPv4, TCP/UDP Header-Parsing &amp;
        Visualisierung
      </p>

      <div class="card">
        <h2>Hex-Paket eingeben</h2>
        <textarea
          id="hexInput"
          placeholder="Hex-Bytes einfügen (z.B. FFFFFFFFFFFF AABBCCDDEEFF 0800 ...)"
        ></textarea>
        <br />
        <button class="demo" onclick="loadDemo('tcp_syn')">
          ▶ Demo: TCP SYN
        </button>
        <button class="demo" onclick="loadDemo('udp_dns')">
          ▶ Demo: UDP DNS
        </button>
        <button onclick="decode()">Dekodieren</button>
        <div id="error"></div>
      </div>

      <div id="results" style="display: none">
        <div class="card">
          <h2>Dekodiertes Paket</h2>
          <div class="summary" id="summary"></div>
          <div id="layers"></div>
        </div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script>
      const DEMOS = {{ demos|tojson }};
      function loadDemo(key){
        document.getElementById('hexInput').value = DEMOS[key].hex;
        decode();
      }

      async function decode(){
        const hex = document.getElementById('hexInput').value;
        document.getElementById('error').textContent = '';
        const res  = await fetch('/proto/decode', {method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({hex})});
        const data = await res.json();
        if(data.error){ document.getElementById('error').textContent = data.error; return; }
        renderLayers(data);
      }

      function renderLayers(data){
        document.getElementById('results').style.display='block';
        document.getElementById('summary').textContent =
          `Paketgröße: ${data.total_bytes} Bytes  ·  Erkannte Layer: ${data.layers.length}`;
        const colors = {2:'l2',3:'l3',4:'l4'};
        const html = data.layers.map(l=>{
          const n = parseInt(l.layer.match(/\\d+/)[0]);
          const cls = colors[n] || 'l2';
          const fields = Object.entries(l).filter(([k])=>k!=='layer')
            .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('');
          return `<div class="layer-card ${cls}">
            <div class="layer-title">${l.layer}</div>
            <div class="kv">${fields}</div>
          </div>`;
        }).join('');
        document.getElementById('layers').innerHTML = html;
      }
      window.onload = ()=> loadDemo('tcp_syn');
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

@proto_bp.route("/")
def index():
    from flask import render_template_string as rts
    return rts(INDEX_HTML, demos=DEMO_PACKETS)

@proto_bp.route("/decode", methods=["POST"])
def decode():
    data = request.get_json()
    if not data or "hex" not in data:
        return jsonify({"error": "Kein Hex-String"}), 400
    return jsonify(decode_packet(data["hex"]))
