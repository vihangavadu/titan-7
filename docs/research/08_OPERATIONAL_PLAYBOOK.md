# Operational Playbook — Real-World Operator Workflow

## How a Human Operator Uses TITAN OS for Successful Operations

This document describes the complete end-to-end workflow from VPS login to successful purchase, including the critical "Handover Protocol" where automation hands off to the human operator.

---

## The Fundamental Principle: Human-in-the-Loop

TITAN is NOT a bot. It is an **augmentation system** that prepares everything for a human operator to execute manually. This is critical because:

1. **`navigator.webdriver = false`**: Only a manually-launched browser clears this flag
2. **Cognitive non-determinism**: Humans introduce natural chaos that no bot can replicate
3. **Adaptive decision-making**: Humans handle unexpected UI changes, CAPTCHAs, and 3DS challenges
4. **Organic navigation**: Humans naturally search Google → click result → browse → buy (not direct URL)

The automated system achieves 95% of the preparation. The human operator delivers the final 5% that makes the difference between success and detection.

---

## Phase 1: Pre-Operation Setup (One-Time)

### 1.1 RDP into VPS
```
Connection: 72.62.72.48:3389
User: root
Desktop: XFCE with dark cyberpunk theme
```

### 1.2 Configure API Keys
Double-click "Edit API Keys" desktop shortcut → edit `/opt/titan/config/titan.env`:
```bash
# Residential proxy (REQUIRED)
PROXY_HOST=gate.smartproxy.com
PROXY_PORT=7777
PROXY_USER=your_username
PROXY_PASS=your_password

# Cloud AI (optional, improves CAPTCHA solving)
TITAN_CLOUD_URL=https://your-vllm-server.com/v1
TITAN_API_KEY=your_key
TITAN_MODEL=meta-llama/Meta-Llama-3-70B-Instruct
```

### 1.3 Verify System Readiness
Launch "Titan Operation Center" → Preflight tab → Run All Checks:
- ✅ Kernel module loaded
- ✅ TTL = 128
- ✅ Timezone matches target
- ✅ DNS clean (no ISP leak)
- ✅ 0 Linux fonts visible
- ✅ Proxy connected
- ✅ Camoufox installed

---

## Phase 2: Profile Forging (Genesis)

### 2.1 Select Target
In the Operation Center or Genesis app:
- Choose target merchant (e.g., "Amazon US", "Steam", "Nike")
- Each target has pre-configured settings (browser preference, antifraud systems, difficulty)

### 2.2 Enter Persona Details
```
Name: John Michael Davis
Email: jmdavis1987@gmail.com
Address: 4521 Oak Ridge Drive, Austin, TX 78745
Phone: (512) 555-0147
```

### 2.3 Configure Profile
- **Age**: 90-180 days (older = more trust, but takes longer to generate)
- **Archetype**: Professional (matches the persona's apparent lifestyle)
- **Hardware profile**: US Windows Desktop (i7-13700K, 32GB RAM)

### 2.4 Forge Profile
Click "Forge Profile" → Genesis Engine creates:
- 5,000+ browsing history entries with circadian rhythm
- 800+ cookies including trust anchors (Google, Facebook, Amazon)
- localStorage entries for major websites
- Hardware fingerprint configuration
- Purchase history on target merchant (synthetic past orders)
- Location configuration (GPS, timezone, locale aligned to Austin, TX)

**Profile size**: ~700MB (matching a real 6-month-old browser profile)

### 2.5 Inject Purchase History
The Purchase History Engine adds synthetic past purchases:
```
Day -120: Phone case ($14.99) — small, low-risk
Day -90:  Bluetooth speaker ($34.99) — medium
Day -60:  Running shoes ($89.99) — establishes category
Day -30:  Wireless earbuds ($49.99) — regular customer pattern
Day -14:  Cart abandonment (added items, didn't buy)
Day -7:   Wishlist activity
```

This transforms the profile from "first-time buyer" (40% decline rate) to "returning customer" (5% decline rate).

---

## Phase 3: Card Validation (Cerberus)

### 3.1 Validate Card
Enter card number → Cerberus performs:
- Luhn checksum validation
- BIN lookup (bank, type, level, country)
- Card quality grading (A+ through F)
- AVS recommendation

### 3.2 Assess Risk
Cerberus calculates risk score based on:
- Card type (credit > debit > prepaid)
- Card level (Platinum/Signature = lower risk)
- Geo match (card country vs merchant country)
- BIN reputation (known decline rates)

### 3.3 Select Strategy
Based on card quality and target difficulty:
- **Grade A + Easy target**: Direct checkout, high confidence
- **Grade B + Medium target**: Warmup browsing first, then checkout
- **Grade C + Hard target**: Extended warmup, small purchase first, then target purchase
- **Grade D/F**: Consider different card or easier target

---

## Phase 4: The Handover Protocol

### Module: `handover_protocol.py` (711 lines)

This is the most critical phase. The automated system has prepared everything; now it hands control to the human operator.

### 4.1 GENESIS Phase (Automated)
- Profile forged ✅
- Card validated ✅
- Proxy configured ✅
- Hardware profile loaded ✅
- Kill switch armed ✅

### 4.2 FREEZE Phase (Transition)
```
[HANDOVER] Terminating all automation...
[HANDOVER] Closing headless browser instances...
[HANDOVER] Flushing automation artifacts...
[HANDOVER] Profile ready for manual operation
[HANDOVER] *** FREEZE COMPLETE — AWAITING OPERATOR ***
```

All automation stops. No scripts running. No headless browsers. The profile directory is ready for a clean manual browser launch.

### 4.3 HANDOVER Phase (Manual Operation)

The operator launches Camoufox with the forged profile:
```bash
/opt/titan/bin/titan-browser --profile /opt/titan/profiles/titan_30de2ac0af15
```

Camoufox opens with:
- All cookies pre-loaded (appears as returning visitor)
- Hardware fingerprint configured (reports Dell XPS desktop)
- Proxy connected (residential IP in Austin, TX)
- Ghost Motor extension active (humanizes all interactions)
- TX Monitor extension active (watches for fraud signals)

### 4.4 Operator Browsing Workflow

The operator follows a natural browsing pattern:

```
Step 1: Google Search
  → Search "amazon electronics deals" (not direct URL)
  → Click organic result (establishes referrer chain)
  → Time: 5-10 seconds

Step 2: Browse Amazon
  → Land on Amazon homepage
  → Scroll through deals (Ghost Motor humanizes scroll)
  → Time: 15-30 seconds

Step 3: Search for Product
  → Use Amazon search bar
  → Type product name naturally (Ghost Motor humanizes typing)
  → Browse 2-3 results
  → Time: 30-60 seconds

Step 4: Product Page
  → Read product details (scroll naturally)
  → Check reviews (scroll down)
  → Select options (size, color)
  → Add to cart
  → Time: 30-60 seconds

Step 5: Cart Review
  → Review cart
  → Maybe continue shopping (adds realism)
  → Proceed to checkout
  → Time: 10-20 seconds

Step 6: Checkout
  → Select shipping address (pre-filled from profile)
  → Select payment method
  → Enter card details (type naturally, Ghost Motor active)
  → Review order
  → Place order
  → Time: 60-120 seconds

Total session: 3-5 minutes of natural browsing before purchase
```

### Why This Works

Antifraud systems see:
- ✅ Returning customer (purchase history)
- ✅ Aged browser profile (6+ months of history)
- ✅ Natural referrer chain (Google → Amazon)
- ✅ Human behavioral patterns (Ghost Motor)
- ✅ Consistent device fingerprint (same as previous visits)
- ✅ Geographic consistency (IP, timezone, billing all match)
- ✅ Natural session duration (3-5 minutes, not instant checkout)
- ✅ Windows desktop (hardware shield + font sanitization)
- ✅ Real residential IP (proxy)

---

## Phase 5: Post-Operation

### 5.1 Success Path
- Order confirmed → screenshot for records
- Disarm kill switch
- Save profile for future use on same merchant
- Clean forensic traces (optional)

### 5.2 Decline Path
- Kill switch may auto-trigger if fraud score drops
- If manual decline: note the reason
- Cerberus analyzes decline code
- Adjust strategy (different card, different approach)
- Wait cooldown period before retry

### 5.3 3DS Challenge Path
- If 3DS challenge appears: requires cardholder's OTP
- TX Monitor detects 3DS iframe
- Operator enters OTP if available
- If no OTP access: abort and try different card

---

## Referrer Warmup Strategy

### Module: `referrer_warmup.py`

Before visiting the target merchant, the operator builds a natural referrer chain:

```
Google.com (search) → Blog article about product → Target merchant
```

This is critical because antifraud systems check the `Referer` header. Direct navigation to checkout (no referrer) is a strong fraud signal. A natural referrer chain from Google search → organic result → merchant looks like genuine shopping behavior.

### Warmup Plan Generation

```python
class ReferrerWarmup:
    def create_warmup_plan(self, target_domain, persona):
        """
        Generate a warmup browsing plan:
        1. Google search for product category
        2. Visit 1-2 review/comparison sites
        3. Click through to target merchant
        4. Browse 2-3 products
        5. Return to target via Google (second visit)
        6. Proceed with purchase
        """
```

---

## Form Autofill Strategy

### Module: `form_autofill_injector.py`

Rather than using browser autofill (which antifraud systems can detect), TITAN's form autofill:

1. **Identifies form fields** by label text, name attribute, and placeholder
2. **Types values character by character** using Ghost Motor timing
3. **Handles dynamic forms** (fields that appear after previous fields are filled)
4. **Manages dropdowns** (state/country selectors)
5. **Handles address autocomplete** (Google Places suggestions)

The key difference from browser autofill: each character is typed individually with human-like timing, not pasted instantly. Antifraud systems specifically detect instant form fills as bot behavior.

---

## Kill Switch Integration

During the entire operation, the Kill Switch daemon runs in the background:

```
[KILLSWITCH] *** ARMED ***
[KILLSWITCH] Monitoring fraud score every 500ms
[KILLSWITCH] Threshold: score < 85 → PANIC

  Score: 95 → GREEN (safe)
  Score: 92 → GREEN (safe)
  Score: 88 → YELLOW (elevated, continue with caution)
  Score: 84 → RED → *** PANIC SEQUENCE ***
    Step 0: Network SEVERED (nftables DROP all outbound)
    Step 1: Browser KILLED
    Step 2: Hardware ID FLUSHED (new random ID via Netlink)
    Step 3: Session data CLEARED
    Step 4: Proxy ROTATED (new IP)
    Step 5: MAC address RANDOMIZED
    Sequence complete in 487ms
```

The entire panic sequence executes in under 500ms — faster than any human could react, and faster than the antifraud system can exfiltrate session data.
