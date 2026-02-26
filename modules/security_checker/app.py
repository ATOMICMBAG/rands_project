"""
Modul 5: Security / PKI Demo
X.509 Zertifikat-Visualisierung, RSA-Signatur, AES-Verschlüsselung
Verwendet: pyca/cryptography
"""
import base64, os, json, datetime
from flask import Blueprint, render_template_string, request, jsonify

sec_bp = Blueprint("security", __name__)

# ── Krypto-Funktionen ─────────────────────────────────────────────────────────
def rsa_sign_verify(message: str):
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes, serialization
    # Schlüsselpaar generieren (2048 Bit)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key  = private_key.public_key()
    msg_bytes   = message.encode("utf-8")
    # Signieren
    signature   = private_key.sign(msg_bytes, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    sig_b64 = base64.b64encode(signature).decode()
    # Verifizieren
    try:
        public_key.verify(signature, msg_bytes, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        verified = True
    except Exception:
        verified = False
    pub_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return {
        "message":    message,
        "key_size":   2048,
        "algorithm":  "RSA-PSS with SHA-256",
        "signature_b64": sig_b64[:60] + "...",
        "signature_len": len(signature),
        "verified":   verified,
        "public_key_pem": pub_pem[:120] + "...",
    }

def aes_demo(plaintext: str):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    key = os.urandom(32)       # AES-256
    iv  = os.urandom(16)
    data = plaintext.encode("utf-8")
    # Padding auf 16-Byte-Grenze
    pad_len = 16 - (len(data) % 16)
    data_padded = data + bytes([pad_len] * pad_len)
    # Verschlüsseln
    cipher     = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    enc        = cipher.encryptor()
    ciphertext = enc.update(data_padded) + enc.finalize()
    ct_hex     = ciphertext.hex()
    # Entschlüsseln
    dec = cipher.decryptor()
    pt_padded   = dec.update(ciphertext) + dec.finalize()
    pt_unpadded = pt_padded[:-pt_padded[-1]].decode("utf-8")
    return {
        "plaintext":          plaintext,
        "algorithm":          "AES-256-CBC",
        "key_hex":            key.hex()[:32] + "...",
        "iv_hex":             iv.hex(),
        "ciphertext_hex":     ct_hex[:64] + "...",
        "ciphertext_len":     len(ciphertext),
        "decrypted":          pt_unpadded,
        "decryption_success": pt_unpadded == plaintext,
    }

def build_pki_chain():
    """Statische PKI-Chain-Darstellung (ohne echte Zertifikatsgenerierung für Schnelligkeit)"""
    return [
        {"role": "Root CA", "cn": "R&S Demo Root CA", "key": "RSA-4096",
         "valid": "10 Jahre", "self_signed": True,
         "description": "Vertrauensanker. Signiert Intermediate CAs. Offline gehalten."},
        {"role": "Intermediate CA", "cn": "R&S Comm Signing CA",
         "key": "RSA-2048", "valid": "5 Jahre", "self_signed": False,
         "description": "Stellt End-Entity-Zertifikate für Geräte/Dienste aus."},
        {"role": "End-Entity", "cn": "sdr-device-001.rands.local",
         "key": "RSA-2048 / ECDSA-256", "valid": "1 Jahr", "self_signed": False,
         "description": "Gerätezertifikat für SDR-Unit. TLS-Authentifizierung."},
    ]

INDEX_HTML = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Security / PKI Demo | SDR Dashboard</title>
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
      .tabs {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
      }
      .tab {
        background: #bbbbbb;
        border: 1px solid #30363d;
        color: #000000;
        padding: 0.5rem 1rem;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: border-color 0.2s;
      }
      .tab.active {
        border-color: #30363d;
        color: #000000;
        background: #bbbbbb;
        box-shadow: 0px 0px 10px #000000;
      }
      .pane {
        display: none;
      }
      .pane.active {
        display: block;
      }
      input[type="text"] {
        background: #ffffff;
        color: #000000;
        border: 1px solid #30363d;
        border-radius: 3px;
        padding: 0.4rem 0.7rem;
        width: 97%;
        margin-bottom: 0.8rem;
        font-size: 0.9rem;
      }
      button {
        background: #bbbbbb;
        border: 1px solid #30363d;
        color: #000000;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.85rem;
        transition: border-color 0.2s;
      }
      button:hover {
        opacity: 0.85;
        border-color: #808080;
      }
      .kv {
        display: grid;
        grid-template-columns: 200px 1fr;
        gap: 0.3rem 0.5rem;
        font-size: 0.83rem;
        margin-top: 0.5rem;
      }
      .kv .k {
        color: #222222;
      }
      .kv .v {
        color: #111111;
        font-family: monospace;
        word-break: break-all;
      }
      .ok {
        color: #56d364;
      }
      .fail {
        color: #f85149;
      }
      .pki-chain {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      .pki-node {
        background: #999999;
        border-radius: 3px;
        padding: 1rem;
        position: relative;
        border-left: 4px solid;
      }
      .root {
        border-color: #888888;
      }
      .intermediate {
        border-color: #777777;
      }
      .endentity {
        border-color: #666666;
      }
      .pki-role {
        font-weight: bold;
        font-size: 0.85rem;
      }
      .root .pki-role {
        color: #000000;
      }
      .intermediate .pki-role {
        color: #111111;
      }
      .endentity .pki-role {
        color: #222222;
      }
      .pki-cn {
        font-family: monospace;
        font-size: 0.88rem;
        margin: 0.3rem 0;
      }
      .pki-desc {
        font-size: 0.8rem;
        color: #333333;
      }
      .pki-arrow {
        text-align: center;
        color: #333333;
        font-size: 1.3rem;
        line-height: 1;
      }
      #spinner {
        color: #444444;
        font-size: 0.85rem;
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
          <a href="/security/" class="x2">Security / PKI Demo</a>
          <a href="/hw/">Hardware-Interface</a>
          <a href="/stream/">Echtzeit-Signalstream</a>
          <a href="/avionics/">Avionik-Frequenzplan</a>
        </div>
      </nav>
    </header>

    <div class="container">
      <h1>Security / PKI Demo</h1>
      <p class="sub">
        Sichere Funkkommunikation (z.B. militärische SDRs, Behördenfunk)
        benötigt Verschlüsselung (AES), digitale Signaturen (RSA/ECDSA) und eine
        Public-Key-Infrastruktur (PKI) zur Zertifikatsverwaltung. Dieses Modul
        demonstriert alle drei Bausteine:
      </p>
      <p class="sub">
        PKI-Zertifikatskette: Zeigt die typische Hierarchie: Root CA (offline,
        nur für CA-Signaturen), Intermediate CA (stellt Gerätezertifikate aus),
        End-Entity (z.B. SDR-Gerät "sdr-device-001"). Jedes Zertifikat wird von
        der darüberliegenden CA signiert – so entsteht eine Vertrauenskette. Bei
        Rohde & Schwarz sind solche Ketten relevant für: TLS-Authentifizierung
        von Geräten, Code-Signing für Firmware-Updates, und Zertifizierung nach
        Common Criteria (EAL4+).
      </p>
      <p class="sub">
        RSA-Signatur (RSA-PSS mit SHA-256): Eine Nachricht wird mit einem
        privaten Schlüssel signiert, die Signatur kann mit dem öffentlichen
        Schlüssel verifiziert werden. Das beweist: Die Nachricht stammt vom
        Inhaber des privaten Schlüssels und wurde nicht manipuliert. Anwendung:
        Firmware-Authentifizierung, Protokoll-Authentifizierung (z.B.
        NATO-Verfahren).
      </p>
      <p class="sub">
        AES-Verschlüsselung (AES-256-CBC): Symmetrische Verschlüsselung für
        Nutzdaten. Der gleiche Schlüssel wird zum Ver- und Entschlüsseln
        verwendet (im Gegensatz zu RSA: asymmetrisch). AES ist der Standard für
        Datenvertraulichkeit in modernen Funkverfahren. Das Modul zeigt:
        Klartext → Verschlüsselt (Hex) → Entschlüsselt (Klartext). CBC-Modus
        (Cipher Block Chaining) mit Initialization Vector (IV) verhindert, dass
        gleiche Klartexte zu gleichen Geheimtexten führen.
      </p>
      <p class="sub">
        PKI-Zertifikatskette, RSA-Signatur &amp; AES-Verschlüsselung &mdash;
        visualisiert
      </p>

      <div class="card">
        <div class="tabs">
          <div class="tab active" onclick="switchTab('pki')">
            PKI-Zertifikatskette
          </div>
          <div class="tab" onclick="switchTab('rsa')">RSA-Signatur</div>
          <div class="tab" onclick="switchTab('aes')">AES-Verschlüsselung</div>
        </div>

        <!-- PKI Tab -->
        <div class="pane active" id="pane-pki">
          <p style="font-size: 0.85rem; color: #222222; margin-bottom: 1rem">
            Typische PKI-Hierarchie für R&S SDR-Gerätezertifikate (ISO 27001 /
            Common Criteria relevant):
          </p>
          <div class="pki-chain" id="pkiChain"></div>
        </div>

        <!-- RSA Tab -->
        <div class="pane" id="pane-rsa">
          <label style="font-size: 0.85rem; color: #222222"
            >Nachricht signieren:</label
          >
          <input
            type="text"
            id="rsaMsg"
            value="SDR-Gerät authentifiziert: device-001"
          />
          <button onclick="doRSA()">🔏 Signieren &amp; Verifizieren</button>
          <span id="spinner"></span>
          <div id="rsaResult"></div>
        </div>

        <!-- AES Tab -->
        <div class="pane" id="pane-aes">
          <label style="font-size: 0.85rem; color: #222222"
            >Klartext verschlüsseln:</label
          >
          <input
            type="text"
            id="aesMsg"
            value="Geheime Frequenzkonfiguration: 403.500 MHz"
          />
          <button onclick="doAES()">
            🔒 Verschlüsseln &amp; Entschlüsseln
          </button>
          <div id="aesResult"></div>
        </div>
      </div>
    </div>
    <footer>
      <a href="http://maazi.de">maazi.de</a> &bull; Hiring Project
    </footer>
    <script>
      function switchTab(name) {
        document.querySelectorAll(".tab").forEach((t, i) => {
          const names = ["pki", "rsa", "aes"];
          t.classList.toggle("active", names[i] === name);
        });
        document
          .querySelectorAll(".pane")
          .forEach((p) => p.classList.remove("active"));
        document.getElementById("pane-" + name).classList.add("active");
      }

      // PKI-Chain rendern
      async function loadPKI() {
        const res = await fetch("/security/pki_chain");
        const chain = await res.json();
        const classes = ["root", "intermediate", "endentity"];
        const html = chain
          .map((n, i) => {
            const arrow =
              i < chain.length - 1
                ? '<div class="pki-arrow">▼ signiert</div>'
                : "";
            return `<div class="pki-node ${classes[i]}">
      <div class="pki-role">${n.role}</div>
      <div class="pki-cn">${n.cn}</div>
      <div style="font-size:0.78rem;color:#222222;margin:0.2rem 0">
        ${n.key} &bull; Gültig: ${n.valid}
        ${n.self_signed ? ' &bull; <span style="color:#000000;font-weight: bold;">self-signed</span>' : ""}
      </div>
      <div class="pki-desc">${n.description}</div>
    </div>${arrow}`;
          })
          .join("");
        document.getElementById("pkiChain").innerHTML = html;
      }

      async function doRSA() {
        const msg = document.getElementById("rsaMsg").value;
        document.getElementById("spinner").textContent =
          " Generiere RSA-Schlüssel...";
        const res = await fetch("/security/rsa_sign", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg }),
        });
        const d = await res.json();
        document.getElementById("spinner").textContent = "";
        const ok = d.verified
          ? '<span class="ok">✅ Signatur gültig</span>'
          : '<span class="fail">❌ Ungültig</span>';
        document.getElementById("rsaResult").innerHTML = `<div class="kv">
    <div class="k">Algorithmus</div><div class="v">${d.algorithm}</div>
    <div class="k">Schlüssellänge</div><div class="v">${d.key_size} Bit</div>
    <div class="k">Signaturlänge</div><div class="v">${d.signature_len} Bytes</div>
    <div class="k">Signatur (Base64)</div><div class="v">${d.signature_b64}</div>
    <div class="k">Public Key (PEM)</div><div class="v">${d.public_key_pem}</div>
    <div class="k">Verifikation</div><div class="v">${ok}</div>
  </div>`;
      }

      async function doAES() {
        const msg = document.getElementById("aesMsg").value;
        const res = await fetch("/security/aes_demo", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ plaintext: msg }),
        });
        const d = await res.json();
        const ok = d.decryption_success
          ? '<span class="ok">✅ Entschlüsselung erfolgreich</span>'
          : '<span class="fail">❌</span>';
        document.getElementById("aesResult").innerHTML = `<div class="kv">
    <div class="k">Algorithmus</div><div class="v">${d.algorithm}</div>
    <div class="k">Schlüssel (hex, 256 Bit)</div><div class="v">${d.key_hex}</div>
    <div class="k">IV (hex)</div><div class="v">${d.iv_hex}</div>
    <div class="k">Geheimtext (hex)</div><div class="v">${d.ciphertext_hex}</div>
    <div class="k">Geheimtext-Länge</div><div class="v">${d.ciphertext_len} Bytes</div>
    <div class="k">Entschlüsselt</div><div class="v">${d.decrypted}</div>
    <div class="k">Status</div><div class="v">${ok}</div>
  </div>`;
      }

      window.onload = loadPKI;
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

@sec_bp.route("/")
def index():
    return render_template_string(INDEX_HTML)

@sec_bp.route("/pki_chain")
def pki_chain():
    return jsonify(build_pki_chain())

@sec_bp.route("/rsa_sign", methods=["POST"])
def rsa_sign():
    data = request.get_json()
    msg  = data.get("message", "Test") if data else "Test"
    try:
        return jsonify(rsa_sign_verify(msg))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sec_bp.route("/aes_demo", methods=["POST"])
def aes_endpoint():
    data = request.get_json()
    pt   = data.get("plaintext", "Test") if data else "Test"
    try:
        return jsonify(aes_demo(pt))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
