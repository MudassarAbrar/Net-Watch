# NetWatch — Detailed Project Breakdown & Implementation Guide

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Approach](#architecture--approach)
3. [Implementation Details](#implementation-details)
4. [Core Functions Explained](#core-functions-explained)
5. [Live Packet Capturing Mechanism](#live-packet-capturing-mechanism)
6. [Data Storage & Logs](#data-storage--logs)
7. [Complete Workflow](#complete-workflow)
8. [UI/UX Components](#uiux-components)
9. [How to Run & Test](#how-to-run--test)

---

## 1. Project Overview

### What is NetWatch?

NetWatch is a **web-based network traffic monitoring platform** built for a Computer Networks course project. It provides real-time visualization and analysis of network packets using two modes:

- **CSV Simulation Mode**: Replays synthetic network traffic from a CSV file (~0.8 seconds per packet)
- **Live Capture Mode**: Captures real packets from your network interface in real-time

### Key Technologies

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, Flask framework |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Packet Capture** | Scapy library (cross-platform) |
| **Data Source** | CSV dataset (50 synthetic records) for simulation mode |
| **Threading** | Python `threading` module for concurrent packet capture |

---

## 2. Architecture & Approach

### Why This Design?

The project uses a **client-server architecture** with a **single-page application (SPA)** frontend:

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (SPA)                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Frontend (HTML/CSS/JS)                         │   │
│  │  • Dashboard with stats                         │   │
│  │  • Packet table with filtering                  │   │
│  │  • Mode toggle (CSV ↔ Live)                     │   │
│  │  • Event logs                                   │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────▲────────────────────────▲─────────────────┘
               │                        │
         GET/POST                  WebSocket (polling)
               │ /api/start            │
               │ /api/stop             │ Poll every 1s
               │ /api/packets          │
               │ /api/logs             │
               │ /api/set-mode         │
               ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│           Flask Backend (app.py)                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Packet Processing                             │   │
│  │  • CSV Simulation Thread                        │   │
│  │  • Scapy Live Capture Thread                    │   │
│  │  • Thread-safe packet storage (list + lock)     │   │
│  │  • Log aggregation                              │   │
│  │  • Statistics computation                       │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### Two Capture Modes

#### Mode 1: CSV Simulation (Default)
- **Data Source**: `network_traffic.csv` (hand-crafted 50 records)
- **Execution**: Reads CSV → creates dict → appends to `packets` list
- **Timing**: Fixed 0.8-second delay between packets
- **Use Case**: Testing UI without real network, educational demonstrations

#### Mode 2: Live Packet Capture (New Feature)
- **Data Source**: Real network interface packets
- **Library**: Scapy (handles packet parsing across all protocols)
- **Filter**: Captures only IP packets (filters noise)
- **Timing**: Real-time (varies based on network activity)
- **Use Case**: Actual network monitoring, production debugging

---

## 3. Implementation Details

### 3.1 Backend Architecture (`app.py`)

#### **Global State Variables**

```python
monitoring_active = False      # Boolean: is monitoring running?
use_live_capture = True        # Boolean: which mode? (True=Live, False=CSV)
packets = []                   # List[dict]: all captured packets
logs = []                      # List[str]: timestamped log messages
lock = threading.Lock()        # Mutex: prevents race conditions
_sim_thread = None             # Thread: background capture/simulation
_sim_index = 0                 # Int: CSV row index (for cycling)
```

**Why these variables?**
- `monitoring_active`: Controls the infinite loop in both capture modes
- `use_live_capture`: Allows runtime switching between modes
- `packets` & `logs`: In-memory storage (fast access, cleared on each start)
- `lock`: Critical for thread safety (both threads write to `packets`/`logs`)

#### **Port-to-Service Mapping**

```python
PORT_SERVICES = {
    20: "FTP-Data", 21: "FTP", 22: "SSH", 23: "Telnet",
    25: "SMTP",     53: "DNS", 80: "HTTP", 110: "POP3",
    143: "IMAP",   443: "HTTPS", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB",
}
```

**Purpose**: Translates destination port numbers to human-readable service names (e.g., port 443 → HTTPS)

---

### 3.2 Frontend Architecture (`index.html`)

#### **Three Main Sections**

1. **Header** (Navigation & Status)
   - Logo and title
   - Live/Idle status indicator
   - Packet counter

2. **Control Panel** (User Input)
   - Protocol filter dropdown
   - Source IP filter
   - Destination IP filter
   - **NEW: Capture Mode Toggle** (CSV ↔ Live)
   - Filter, Clear, Start, Stop buttons

3. **Dashboard** (Data Visualization)
   - Statistics cards (Total, TCP, UDP, ICMP, Avg Size)
   - Packet capture table
   - Protocol distribution bars
   - Top sources list
   - Event log

---

## 4. Core Functions Explained

### **Backend Core Functions**

#### 1. `load_csv_rows()` → `List[Dict]`

```python
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
```

**What it does**: Reads CSV file and converts string columns to integers, adds service names.

**Why it matters**: 
- Called once on startup (`ALL_ROWS = load_csv_rows()`)
- Caches all data in memory for fast repeated access
- Type conversion prevents errors in filtering/statistics

**Output Example**:
```python
[
  {
    "time": "10:35:21",
    "source_ip": "192.168.1.5",
    "destination_ip": "8.8.8.8",
    "protocol": "TCP",
    "packet_size": 512,
    "source_port": 52341,
    "destination_port": 80,
    "service": "HTTP"
  },
  # ... 49 more records
]
```

---

#### 2. `simulate_traffic()` → `None` (Infinite Thread Loop)

```python
def simulate_traffic():
    global monitoring_active, _sim_index
    while monitoring_active:
        row = ALL_ROWS[_sim_index % len(ALL_ROWS)]  # Cycle through CSV
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
        with lock:  # ← CRITICAL: Lock prevents race conditions
            packets.append(packet)
            logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"Packet #{packet['id']}: {packet['source_ip']} → "
                f"{packet['destination_ip']} | {packet['protocol']} | "
                f"{packet['service']} | {packet['packet_size']} bytes"
            )

        time.sleep(0.8)  # Wait 0.8 seconds before next packet
```

**What it does**: 
- Runs in a daemon thread
- Infinitely cycles through CSV rows
- Appends to `packets` list and `logs` list
- Sleeps 0.8 seconds between packets (simulates real-time)

**Thread Safety**: 
- Uses `with lock:` to ensure only one thread writes at a time
- Prevents data corruption from simultaneous read/write

**Why 0.8 seconds?**
- Gives UI time to render without overwhelming the browser
- Makes it look like real packet arrival

---

#### 3. `capture_live_traffic()` → `None` (Infinite Scapy Loop)

```python
def packet_callback(pkt):
    """Called for EACH packet captured by Scapy"""
    if not monitoring_active:
        return
    
    try:
        if not pkt.haslayer(IP):  # Skip non-IP packets
            return
        
        ip_layer = pkt[IP]
        source_ip = ip_layer.src
        dest_ip = ip_layer.dst
        protocol_name = "Unknown"
        src_port = 0
        dst_port = 0
        
        # Determine protocol and extract ports
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
        
        with lock:  # ← CRITICAL: Thread safety
            packets.append(packet)
            logs.append(f"[...] Packet #{packet['id']}: ...")
    
    except Exception as e:
        with lock:
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ Error: {str(e)}")

def capture_live_traffic():
    """Main function: calls Scapy's sniff() which runs the callback on each packet"""
    global monitoring_active
    try:
        sniff(
            prn=packet_callback,        # Function to call per packet
            filter="ip",                # Only capture IP packets
            store=False,                # Don't store in memory (we handle storage)
            stop_filter=lambda x: not monitoring_active  # Stop when monitoring_active=False
        )
    except PermissionError:
        with lock:
            logs.append(f"[...] ❌ ERROR: Admin/root privileges required for packet capture.")
```

**How Scapy Works**:
1. `sniff()` starts listening on network interface
2. For each packet, calls `packet_callback(pkt)` 
3. Extracts IP layer and checks for TCP/UDP/ICMP
4. Stops when `stop_filter` returns True

**Why callback pattern?**
- Scapy handles all low-level packet reception
- Callback gives us control to process each packet
- More efficient than polling

---

#### 4. `compute_stats(pkt_list)` → `Dict`

```python
def compute_stats(pkt_list: list[dict]) -> dict:
    if not pkt_list:
        return { "total_packets": 0, "protocol_counts": {}, ... }

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
```

**What it does**: 
- Counts occurrences of each protocol, source IP, destination IP, service
- Calculates average packet size
- Returns top 5 of each category

**Used By**: Frontend for dashboard stats and charts

**Example Output**:
```python
{
  "total_packets": 42,
  "protocol_counts": {"TCP": 25, "UDP": 15, "ICMP": 2},
  "avg_packet_size": 512.3,
  "top_sources": [("192.168.1.5", 12), ("192.168.1.10", 8), ...],
  "top_destinations": [("8.8.8.8", 10), ("1.1.1.1", 7), ...],
  "top_services": [("HTTP", 15), ("DNS", 12), ...]
}
```

---

#### 5. API Routes (Flask)

##### `/api/start` (POST)

```python
@app.route("/api/start", methods=["POST"])
def start_monitoring():
    global monitoring_active, _sim_thread, packets, logs, _sim_index
    if monitoring_active:
        return jsonify({"status": "already_running"})

    monitoring_active = True
    packets.clear()
    logs.clear()
    _sim_index = 0

    if use_live_capture:
        logs.append(f"[...] 🟢 Live packet capture started.")
        _sim_thread = threading.Thread(target=capture_live_traffic, daemon=True)
    else:
        logs.append(f"[...] 🔵 CSV simulation started.")
        _sim_thread = threading.Thread(target=simulate_traffic, daemon=True)
    
    _sim_thread.start()
    return jsonify({"status": "started", "mode": "live" if use_live_capture else "simulation"})
```

**What it does**:
1. Checks if already running
2. Sets `monitoring_active = True` (allows threads to loop)
3. Clears previous data
4. Spawns appropriate thread (live or CSV)
5. Returns confirmation to frontend

**Called by**: Frontend "Start" button

---

##### `/api/stop` (POST)

```python
@app.route("/api/stop", methods=["POST"])
def stop_monitoring():
    global monitoring_active
    monitoring_active = False  # ← Signal thread to exit loop
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⏹ Monitoring stopped. {len(packets)} packets.")
    return jsonify({"status": "stopped", "total": len(packets)})
```

**What it does**:
1. Sets `monitoring_active = False`
2. Threads detect this and exit their loops
3. Logs total packet count

**Called by**: Frontend "Stop" button

---

##### `/api/packets` (GET)

```python
@app.route("/api/packets")
def get_packets():
    protocol  = request.args.get("protocol", "").upper()
    src_ip    = request.args.get("src_ip", "").strip()
    dst_ip    = request.args.get("dst_ip", "").strip()

    with lock:
        result = list(packets)  # Snapshot current list

    # Apply filters
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
```

**What it does**:
1. Takes optional query parameters: `protocol`, `src_ip`, `dst_ip`
2. Copies packet list (thread-safe read with lock)
3. Filters packets based on parameters
4. Returns filtered packets + statistics

**Example URL**: `/api/packets?protocol=TCP&src_ip=192.168`

**Called by**: Frontend every 1 second (polling)

---

##### `/api/set-mode` (POST) [NEW]

```python
@app.route("/api/set-mode", methods=["POST"])
def set_mode():
    global use_live_capture, monitoring_active
    if monitoring_active:
        return jsonify({
            "status": "error", 
            "message": "Cannot switch mode while monitoring is active. Stop first."
        }), 400
    
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
```

**What it does**:
1. Checks if monitoring is running (prevents mid-capture mode switch)
2. Updates global `use_live_capture` variable
3. Logs the change

**Called by**: Frontend toggle switch

---

### **Frontend Core Functions**

#### 1. `toggleMode()` 

```javascript
function toggleMode() {
  if (document.getElementById('btn-start').disabled) {
    alert('Cannot switch mode while monitoring is active. Press Stop first.');
    return;
  }
  
  const newMode = currentMode === 'simulation' ? 'live' : 'simulation';
  
  fetch('/api/set-mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: newMode })
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === 'ok') {
      currentMode = newMode;
      updateModeDisplay();
      fetchLogs();
    } else {
      alert('Error: ' + data.message);
    }
  })
  .catch(err => console.error('Mode switch failed:', err));
}
```

**What it does**:
1. Checks if Start button is disabled (means monitoring is running)
2. Toggles mode opposite to current
3. Sends POST request to `/api/set-mode`
4. Updates UI display

**Called by**: Toggle switch in control panel

---

#### 2. `startMonitoring()`

```javascript
function startMonitoring() {
  fetch('/api/start', { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      document.getElementById('btn-start').disabled = true;
      document.getElementById('btn-stop').disabled  = false;
      setLive(true);  // Show "Live" status indicator
      pollTimer = setInterval(() => { fetchData(); fetchLogs(); }, 1000);  // Poll every 1s
    });
}
```

**What it does**:
1. Calls `/api/start` on backend
2. Disables Start button, enables Stop button
3. Activates live status indicator
4. Starts polling API every 1 second

---

#### 3. `fetchData()`

```javascript
function fetchData() {
  const q = new URLSearchParams(filters);
  fetch('/api/packets?' + q)
    .then(r => r.json())
    .then(d => {
      renderTable(d.packets);
      renderStats(d.stats);
      document.getElementById('pkt-count').textContent = d.packets.length;
    });
}
```

**What it does**:
1. Builds query string from filters (protocol, src_ip, dst_ip)
2. Fetches `/api/packets` with filters
3. Passes data to render functions

---

#### 4. `renderTable(pkts)`

```javascript
function renderTable(pkts) {
  const tbody = document.getElementById('tbl-body');
  document.getElementById('tbl-count').textContent = pkts.length + ' records';
  if (!pkts.length) {
    tbody.innerHTML = '<tr><td colspan="9">...empty...</td></tr>';
    return;
  }
  tbody.innerHTML = [...pkts].reverse().map(p =>
    '<tr>' +
    '<td>' + p.id + '</td>' +
    '<td>' + p.time + '</td>' +
    '<td><strong>' + p.source_ip + '</strong></td>' +
    '<td>' + p.destination_ip + '</td>' +
    '<td><span class="chip chip-' + p.protocol.toLowerCase() + '">' + p.protocol + '</span></td>' +
    '<td>' + p.source_port + '</td>' +
    '<td>' + p.destination_port + '</td>' +
    '<td><span class="svc-chip">' + p.service + '</span></td>' +
    '<td><strong>' + p.packet_size + '</strong></td>' +
    '</tr>'
  ).join('');
}
```

**What it does**:
1. Updates row count badge
2. Reverses array (newest packets at top)
3. Maps each packet to table row HTML
4. Inserts into DOM

---

#### 5. `renderStats(s)`

```javascript
function renderStats(s) {
  document.getElementById('s-total').textContent = s.total_packets || 0;
  const pc = s.protocol_counts || {};
  const tcp = pc.TCP || 0, udp = pc.UDP || 0, icmp = pc.ICMP || 0;
  const tot = Math.max(tcp + udp + icmp, 1);
  
  // Update stat cards
  document.getElementById('s-tcp').textContent  = tcp;
  document.getElementById('s-udp').textContent  = udp;
  document.getElementById('s-icmp').textContent = icmp;
  document.getElementById('s-avg').textContent  = s.avg_packet_size || 0;
  
  // Update protocol distribution bars (calculate percentages)
  document.getElementById('bar-tcp').style.width  = (tcp  / tot * 100).toFixed(1) + '%';
  document.getElementById('bar-udp').style.width  = (udp  / tot * 100).toFixed(1) + '%';
  document.getElementById('bar-icmp').style.width = (icmp / tot * 100).toFixed(1) + '%';
  
  // Update top sources list
  const srcs = s.top_sources || [];
  if (!srcs.length) {
    srcDiv.innerHTML = '<div class="empty"><p>No data yet</p></div>';
  } else {
    srcDiv.innerHTML = srcs.map(x => 
      '<div class="ip-row"><span class="ip-addr">' + x[0] + '</span><span class="ip-badge">' + x[1] + '</span></div>'
    ).join('');
  }
}
```

**What it does**:
1. Updates all statistics cards
2. Calculates percentages for protocol bars
3. Renders top sources list

---

## 5. Live Packet Capturing Mechanism

### How Live Capture Works (Step-by-Step)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. USER CLICKS "Start" BUTTON                                 │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Frontend sends POST /api/start                            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Backend:                                                   │
│    - Sets monitoring_active = True                           │
│    - Checks use_live_capture flag                            │
│    - If True: starts capture_live_traffic() thread           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Scapy's sniff() function:                                 │
│    - Initializes raw socket                                  │
│    - Starts listening on network interface                   │
│    - Requires Admin/root privileges                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼ (FOR EACH PACKET CAPTURED)
┌──────────────────────────────────────────────────────────────┐
│ 5. packet_callback(pkt) is called:                           │
│    a. Check if pkt has IP layer (skip if not)               │
│    b. Extract source IP, dest IP                             │
│    c. Check for TCP/UDP/ICMP layer                          │
│    d. Extract source port, dest port (if available)         │
│    e. Look up service name from port                         │
│    f. Calculate packet size                                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Create packet dict:                                       │
│    {                                                          │
│      "id": 1,                                                │
│      "time": "14:32:05",                                     │
│      "source_ip": "192.168.1.100",                          │
│      "destination_ip": "8.8.8.8",                           │
│      "protocol": "TCP",                                      │
│      "packet_size": 1024,                                    │
│      "source_port": 54321,                                   │
│      "destination_port": 443,                                │
│      "service": "HTTPS"                                      │
│    }                                                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. THREAD-SAFE STORAGE (with lock):                         │
│    packets.append(packet_dict)                              │
│    logs.append(timestamped_log_entry)                       │
└──────────────────────┬───────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
┌──────────────────────┐    ┌──────────────────────┐
│ 8a. Frontend polls   │    │ 8b. Each packet      │
│     /api/packets     │    │     added to list    │
│     every 1 second   │    │     instantly        │
│  (not every packet)  │    │                      │
└──────────────────────┘    └──────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│ 9. Frontend receives JSON with filtered packets + stats      │
│    - renderTable() updates packet table                      │
│    - renderStats() updates all cards & charts               │
│    - UI refreshes showing latest packets                     │
└─────────────────────────────────────────────────────────────┘
```

### The Callback Pattern (Why Scapy Works This Way)

```
Without Scapy, you'd need to:
❌ Poll OS socket API continuously
❌ Handle binary packet format manually
❌ Parse Ethernet, IP, TCP/UDP headers yourself
❌ Deal with platform-specific differences

With Scapy:
✅ Scapy handles all the low-level stuff
✅ Calls your callback for each packet
✅ Gives you parsed data (already extracted)
✅ Works on Linux, macOS, Windows
```

### Thread Safety in Live Capture

**Problem**: Two things access `packets` list simultaneously:
- **Scapy thread**: Continuously adding packets
- **Flask thread**: Serving requests to API, reading packets

**Solution**: Mutex Lock

```python
with lock:  # Acquire lock
    packets.append(packet)  # Only one thread at a time in this block
    logs.append(log_msg)
# Lock automatically released at end of `with` block
```

**Without lock**: Race condition → data corruption

---

## 6. Data Storage & Logs

### Where Data is Stored

#### **In-Memory Storage (Temporary)**

```
Python Process Memory
├── packets = [         ← All captured/simulated packets
│   {dict1},
│   {dict2},
│   ...
│ ]
│
└── logs = [            ← All timestamped log entries
    "[14:32:05] ...",
    "[14:32:06] ...",
    ...
  ]
```

**Lifetime**: Only while the Flask app is running
- **Cleared** when clicking Start button
- **Persisted** while monitoring is active
- **Lost** when app restarts or crashes

**Why in-memory?**
- Fast (no disk I/O)
- Simple (no database setup)
- Educational (focuses on networking, not persistence)

#### **CSV Dataset (Read-Only)**

```
File: network_traffic.csv
├─ 50 synthetic network packet records
├─ Read once on startup: ALL_ROWS = load_csv_rows()
└─ Repeated cyclically in simulation mode
```

**Columns**:
- `time` — Time of day (e.g., "10:35:21")
- `source_ip` — Source IP address
- `destination_ip` — Destination IP address
- `protocol` — TCP, UDP, or ICMP
- `packet_size` — Bytes
- `source_port` — Source port number
- `destination_port` — Destination port number

### Log Storage & Retrieval

#### **How Logs Work**

```python
# Every action gets logged
logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✔ Monitoring started.")
logs.append(f"[14:32:05] Packet #1: 192.168.1.5 → 8.8.8.8 | TCP | HTTPS | 512 bytes")
logs.append(f"[14:32:06] Packet #2: ...")
```

#### **API Endpoint for Logs**

```python
@app.route("/api/logs")
def get_logs():
    with lock:
        return jsonify({"logs": list(logs[-100:])})  # Last 100 entries only
```

**Why limit to 100?**
- Prevents browser from displaying huge HTML
- Avoids memory bloat after long sessions
- Frontend shows most recent events anyway

#### **Frontend Log Display**

```javascript
function renderLogs(logs) {
  div.innerHTML = [...logs].reverse().map(function(l, i) {
    var ts = (l.match(/\[(\d+:\d+:\d+)\]/) || ['',''])[1];
    var msg = l.replace(/\[\d+:\d+:\d+\]\s*/, '');
    return '<div class="log-line ' + (i===0?'fresh':'') + '">'
           + '<span class="log-ts">' + ts + '</span> ' + msg 
           + '</div>';
  }).join('');
}
```

**Features**:
- Displays last newest log at top
- Extracts timestamp and highlights it
- Marks newest log as "fresh" (different color)

---

## 7. Complete Workflow

### Workflow A: CSV Simulation Mode

```
START
  │
  ├─→ User clicks "Start" button
  │
  ├─→ Frontend sends: POST /api/start
  │
  ├─→ Backend:
  │   ├─ monitoring_active = True
  │   ├─ packets.clear()
  │   ├─ use_live_capture == False? → Yes
  │   └─ spawn_thread(simulate_traffic)
  │
  ├─→ simulate_traffic() thread does:
  │   Loop while monitoring_active == True:
  │   ├─ row = ALL_ROWS[_sim_index % 50]  ← Get next CSV row (cycles)
  │   ├─ Create packet dict from row
  │   ├─ packets.append(packet)
  │   ├─ logs.append(log_string)
  │   ├─ time.sleep(0.8)  ←Wait 0.8 seconds
  │   └─ End of loop
  │
  ├─→ Frontend polls every 1 second:
  │   ├─ GET /api/packets
  │   ├─ Receives: {packets: [...], stats: {...}, active: true}
  │   ├─ renderTable(packets)  ← Updates table with newest packets
  │   ├─ renderStats(stats)    ← Updates stat cards
  │   └─ Repeat
  │
  ├─→ [During monitoring...]
  │   ├─ 0.0s: Packet 1 appended, sleep 0.8s
  │   ├─ 1.0s: Frontend polls, gets 1 packet
  │   ├─ 0.8s: Packet 2 appended, sleep 0.8s
  │   ├─ 1.6s: Packet 3 appended, sleep 0.8s
  │   ├─ 2.0s: Frontend polls, gets 2-3 packets
  │   └─ ... continues ...
  │
  ├─→ User clicks "Stop" button
  │
  ├─→ Frontend sends: POST /api/stop
  │
  ├─→ Backend:
  │   ├─ monitoring_active = False  ← Signal thread to exit
  │   ├─ Thread exits while loop
  │   └─ logs.append("Monitoring stopped. 42 packets captured.")
  │
  └─→ Frontend:
      ├─ Disables Stop button, enables Start button
      ├─ Stops polling timer
      └─ Shows final stats
```

### Workflow B: Live Packet Capture Mode

```
START
  │
  ├─→ User clicks toggle switch → "Live" mode
  │
  ├─→ Frontend sends: POST /api/set-mode with {"mode": "live"}
  │
  ├─→ Backend:
  │   ├─ monitoring_active == False? → Yes (can switch)
  │   ├─ use_live_capture = True
  │   └─ logs.append("Mode switched to: Live Packet Capture")
  │
  ├─→ User clicks "Start" button
  │
  ├─→ Frontend sends: POST /api/start
  │
  ├─→ Backend:
  │   ├─ monitoring_active = True
  │   ├─ packets.clear()
  │   ├─ use_live_capture == True? → Yes
  │   └─ spawn_thread(capture_live_traffic)
  │
  ├─→ capture_live_traffic() thread does:
  │   ├─ Scapy's sniff(prn=packet_callback, filter="ip") starts
  │   │  └─ Requires Admin/root privileges!
  │   │
  │   └─ FOR EACH PACKET on network:
  │      ├─ packet_callback(raw_packet) called
  │      ├─ Extract IP layer (skip non-IP)
  │      ├─ Check for TCP/UDP/ICMP
  │      ├─ Extract ports, IPs, size
  │      ├─ Look up service name
  │      ├─ Create packet dict
  │      ├─ WITH LOCK: packets.append(packet_dict)
  │      └─ Repeat for next packet
  │
  ├─→ Frontend polls every 1 second:
  │   ├─ GET /api/packets
  │   ├─ Gets packet snapshot (locked copy)
  │   ├─ Filters if user set protocol/IP filters
  │   ├─ Computes stats
  │   └─ Renders in browser
  │
  ├─→ [During monitoring...]
  │   ├─ Packets arrive asynchronously from network
  │   ├─ callback() processes them in real-time
  │   ├─ Frontend updates UI every 1 second
  │   ├─ Might show 5-100+ packets depending on network activity
  │   └─ Real-time capture (not delayed like CSV)
  │
  ├─→ User clicks "Stop" button
  │
  ├─→ Frontend sends: POST /api/stop
  │
  ├─→ Backend:
  │   ├─ monitoring_active = False
  │   ├─ Scapy's stop_filter triggers: not monitoring_active → True
  │   ├─ sniff() exits
  │   ├─ Thread exits
  │   └─ logs.append("Monitoring stopped. X packets captured.")
  │
  └─→ Frontend: Shows final results
```

---

## 8. UI/UX Components

### Control Panel (New Toggle Switch)

```html
<div class="ctrl-grp" style="...">
  <label>Capture Mode</label>
  <div class="mode-toggle" id="mode-toggle" onclick="toggleMode()">
    <div class="toggle-switch" id="toggle-switch">
      <div class="toggle-slider"></div>
    </div>
    <span class="mode-label" id="mode-label">CSV</span>
  </div>
</div>
```

**Visual States**:

```
OFF (CSV Mode):               ON (Live Mode):
┌─────────────┐               ┌─────────────┐
│ ● CSV       │               │       ● Live│
└─────────────┘               └─────────────┘
 ◁━━━━━━━━━━                  ━━━━━━━━━━▷
 Purple.ghost                 Green (#10B981)
```

**JavaScript Handler**:

```javascript
function toggleMode() {
  // Check if monitoring is active
  if (start_button_is_disabled) {
    alert('Stop monitoring first');
    return;
  }
  
  // Toggle mode
  newMode = opposite_of_current_mode;
  
  // Send to backend
  POST /api/set-mode
  
  // Update display
  updateModeDisplay();
}

function updateModeDisplay() {
  if (currentMode === 'live') {
    toggle.classList.add('active');      // Green, slider right
    label.text = 'Live';
  } else {
    toggle.classList.remove('active');   // Purple, slider left
    label.text = 'CSV';
  }
}
```

### Statistics Cards

```
┌────────────────────────────────────────────────────┐
│ 📊 Total | 🔵 TCP | 🟢 UDP | 🟡 ICMP | 📏 Avg Size│
│ 42 pkts  | 25     | 15     | 2      | 512.3 bytes │
└────────────────────────────────────────────────────┘
```

**Updated by**: `renderStats()` function every 1 second

### Packet Table

```
┌─────────────────────────────────────────────────────────────────┐
│ # │ Time     │ Src IP        │ Dst IP    │ Prot│ Src  │ Dst │...│
├─────────────────────────────────────────────────────────────────┤
│42 │ 14:32:15 │ 192.168.1.100 │ 8.8.8.8   │ TCP │ 54   │ 443 │...│
│41 │ 14:32:14 │ 192.168.1.50  │ 1.1.1.1   │ UDP │ 52341│ 53  │...│
│40 │ 14:32:13 │ 192.168.1.5   │ 10.0.0.1  │ICMP │ -    │ -   │...│
└─────────────────────────────────────────────────────────────────┘
```

**Features**:
- Newest packets at top (reversed)
- Color-coded protocol chips
- Service name lookup (443 → HTTPS)
- Scrollable (max-height: 440px)

---

## 9. How to Run & Test

### Prerequisites

```bash
# Check Python version
python --version  # Should be 3.10+

# Check if pip is installed
pip --version
```

### Installation Steps

#### Step 1: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

#### Step 2: Install Dependencies

```bash
pip install -U pip
pip install flask scapy
```

#### Step 3: Setup Files

```bash
# Create templates folder
mkdir templates

# Copy HTML to templates folder
# (On Windows)
copy "index.html" "templates\index.html"
# (On Linux/macOS)
cp index.html templates/index.html

# Verify CSV exists
dir network_traffic.csv        # Windows
ls network_traffic.csv         # Linux/macOS
```

#### Step 4: Start Server

**Windows** (Run as Administrator):

```bash
python app.py
```

**Linux/macOS** (Need sudo for live packet capture):

```bash
sudo python app.py
```

**Output**:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

#### Step 5: Open Browser

Navigate to: **http://localhost:5000**

### Testing CSV Simulation Mode

1. Toggle to "CSV" mode (if not already)
2. Click "Start"
3. Watch packets appear at ~0.8-second intervals
4. Try filtering:
   - Protocol: Select "TCP"
   - Source IP: Type "192.168"
5. Click "Stop"
6. Verify final packet count in logs

### Testing Live Capture Mode

**Windows**:

1. Download & install **Npcap** from: https://nmap.org/npcap/
   - Choose "Install in WinPcap API-compatible Mode"
   - Reboot
2. Run Flask as **Administrator**
3. Toggle to "Live" mode
4. Click "Start"
5. Open browser, visit different websites (generates traffic)
6. Watch packets appear in real-time
7. Filter by destination IP (e.g., "8.8")

**Linux/macOS**:

1. Run Flask with `sudo python app.py`
2. Toggle to "Live" mode
3. Click "Start"
4. In another terminal, generate traffic: `ping google.com`
5. Packets should appear in real-time

---

## 10. Troubleshooting

### Issue: "Module 'scapy' not found"

```bash
pip install scapy
```

### Issue: "Permission denied" on Linux/macOS

```bash
# Need sudo for raw socket access
sudo python app.py
```

### Issue: "Admin privileges required" on Windows

```bash
# Run Command Prompt as Administrator, then:
python app.py
```

### Issue: Toggle button not visible

1. Refresh browser (Ctrl+F5)
2. Check if file is in `templates/index.html`
3. Check console (F12) for errors

### Issue: No packets appearing in Live mode

1. Verify you're running as Admin/sudo
2. Check if Npcap/Wireshark is installed (Windows)
3. Try filtering: `/api/packets?protocol=TCP`
4. Open another tab, visit a website to generate traffic

---

## Summary

**NetWatch** is a dual-mode packet monitoring system:

| Aspect | CSV Mode | Live Mode |
|--------|----------|-----------|
| **Data Source** | Synthetic CSV | Real network |
| **Speed** | 0.8s/packet | Real-time |
| **Permissions** | None | Admin/root |
| **Use Case** | Testing/demo | Production |
| **Implementation** | CSV reader | Scapy callback |
| **Threading** | Simulation loop | Callback loop |
|**Storage** | In-memory | In-memory |

The new **toggle feature** allows runtime switching between modes without restarting the application, providing flexibility for both educational demonstrations and real-time network analysis.

