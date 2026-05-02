# NetWatch — Network Traffic Monitoring Platform

A web-based network traffic monitoring and analysis platform built for the Computer Networks course project.

## 📸 Demo

> Run the app and visit `http://localhost:5000` to see the live dashboard.

---

## 🛠 Tech Stack

| Layer     | Technology          |
|-----------|---------------------|
| Backend   | Python 3.10+, Flask |
| Frontend  | HTML5, CSS3, Vanilla JavaScript |
| Dataset   | CSV (50 synthetic traffic records) |
| Fonts     | Share Tech Mono, Exo 2 (Google Fonts) |

---

## 📁 Project Structure

```
network_monitor/
├── app.py                  # Flask backend — all API routes + simulation logic
├── network_traffic.csv     # Dataset (50 synthetic packet records)
├── templates/
│   └── index.html          # Single-page frontend
└── README.md
```

---

## 🚀 Setup & Run

### 1. Install dependencies
```bash
pip install flask
```

### 2. Start the server
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## ✨ Features

- **Start / Stop Monitoring** — Simulates live packet arrival (one packet every ~0.8 s)
- **Packet Table** — Displays all captured packets with full details
- **Filtering** — Filter by Protocol (TCP/UDP/ICMP), Source IP, Destination IP
- **Statistics Panel** — Total packets, per-protocol counts, average packet size
- **Protocol Distribution Bars** — Live visual breakdown of traffic by protocol
- **Top Sources** — Most active source IPs
- **Event Log** — Timestamped log of all captured packets
- **Service Mapping** — Destination port → service name (HTTP, HTTPS, DNS, SSH, etc.)

---

## 📊 Dataset

File: `network_traffic.csv`

| Field            | Example Value  |
|------------------|----------------|
| time             | 10:35:21       |
| source_ip        | 192.168.1.5    |
| destination_ip   | 8.8.8.8        |
| protocol         | TCP            |
| packet_size      | 512            |
| source_port      | 52341          |
| destination_port | 80             |

The dataset contains 50 hand-crafted records representing realistic LAN traffic including web browsing (HTTP/HTTPS), DNS lookups, ICMP pings, and service connections (SSH, FTP, SMTP).

---

## 🔌 API Endpoints

| Method | Endpoint        | Description                          |
|--------|-----------------|--------------------------------------|
| POST   | `/api/start`    | Start packet simulation              |
| POST   | `/api/stop`     | Stop simulation                      |
| GET    | `/api/packets`  | Get packets (supports filter params) |
| GET    | `/api/logs`     | Get event log entries                |
| GET    | `/api/status`   | Get monitoring status                |

### Filter query parameters for `/api/packets`
- `protocol` — `TCP`, `UDP`, or `ICMP`
- `src_ip` — partial match on source IP
- `dst_ip` — partial match on destination IP

---

## 🗺 Port → Service Mapping

| Port | Service     |
|------|-------------|
| 21   | FTP         |
| 22   | SSH         |
| 25   | SMTP        |
| 53   | DNS         |
| 80   | HTTP        |
| 443  | HTTPS       |
| 3306 | MySQL       |
| 3389 | RDP         |

---

## 📌 Notes

- The system uses **CSV-based simulation** (not live packet sniffing) — packets are replayed from the dataset with a delay to simulate real-time capture.
- All filtering is done server-side via the Flask API.
- No external JS frameworks are used — pure HTML/CSS/JS frontend.
