# TITAN V7.0 SINGULARITY - Operator Guide

## Manual Operation Handbook for 95%+ Success Rate

**Authority:** Dva.12 | **Version:** 6.2.0 | **Classification:** OPERATIONAL

---

## 1. Session Timing Guide

### Critical: Human-Like Timing

Fraud detection systems analyze timing patterns. Too fast = bot. Too slow = abandoned cart detection.

### Recommended Page Timings

| Page/Action | Minimum | Optimal | Maximum | Notes |
|-------------|---------|---------|---------|-------|
| **Product View** | 30s | 45-90s | 180s | Read description, scroll, check reviews |
| **Add to Cart** | 5s | 8-15s | 30s | Brief pause after clicking |
| **View Cart** | 10s | 20-40s | 60s | Review items, check totals |
| **Checkout Start** | 15s | 30-60s | 120s | Fill shipping info naturally |
| **Payment Entry** | 20s | 45-90s | 180s | Type card details with pauses |
| **Review Order** | 10s | 20-45s | 90s | Final review before submit |
| **Order Confirmation** | 5s | 10-20s | 60s | Wait for confirmation page |

### Timing Tips

1. **Never rush** - Even if you know exactly what to do, pause
2. **Scroll naturally** - Don't jump to bottom instantly
3. **Read content** - Move eyes across page (cursor follows)
4. **Hesitate on payment** - Normal humans double-check card numbers
5. **Don't multi-tab** - Stay focused on one checkout flow

### Red Flags (Avoid These)

- ❌ Completing checkout in under 2 minutes
- ❌ Instant form fills (paste detected)
- ❌ No scrolling on product pages
- ❌ Perfect typing speed (no corrections)
- ❌ Clicking submit within 1 second of last field

---

## 2. 3D Secure (3DS) Handling

### What is 3DS?

3D Secure is bank-side verification that requires:
- SMS OTP code
- Bank app approval
- Biometric verification
- Security questions

### 3DS Detection in Cerberus

When Cerberus shows **risk_score=40** or status **"3DS Required"**, the card requires additional verification.

### Handling Strategies

#### Strategy A: Use Non-3DS Cards
- Filter cards before operation
- Cerberus risk_score=20 = no 3DS
- Prepaid cards often skip 3DS
- Some BINs are known non-3DS

#### Strategy B: SMS OTP Ready
If you have access to the card's phone:
1. Proceed with checkout
2. Wait for 3DS popup
3. Enter OTP when received
4. Complete within 60 seconds (OTP expires)

#### Strategy C: Virtual Numbers
For SMS verification:
- TextNow (US numbers)
- Google Voice (US)
- Hushed (disposable)
- Note: Banks may block known VoIP ranges

#### Strategy D: Avoid 3DS Triggers
Some factors reduce 3DS likelihood:
- Low transaction amounts (<$50)
- Trusted merchant relationships
- Matching billing/shipping
- Aged profile with history

### 3DS Failure Recovery

If 3DS fails:
1. **Don't retry immediately** - Wait 24 hours
2. **Don't use same card** - It's now flagged
3. **Check decline code** - Soft vs hard decline
4. **Document for learning** - Note what triggered it

---

## 3. Navigation Best Practices

### Organic Navigation Path

**Never** navigate directly to checkout. Always:

1. **Start at Google**
   ```
   google.com → search "amazon electronics" → click organic result
   ```

2. **Browse naturally**
   ```
   Homepage → Category → Product → Add to Cart → Checkout
   ```

3. **Create referrer chain**
   - document.referrer should show previous page
   - Direct URL entry = empty referrer = suspicious

### Example Flow: Amazon

```
1. google.com
2. Search: "amazon laptop deals"
3. Click: Amazon organic result (not ad)
4. Browse: Electronics → Computers → Laptops
5. View: 2-3 products (30-60s each)
6. Select: Target product
7. Add to Cart
8. View Cart
9. Proceed to Checkout
10. Complete purchase
```

### Mouse Movement

- **Don't teleport** - Move cursor smoothly between elements
- **Overshoot slightly** - Humans don't click perfectly
- **Hover before click** - Brief pause on buttons
- **Scroll with mouse** - Use wheel, not keyboard

---

## 4. Pre-Operation Checklist

### Before Every Operation

- [ ] Profile forged with Genesis (90+ days age)
- [ ] Hardware shield active (check kernel module)
- [ ] Network shield active (check eBPF)
- [ ] Proxy configured (residential, matching billing geo)
- [ ] Card validated with Cerberus (LIVE status)
- [ ] Card holder matches profile persona
- [ ] Billing address matches proxy location
- [ ] Browser launched with titan-browser

### Pre-Flight Validation

Run before handover:
```bash
titan-browser --profile my_profile --preflight
```

Or in Python:
```python
from titan.core import run_preflight_checks
result = run_preflight_checks("/opt/titan/profiles/my_profile")
if not result["passed"]:
    print("ABORT:", result["abort_reason"])
```

---

## 5. Error Recovery

### Common Declines and Actions

| Decline Code | Meaning | Action |
|--------------|---------|--------|
| `card_declined` | Generic decline | Try different card |
| `insufficient_funds` | Balance issue | Card is valid, try lower amount |
| `incorrect_cvc` | CVV wrong | Verify CVV, retry once |
| `expired_card` | Card expired | Discard card |
| `processing_error` | Temporary | Wait 5 min, retry |
| `fraud_suspected` | Flagged | **STOP** - Profile burned |
| `velocity_exceeded` | Too many attempts | Wait 24 hours |

### If Flagged

1. **Stop immediately** - Don't retry
2. **Close browser** - Clear session
3. **Don't reuse profile** - It's burned
4. **Don't reuse card** - It's flagged
5. **Wait 24-48 hours** - Let velocity reset
6. **Create new profile** - Fresh start

---

## 6. Quick Reference Commands

### Profile Management
```bash
# Forge new profile
titan-genesis --target amazon_us --persona "John Smith" --age 90

# List profiles
ls /opt/titan/profiles/

# Launch browser with profile
titan-browser -p titan_abc123 https://amazon.com
```

### Card Validation
```bash
# Validate single card
titan-cerberus --card "4111111111111111|12|25|123"

# Batch validate
titan-cerberus --file cards.txt --output results.json
```

### System Status
```bash
# Check all shields
titan-status

# Check kernel module
lsmod | grep titan_hw

# Check eBPF
bpftool prog list | grep titan
```

---

## 7. Success Metrics

### Target: 95% Success Rate

| Factor | Weight | Target |
|--------|--------|--------|
| Profile Trust | 25% | 95%+ |
| Network Sovereignty | 15% | 95%+ |
| Hardware Masking | 10% | 98%+ |
| Behavioral Synthesis | 15% | 95%+ |
| Card Quality | 20% | 85%+ |
| Operational Execution | 15% | 90%+ |

### Your Role (The Final 5%)

The system handles 95% of detection vectors. You handle:
- Natural timing
- Organic navigation
- 3DS challenges
- Unexpected UI changes
- Human judgment calls

---

*TITAN V7.0 SINGULARITY | Reality Synthesis Suite*
*The system achieves 95%. You deliver the final 5%.*
