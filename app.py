from flask import Flask, jsonify, request, render_template
from scapy.all import sniff, IP, TCP, UDP, ICMP
import csv
import os
import time
import threading
from datetime import datetime
from collections import defaultdict
import socket

app = Flask(__name__)

# ─── State ────────────────────────────────────────────────────────────────────
monitoring_active = False
use_live_capture = True  # Toggle: True = live sniffing, False = CSV simulation
packets = []
logs = []
lock = threading.Lock()
_sim_thread = None
_sim_index = 0

# ─── Port → Service mapping ───────────────────────────────────────────────────
PORT_SERVICES = {
    20: "FTP-Data", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP",     53: "DNS", 80: "HTTP", 110: "POP3",
    143: "IMAP",   443: "HTTPS", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB",
}

def get_service(dst_port: int) -> str:
    try:
        return PORT_SERVICES.get(int(dst_port), f"Port {dst_port}")
    except (ValueError, TypeError):
        return "Unknown"

def get_local_ip():
    """Get local machine IP (to filter out own traffic if needed)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ─── CSV dataset loader ───────────────────────────────────────────────────────
def load_csv_rows() -> list[dict]:
    csv_path = os.path.join(os.path.dirname(__file__), "network_traffic.csv")
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["destination_port"] = int(row.get("destination_port", 0))
            row["source_port"]      = int(row.get("source_port", 0))
            row["packet_size"]      = int(row.get("packet_size", 0))
            row["service"]          = get_service(row["destination_port"])
            rows.append(row)
    return rows

ALL_ROWS = load_csv_rows()

# ─── Live packet capture callback ─────────────────────────────────────────────
def packet_callback(pkt):
    """Called for each captured packet."""
    if not monitoring_active:
        return
    
    try:
        # Extract IP layer
        if not pkt.haslayer(IP):
            return
        
        ip_layer = pkt[IP]
        source_ip = ip_layer.src
        dest_ip = ip_layer.dst
        protocol_name = "Unknown"
        src_port = 0
        dst_port = 0
        
        # Determine protocol and ports
        if pkt.haslayer(TCP):
            protocol_name = "TCP"
            src_port = pkt[TCP].sport
            dst_port = pkt[TCP].dport
        elif pkt.haslayer(UDP):
            protocol_name = "UDP"
            src_port = pkt[UDP].sport
            dst_port = pkt[UDP].dport
        elif pkt.haslayer(ICMP):
            protocol_name = "ICMP"
        else:
            return
        
        packet_size = len(pkt)
        service = get_service(dst_port)
        
        packet = {
            "id": len(packets) + 1,
            "time": datetime.now().strftime("%H:%M:%S"),
            "source_ip": source_ip,
            "destination_ip": dest_ip,
            "protocol": protocol_name,
            "packet_size": packet_size,
            "source_port": src_port,
            "destination_port": dst_port,
            "service": service,
        }
        
        with lock:
            packets.append(packet)
            logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Packet #{packet['id']}: {source_ip} → "
                f"{dest_ip} | {protocol_name} | "
                f"{service} | {packet_size} bytes"
            )
    except Exception as e:
        with lock:
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ Error parsing packet: {str(e)}")

# ─── Live capture thread ──────────────────────────────────────────────────────
def capture_live_traffic():
    """Sniff live packets from network interface."""
    global monitoring_active
    try:
        # Sniff on all interfaces, filtering for IP packets
        sniff(
            prn=packet_callback,
            filter="ip",
            store=False,
            stop_filter=lambda x: not monitoring_active
        )
    except PermissionError:
        with lock:
            logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                "❌ ERROR: Admin/root privileges required for packet capture. "
                "(Run as Administrator on Windows or use sudo on Linux/macOS)"
            )

# ─── CSV simulation thread (fallback) ─────────────────────────────────────────
def simulate_traffic():
    """Fallback: replay traffic from CSV."""
    global monitoring_active, _sim_index
    while monitoring_active:
        row = ALL_ROWS[_sim_index % len(ALL_ROWS)]
        _sim_index += 1

        packet = {
            "id": len(packets) + 1,
            "time": row["time"],
            "source_ip": row["source_ip"],
            "destination_ip": row["destination_ip"],
            "protocol": row["protocol"],
            "packet_size": row["packet_size"],
            "source_port": row["source_port"],
            "destination_port": row["destination_port"],
            "service": row["service"],
        }
        with lock:
            packets.append(packet)
            logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Packet #{packet['id']}: {packet['source_ip']} → "
                f"{packet['destination_ip']} | {packet['protocol']} | "
                f"{packet['service']} | {packet['packet_size']} bytes"
            )
        time.sleep(0.8)

# ─── Statistics helper ────────────────────────────────────────────────────────
def compute_stats(pkt_list: list[dict]) -> dict:
    if not pkt_list:
        return {
            "total_packets": 0,
            "protocol_counts": {},
            "avg_packet_size": 0,
            "top_sources": [],
            "top_destinations": [],
            "top_services": [],
        }

    protocol_counts = defaultdict(int)
    src_counts      = defaultdict(int)
    dst_counts      = defaultdict(int)
    svc_counts      = defaultdict(int)
    total_bytes     = 0

    for p in pkt_list:
        protocol_counts[p["protocol"]]        += 1
        src_counts[p["source_ip"]]            += 1
        dst_counts[p["destination_ip"]]       += 1
        svc_counts[p["service"]]              += 1
        total_bytes                           += p["packet_size"]

    return {
        "total_packets":   len(pkt_list),
        "protocol_counts": dict(protocol_counts),
        "avg_packet_size": round(total_bytes / len(pkt_list), 2),
        "top_sources":     sorted(src_counts.items(), key=lambda x: -x[1])[:5],
        "top_destinations": sorted(dst_counts.items(), key=lambda x: -x[1])[:5],
        "top_services":    sorted(svc_counts.items(), key=lambda x: -x[1])[:5],
    }

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def start_monitoring():
    global monitoring_active, _sim_thread, packets, logs, _sim_index
    if monitoring_active:
        return jsonify({"status": "already_running"})

    monitoring_active = True
    packets.clear()
    logs.clear()
    _sim_index = 0

    # Choose capture method
    if use_live_capture:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 Live packet capture started.")
        _sim_thread = threading.Thread(target=capture_live_traffic, daemon=True)
    else:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔵 CSV simulation started.")
        _sim_thread = threading.Thread(target=simulate_traffic, daemon=True)
    
    _sim_thread.start()
    return jsonify({"status": "started", "mode": "live" if use_live_capture else "simulation"})

@app.route("/api/stop", methods=["POST"])
def stop_monitoring():
    global monitoring_active
    monitoring_active = False
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹ Monitoring stopped. "
                f"{len(packets)} packets captured.")
    return jsonify({"status": "stopped", "total": len(packets)})

@app.route("/api/set-mode", methods=["POST"])
def set_mode():
    global use_live_capture, monitoring_active
    if monitoring_active:
        return jsonify({"status": "error", "message": "Cannot switch mode while monitoring is active. Stop first."}), 400
    
    data = request.get_json()
    mode = data.get("mode", "simulation")
    
    if mode == "live":
        use_live_capture = True
        msg = "✅ Mode switched to: Live Packet Capture"
    else:
        use_live_capture = False
        msg = "✅ Mode switched to: CSV Simulation"
    
    with lock:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    return jsonify({"status": "ok", "mode": mode, "message": msg})

@app.route("/api/packets")
def get_packets():
    protocol  = request.args.get("protocol", "").upper()
    src_ip    = request.args.get("src_ip", "").strip()
    dst_ip    = request.args.get("dst_ip", "").strip()

    with lock:
        result = list(packets)

    if protocol:
        result = [p for p in result if p["protocol"] == protocol]
    if src_ip:
        result = [p for p in result if src_ip in p["source_ip"]]
    if dst_ip:
        result = [p for p in result if dst_ip in p["destination_ip"]]

    return jsonify({
        "packets":  result,
        "stats":    compute_stats(result),
        "active":   monitoring_active,
    })

@app.route("/api/logs")
def get_logs():
    with lock:
        return jsonify({"logs": list(logs[-100:])})

@app.route("/api/status")
def status():
    return jsonify({"active": monitoring_active, "total": len(packets), "mode": "live" if use_live_capture else "simulation"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
