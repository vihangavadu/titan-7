# Kill Switch & Forensic Protection — Emergency Protocols & Evidence Destruction

## Core Modules: `kill_switch.py` (789 lines), `forensic_cleaner.py`, `forensic_synthesis_engine.py`, `immutable_os.py`

These modules handle the worst-case scenario: when an antifraud system detects the session. The kill switch executes a sub-500ms panic sequence that destroys all evidence and rotates all identifiers before the antifraud system can exfiltrate session data.

---

## 1. Kill Switch (`kill_switch.py`)

### Threat Level System

The kill switch operates on a four-level threat assessment:

| Level | Score Range | Meaning | Action |
|-------|------------|---------|--------|
| **GREEN** | 90-100 | No detection signals | Continue normally |
| **YELLOW** | 85-89 | Elevated risk | Continue with caution, prepare for panic |
| **ORANGE** | 75-84 | Pre-detection signals | Warning logged, operator should finish quickly |
| **RED** | <75 | Active detection | **AUTOMATIC PANIC SEQUENCE** |

### Panic Triggers

The kill switch monitors for these trigger conditions:

```python
class PanicReason(Enum):
    FRAUD_SCORE_DROP = "fraud_score_drop"          # Score dropped below threshold
    MANUAL_TRIGGER = "manual_trigger"              # Operator pressed panic button
    BROWSER_CHALLENGE = "browser_challenge"        # Unexpected security challenge
    IP_FLAGGED = "ip_flagged"                      # Proxy IP got blacklisted
    DEVICE_FINGERPRINT_MISMATCH = "device_fp_mismatch"  # Fingerprint changed mid-session
    THREE_DS_AGGRESSIVE = "3ds_aggressive"         # Aggressive 3DS challenge
    SESSION_TIMEOUT = "session_timeout"            # Session exceeded safe duration
```

### Panic Sequence (Sub-500ms)

When triggered, the following actions execute in rapid sequence:

```
Step 0: NETWORK SEVER (nftables DROP all outbound)     ~50ms
  → Blocks ALL outbound traffic immediately
  → Prevents antifraud SDK from sending detection data back to server
  → Uses nftables: "nft add chain inet titan_panic output { policy drop }"
  → Fallback: iptables -I OUTPUT -j DROP

Step 1: BROWSER KILL                                    ~30ms
  → Kills all browser processes (camoufox, firefox, chromium)
  → Uses SIGKILL (immediate, no graceful shutdown)
  → subprocess.run(["pkill", "-9", "-f", "camoufox|firefox"])

Step 2: HARDWARE ID FLUSH                               ~100ms
  → Sends new random hardware profile via Netlink to kernel module
  → CPU model, serial number, UUID all randomized
  → Next session will have completely different hardware identity

Step 3: SESSION DATA CLEAR                              ~80ms
  → Deletes browser profile directory
  → Clears /tmp of any session artifacts
  → Removes cookies, localStorage, cache, history
  → Overwrites with random data before deletion (anti-forensic)

Step 4: PROXY ROTATE                                    ~150ms
  → Disconnects current proxy connection
  → Requests new IP from residential proxy provider
  → New session will have different IP address

Step 5: MAC RANDOMIZE (optional, requires root)         ~50ms
  → Changes network interface MAC address
  → macchanger -r eth0
  → Prevents MAC-based tracking

Step 6: CUSTOM CALLBACK                                 ~10ms
  → Calls operator-defined callback function
  → Can trigger additional cleanup, notifications, etc.

TOTAL: ~470ms (under 500ms target)
```

### Network Sever Detail

The network sever is Step 0 (executed FIRST) because it's the most critical. When an antifraud system detects fraud, it tries to:
1. Send the detection event to its server
2. Log the device fingerprint for future blocking
3. Report the session to the merchant

By severing the network BEFORE killing the browser, we prevent any of this data from leaving the machine. The antifraud SDK's detection event dies in the browser process without ever reaching the server.

```python
def _sever_network(self) -> bool:
    # nftables (preferred on Debian 12)
    nft_rules = [
        "nft add table inet titan_panic",
        "nft add chain inet titan_panic output { type filter hook output priority 0 ; policy drop ; }",
        "nft add rule inet titan_panic output ct state established accept",
    ]
    # Only allows established connections (so SSH stays alive)
    # All NEW outbound connections are dropped
```

### Monitoring Loop

The kill switch runs a background daemon thread that checks for detection signals every 500ms:

```python
def _monitor_loop(self):
    while not self._stop_event.is_set():
        # Check fraud score file (written by TX Monitor extension)
        score = self._read_fraud_score()
        if score < self.config.fraud_score_threshold:
            self.panic(PanicReason.FRAUD_SCORE_DROP, score)
            return
        
        # Check for manual kill signal file
        if self._signal_file.exists():
            self.panic(PanicReason.MANUAL_TRIGGER)
            return
        
        self._stop_event.wait(0.5)  # 500ms interval
```

### Panic Event Logging

Every panic event is logged for post-mortem analysis:

```python
@dataclass
class PanicEvent:
    timestamp: str              # When it happened
    reason: PanicReason         # What triggered it
    fraud_score: Optional[int]  # Score at time of panic
    threat_level: ThreatLevel   # Threat level at time
    profile_uuid: str           # Which profile was active
    actions_taken: List[str]    # What actions were executed
    duration_ms: float          # How long the sequence took
```

---

## 2. Forensic Cleaner (`forensic_cleaner.py`)

### What It Cleans

After an operation (successful or not), the forensic cleaner removes all traces:

| Artifact | Location | Cleaning Method |
|----------|----------|----------------|
| Browser profile | `/opt/titan/profiles/` | Overwrite with random data, then delete |
| Browser cache | `~/.cache/camoufox/` | Recursive delete |
| Temporary files | `/tmp/titan_*` | Secure delete |
| Log files | `/opt/titan/state/*.log` | Overwrite + delete |
| State files | `/opt/titan/state/*.json` | Overwrite + delete |
| Bash history | `~/.bash_history` | Truncate |
| Python bytecode | `__pycache__/` | Recursive delete |
| Core dumps | `/var/crash/` | Delete if any |
| Swap space | `/dev/swap` | Not cleaned (use encrypted swap) |

### Secure Deletion

Simple `rm` doesn't actually erase data — it just removes the directory entry. The data remains on disk until overwritten. The forensic cleaner uses secure deletion:

```python
def clean_profile(profile_path):
    """
    Securely delete a browser profile:
    1. Overwrite all files with random data
    2. Rename files to random names (hides original filenames)
    3. Delete the randomized files
    4. Remove empty directories
    """
    for file in profile_path.rglob('*'):
        if file.is_file():
            # Overwrite with random data
            size = file.stat().st_size
            with open(file, 'wb') as f:
                f.write(secrets.token_bytes(size))
            # Rename to random name
            random_name = file.parent / secrets.token_hex(8)
            file.rename(random_name)
            # Delete
            random_name.unlink()
```

---

## 3. Immutable OS (`immutable_os.py`)

### A/B Partition Scheme

TITAN supports an A/B partition layout where:
- **Partition A**: Clean, pristine OS image (read-only)
- **Partition B**: Working partition where operations happen

After each operation:
1. Forensic cleaner runs on Partition B
2. System reboots into Partition A
3. Partition B is reformatted from the clean image
4. Next operation starts on a fresh Partition B

This ensures that even if forensic analysis is performed on the disk, Partition A contains no operational artifacts.

### OverlayFS Mode

For lighter-weight isolation, TITAN can use OverlayFS:
- Root filesystem mounted read-only
- All writes go to a RAM-backed overlay
- On reboot, all changes disappear

```python
class ImmutableOS:
    def enable_overlay(self):
        """
        Mount root as read-only with RAM overlay.
        All changes are lost on reboot.
        """
        # mount -t overlay overlay -o lowerdir=/,upperdir=/tmp/upper,workdir=/tmp/work /mnt/overlay
```

---

## 4. Forensic Synthesis Engine (`forensic_synthesis_engine.py`)

### Anti-Forensic Countermeasures

Beyond cleaning, TITAN can plant false forensic trails:

- **Fake browsing history**: Plant innocent browsing history (news, weather, social media)
- **Fake timestamps**: Modify file timestamps to show normal usage patterns
- **Fake user activity**: Generate login/logout events in system logs
- **Decoy profiles**: Create innocent-looking browser profiles

This makes forensic analysis inconclusive — the investigator finds "normal" user activity rather than a clean-wiped system (which itself is suspicious).

---

## 5. Core Dump Prevention

```bash
# /etc/sysctl.d/99-titan.conf
kernel.core_pattern=|/bin/false    # Redirect core dumps to /dev/null
```

Core dumps can contain sensitive data (card numbers, passwords, session tokens). By redirecting them to `/bin/false`, no core dump files are ever created.

---

## 6. Encrypted Swap

If swap is enabled, it should be encrypted to prevent forensic recovery of memory contents:

```bash
# /etc/crypttab
swap /dev/sda2 /dev/urandom swap,cipher=aes-xts-plain64,size=256
```

This encrypts swap with a random key on each boot — previous swap contents are unrecoverable.

---

## Integration Flow

```
Operation Running
    ↓
TX Monitor detects fraud score drop (score < 85)
    ↓
Writes to /opt/titan/state/fraud_score.json
    ↓
Kill Switch daemon reads file (every 500ms)
    ↓
PANIC SEQUENCE (sub-500ms)
    ├── Network SEVERED
    ├── Browser KILLED
    ├── Hardware ID FLUSHED
    ├── Session CLEARED
    ├── Proxy ROTATED
    └── MAC RANDOMIZED
    ↓
Forensic Cleaner runs
    ├── Profile overwritten + deleted
    ├── Cache cleared
    ├── Logs purged
    └── State files removed
    ↓
System ready for next operation with:
    ├── New hardware identity
    ├── New IP address
    ├── New MAC address
    ├── Clean filesystem
    └── No forensic traces
```
