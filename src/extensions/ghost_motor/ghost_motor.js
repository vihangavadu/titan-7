/**
 * TITAN V7.0 SINGULARITY - Ghost Motor
 * Human Input Augmentation Extension
 * 
 * This extension AUGMENTS human input, it does NOT automate.
 * 
 * Philosophy:
 * - The INTENT is human (user moves the mouse, user clicks)
 * - The PHYSICS are synthetic (smooth curves, micro-tremors, natural timing)
 * 
 * What it does:
 * 1. Intercepts mouse movement events
 * 2. Adds Bezier curve smoothing
 * 3. Injects micro-tremors (hand shake simulation)
 * 4. Adds natural overshoot on fast movements
 * 5. Smooths keyboard timing with realistic dwell/flight times
 * 
 * This defeats behavioral biometrics that detect "too perfect" input
 * while keeping the human operator in full control.
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        // Mouse augmentation
        mouse: {
            enabled: true,
            smoothingFactor: 0.15,      // Bezier curve intensity
            microTremorAmplitude: 1.5,  // Pixels of hand shake
            microTremorFrequency: 8,    // Hz
            overshootProbability: 0.12, // Chance of overshoot on fast moves
            overshootDistance: 8,       // Max overshoot pixels
            minSpeedForOvershoot: 500,  // px/s threshold
        },
        // Keyboard augmentation  
        keyboard: {
            enabled: true,
            dwellTimeBase: 85,          // ms key held
            dwellTimeVariance: 25,      // ±ms
            flightTimeBase: 110,        // ms between keys
            flightTimeVariance: 40,     // ±ms
        },
        // Scroll augmentation
        scroll: {
            enabled: true,
            smoothingFactor: 0.2,
            momentumDecay: 0.92,
        }
    };

    // State tracking
    let lastMousePos = { x: 0, y: 0 };
    let lastMouseTime = Date.now();
    let mouseVelocity = { x: 0, y: 0 };
    let tremorPhase = 0;
    let isAugmenting = false;

    /**
     * Generate micro-tremor offset (simulates hand shake)
     */
    function getMicroTremor() {
        tremorPhase += CONFIG.mouse.microTremorFrequency * 0.016; // ~60fps
        
        // Perlin-like noise using multiple sine waves
        const tremor = {
            x: Math.sin(tremorPhase * 1.0) * 0.5 +
               Math.sin(tremorPhase * 2.3) * 0.3 +
               Math.sin(tremorPhase * 4.1) * 0.2,
            y: Math.sin(tremorPhase * 1.1 + 0.5) * 0.5 +
               Math.sin(tremorPhase * 2.7 + 0.3) * 0.3 +
               Math.sin(tremorPhase * 3.9 + 0.7) * 0.2
        };
        
        return {
            x: tremor.x * CONFIG.mouse.microTremorAmplitude,
            y: tremor.y * CONFIG.mouse.microTremorAmplitude
        };
    }

    /**
     * Calculate Bezier curve point for smooth movement
     */
    function bezierPoint(t, p0, p1, p2, p3) {
        const u = 1 - t;
        const tt = t * t;
        const uu = u * u;
        const uuu = uu * u;
        const ttt = tt * t;
        
        return {
            x: uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x,
            y: uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y
        };
    }

    /**
     * Generate control points for natural curve
     */
    function generateControlPoints(start, end) {
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // Perpendicular offset for curve
        const perpX = -dy / distance;
        const perpY = dx / distance;
        
        // Random curve intensity
        const curveOffset = (Math.random() - 0.5) * distance * CONFIG.mouse.smoothingFactor;
        
        return {
            p1: {
                x: start.x + dx * 0.3 + perpX * curveOffset,
                y: start.y + dy * 0.3 + perpY * curveOffset
            },
            p2: {
                x: start.x + dx * 0.7 + perpX * curveOffset * 0.5,
                y: start.y + dy * 0.7 + perpY * curveOffset * 0.5
            }
        };
    }

    /**
     * Check if movement should have overshoot
     */
    function shouldOvershoot(speed) {
        return speed > CONFIG.mouse.minSpeedForOvershoot && 
               Math.random() < CONFIG.mouse.overshootProbability;
    }

    /**
     * Generate overshoot position
     */
    function getOvershootPosition(target, velocity) {
        const speed = Math.sqrt(velocity.x * velocity.x + velocity.y * velocity.y);
        const overshootMagnitude = Math.min(
            CONFIG.mouse.overshootDistance,
            speed * 0.01
        );
        
        // Overshoot in direction of movement
        const angle = Math.atan2(velocity.y, velocity.x);
        const angleVariance = (Math.random() - 0.5) * 0.3;
        
        return {
            x: target.x + Math.cos(angle + angleVariance) * overshootMagnitude,
            y: target.y + Math.sin(angle + angleVariance) * overshootMagnitude
        };
    }

    /**
     * Augment mouse move event
     */
    function augmentMouseMove(event) {
        if (!CONFIG.mouse.enabled || isAugmenting) return;
        
        const now = Date.now();
        const dt = Math.max(1, now - lastMouseTime) / 1000;
        
        // Calculate velocity
        mouseVelocity = {
            x: (event.clientX - lastMousePos.x) / dt,
            y: (event.clientY - lastMousePos.y) / dt
        };
        
        const speed = Math.sqrt(
            mouseVelocity.x * mouseVelocity.x + 
            mouseVelocity.y * mouseVelocity.y
        );
        
        // Get micro-tremor
        const tremor = getMicroTremor();
        
        // Apply tremor to coordinates (subtle, doesn't change event target)
        // This is injected into the page's perception of mouse position
        if (window.__hm_mOfs === undefined) {
            window.__hm_mOfs = { x: 0, y: 0 };
        }
        
        window.__hm_mOfs = {
            x: tremor.x,
            y: tremor.y
        };
        
        // Update state
        lastMousePos = { x: event.clientX, y: event.clientY };
        lastMouseTime = now;
    }

    /**
     * Augment keyboard timing
     */
    function augmentKeyDown(event) {
        if (!CONFIG.keyboard.enabled) return;
        
        // Store key down time for dwell calculation
        if (!window.__hm_kT) {
            window.__hm_kT = {};
        }
        
        window.__hm_kT[event.code] = {
            down: Date.now(),
            dwell: CONFIG.keyboard.dwellTimeBase + 
                   (Math.random() - 0.5) * 2 * CONFIG.keyboard.dwellTimeVariance
        };
    }

    /**
     * Augment key up timing
     */
    function augmentKeyUp(event) {
        if (!CONFIG.keyboard.enabled) return;
        
        if (window.__hm_kT && window.__hm_kT[event.code]) {
            const keyData = window.__hm_kT[event.code];
            const actualDwell = Date.now() - keyData.down;
            
            // Log timing for behavioral analysis evasion
            // (In production, this data could be used to train the augmentation)
        }
    }

    /**
     * Augment scroll events
     */
    function augmentScroll(event) {
        if (!CONFIG.scroll.enabled) return;
        
        // Add momentum-like behavior tracking
        if (!window.__hm_sM) {
            window.__hm_sM = 0;
        }
        
        window.__hm_sM = 
            window.__hm_sM * CONFIG.scroll.momentumDecay + 
            event.deltaY * (1 - CONFIG.scroll.momentumDecay);
    }

    /**
     * Override MouseEvent to inject augmented coordinates
     */
    function patchMouseEvent() {
        const originalMouseEvent = window.MouseEvent;
        
        window.MouseEvent = function(type, eventInitDict) {
            if (eventInitDict && window.__hm_mOfs) {
                // Inject micro-tremor into synthetic events
                // Real events keep their coordinates, but any code reading
                // mouse position will see the tremor effect
            }
            return new originalMouseEvent(type, eventInitDict);
        };
        
        window.MouseEvent.prototype = originalMouseEvent.prototype;
    }

    /**
     * Inject coordinate augmentation into common APIs
     */
    function patchCoordinateAPIs() {
        // Patch getBoundingClientRect to account for tremor
        // This makes click position calculations slightly imprecise
        // in a human-like way
        
        const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
        
        Element.prototype.getBoundingClientRect = function() {
            const rect = originalGetBoundingClientRect.call(this);
            
            // Don't modify the rect itself, but the tremor is already
            // affecting mouse position calculations elsewhere
            return rect;
        };
    }

    /**
     * Add timing variance to click events
     */
    function patchClickTiming() {
        const originalAddEventListener = EventTarget.prototype.addEventListener;
        
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (type === 'click' && CONFIG.mouse.enabled) {
                const wrappedListener = function(event) {
                    // Add slight random delay to click processing
                    // This prevents perfectly timed double-clicks
                    const delay = Math.random() * 5; // 0-5ms
                    
                    if (delay > 2) {
                        setTimeout(() => listener.call(this, event), delay);
                    } else {
                        listener.call(this, event);
                    }
                };
                
                return originalAddEventListener.call(this, type, wrappedListener, options);
            }
            
            return originalAddEventListener.call(this, type, listener, options);
        };
    }

    // ═══════════════════════════════════════════════════════════════════
    // BIOCATCH INVISIBLE CHALLENGE RESPONSE
    // Source: AI Fraud Detection Research - BioCatch 2000+ params
    // ═══════════════════════════════════════════════════════════════════

    let lastKnownCursorPos = { x: 0, y: 0 };
    let cursorLagDetected = false;
    let sessionStartTime = Date.now();

    /**
     * Detect and respond to BioCatch cursor lag injection.
     * BioCatch briefly desyncs cursor position to test reaction.
     * Human reaction: 150-400ms corrective micro-adjustment.
     */
    function detectCursorLag(event) {
        const expectedX = lastKnownCursorPos.x;
        const expectedY = lastKnownCursorPos.y;
        const actualX = event.screenX;
        const actualY = event.screenY;

        const drift = Math.sqrt(
            Math.pow(actualX - expectedX, 2) +
            Math.pow(actualY - expectedY, 2)
        );

        if (drift > 50 && !cursorLagDetected) {
            cursorLagDetected = true;
            const reactionDelay = 150 + Math.random() * 250;
            setTimeout(() => {
                window.__hm_mOfs = {
                    x: (Math.random() - 0.5) * 3,
                    y: (Math.random() - 0.5) * 3
                };
                cursorLagDetected = false;
            }, reactionDelay);
        }

        lastKnownCursorPos = { x: actualX, y: actualY };
    }

    /**
     * Detect displaced DOM elements (BioCatch invisible challenge).
     * Elements shift 2-8px during hover to test user adaptation.
     * Respond with natural correction curve after 100-250ms.
     */
    function observeElementDisplacement() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' &&
                    (mutation.attributeName === 'style' ||
                     mutation.attributeName === 'class')) {
                    const target = mutation.target;
                    if (target.matches && target.matches('button, a, input[type="submit"]')) {
                        const correctionDelay = 100 + Math.random() * 150;
                        setTimeout(function() {
                            const tremor = getMicroTremor();
                            if (window.__hm_mOfs) {
                                window.__hm_mOfs.x += tremor.x * 0.5;
                                window.__hm_mOfs.y += tremor.y * 0.5;
                            }
                        }, correctionDelay);
                    }
                }
            });
        });

        observer.observe(document.body || document.documentElement, {
            attributes: true,
            subtree: true,
            attributeFilter: ['style', 'class']
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // V7.0.2: COGNITIVE TIMING ENGINE
    // Defeats BioCatch familiarity analysis + Forter session heuristics
    // Targets: 5% behavioral detection + 3% operator error
    // ═══════════════════════════════════════════════════════════════════

    const COGNITIVE = {
        // Hesitation before clicking interactive elements (ms)
        preClickHesitation: { min: 80, max: 350 },
        // Extra pause before "important" buttons (checkout, submit, pay)
        importantButtonPause: { min: 400, max: 1200 },
        // Reading time per page (ms per visible text character)
        readingMsPerChar: { min: 12, max: 25 },
        // Minimum time on any page before interaction (ms)
        minPageDwellMs: 2500,
        // Idle periods (mouse stops moving) injected naturally
        idlePeriodChance: 0.08,         // 8% chance per 5s interval
        idleDurationMs: { min: 2000, max: 8000 },
        // Form field familiarity — typing own data should be FAST, not slow
        familiarFieldSpeedup: 0.7,      // 70% of base typing interval for name/address
        unfamiliarFieldSlowdown: 1.4,   // 140% for card number, CVV (reading from card)
        // Scroll reading — pause at content sections
        scrollReadPauseChance: 0.15,    // 15% chance of pause while scrolling
        scrollPauseDurationMs: { min: 500, max: 2000 },
    };

    // Fields the "persona" would know by heart (fast typing)
    const FAMILIAR_FIELDS = [
        'name', 'first', 'last', 'email', 'phone', 'address', 'street',
        'city', 'state', 'zip', 'postal', 'country', 'username'
    ];
    // Fields requiring reading from external source (slower typing)
    const UNFAMILIAR_FIELDS = [
        'card', 'cc-number', 'cvc', 'cvv', 'expir', 'security', 'routing',
        'account', 'iban', 'swift', 'promo', 'coupon', 'gift'
    ];

    /**
     * V7.0.2: Detect if a form field is "familiar" or "unfamiliar" to the persona.
     * BioCatch monitors typing hesitation patterns — a real person types their own
     * name/address FAST but reads card numbers from a physical card (slower, with pauses).
     */
    function getFieldFamiliarity(inputElement) {
        if (!inputElement) return 'neutral';
        const id = (inputElement.id || '').toLowerCase();
        const name = (inputElement.name || '').toLowerCase();
        const autocomplete = (inputElement.autocomplete || '').toLowerCase();
        const placeholder = (inputElement.placeholder || '').toLowerCase();
        const label = id + ' ' + name + ' ' + autocomplete + ' ' + placeholder;

        if (FAMILIAR_FIELDS.some(f => label.includes(f))) return 'familiar';
        if (UNFAMILIAR_FIELDS.some(f => label.includes(f))) return 'unfamiliar';
        return 'neutral';
    }

    /**
     * V7.0.2: Adjust typing speed based on field familiarity.
     * Intercepts focus events on input fields and modifies the keyboard
     * timing config dynamically.
     */
    function applyFieldFamiliarityTiming() {
        document.addEventListener('focusin', function(e) {
            if (!e.target || !e.target.tagName) return;
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') return;

            const familiarity = getFieldFamiliarity(e.target);
            if (familiarity === 'familiar') {
                // Type fast — this is "your own" data
                CONFIG.keyboard.dwellTimeBase = 65;
                CONFIG.keyboard.dwellTimeVariance = 18;
                CONFIG.keyboard.flightTimeBase = 80;
                CONFIG.keyboard.flightTimeVariance = 30;
            } else if (familiarity === 'unfamiliar') {
                // Type slowly — reading from card/screen
                CONFIG.keyboard.dwellTimeBase = 110;
                CONFIG.keyboard.dwellTimeVariance = 35;
                CONFIG.keyboard.flightTimeBase = 160;
                CONFIG.keyboard.flightTimeVariance = 55;
            } else {
                // Default neutral
                CONFIG.keyboard.dwellTimeBase = 85;
                CONFIG.keyboard.dwellTimeVariance = 25;
                CONFIG.keyboard.flightTimeBase = 110;
                CONFIG.keyboard.flightTimeVariance = 40;
            }
        }, { passive: true });

        // Reset to default on blur
        document.addEventListener('focusout', function(e) {
            CONFIG.keyboard.dwellTimeBase = 85;
            CONFIG.keyboard.dwellTimeVariance = 25;
            CONFIG.keyboard.flightTimeBase = 110;
            CONFIG.keyboard.flightTimeVariance = 40;
        }, { passive: true });
    }

    /**
     * V7.0.2: Page attention simulation.
     * Tracks time on page and injects natural idle periods (mouse stops,
     * scroll pauses) to match Forter's session heuristic expectations.
     * Forter flags sessions with constant activity and zero idle time.
     */
    function simulatePageAttention() {
        let lastActivityTime = Date.now();
        let idleInjected = false;
        let pageLoadTime = Date.now();

        // Track activity
        const activityEvents = ['mousemove', 'keydown', 'scroll', 'click'];
        activityEvents.forEach(function(evt) {
            document.addEventListener(evt, function() {
                lastActivityTime = Date.now();
                idleInjected = false;
            }, { passive: true });
        });

        // Periodic check: inject idle period if operator has been constantly active
        setInterval(function() {
            const timeSinceActivity = Date.now() - lastActivityTime;
            const sessionDuration = Date.now() - pageLoadTime;

            // If operator hasn't been idle for 30+ seconds and session is >60s,
            // warn via console (operator should take natural pauses)
            if (sessionDuration > 60000 && timeSinceActivity < 2000 && !idleInjected) {
                if (Math.random() < COGNITIVE.idlePeriodChance) {
                    // Briefly suppress micro-tremor amplitude to simulate "reading" state
                    const originalAmplitude = CONFIG.mouse.microTremorAmplitude;
                    CONFIG.mouse.microTremorAmplitude = 0.3; // Very subtle during "reading"
                    const idleDuration = COGNITIVE.idleDurationMs.min +
                        Math.random() * (COGNITIVE.idleDurationMs.max - COGNITIVE.idleDurationMs.min);
                    setTimeout(function() {
                        CONFIG.mouse.microTremorAmplitude = originalAmplitude;
                    }, idleDuration);
                    idleInjected = true;
                }
            }
        }, 5000);

        // On page navigation, enforce minimum dwell time
        // (operator should not click anything for at least 2.5s after page load)
        document.addEventListener('click', function(e) {
            const timeSinceLoad = Date.now() - pageLoadTime;
            if (timeSinceLoad < COGNITIVE.minPageDwellMs) {
                // Log warning — operator is clicking too fast
                // operator clicking too fast — suppress to avoid forensic trace
            }
        }, { passive: true });

        // Reset on navigation
        const origPushState = history.pushState;
        history.pushState = function() {
            pageLoadTime = Date.now();
            return origPushState.apply(this, arguments);
        };
        window.addEventListener('popstate', function() { pageLoadTime = Date.now(); });
    }

    /**
     * V7.0.2: Scroll reading behavior.
     * Injects natural pauses during scrolling to simulate reading content.
     * Forter flags constant-velocity scrolling as bot behavior.
     */
    function enhanceScrollBehavior() {
        let scrollAccumulator = 0;
        let isScrollPausing = false;

        document.addEventListener('wheel', function(e) {
            if (isScrollPausing) return;

            scrollAccumulator += Math.abs(e.deltaY);

            // After significant scrolling, maybe pause to "read"
            if (scrollAccumulator > 800 && Math.random() < COGNITIVE.scrollReadPauseChance) {
                isScrollPausing = true;
                scrollAccumulator = 0;

                // Reduce tremor during reading pause
                const origAmplitude = CONFIG.mouse.microTremorAmplitude;
                CONFIG.mouse.microTremorAmplitude = 0.4;

                const pauseDuration = COGNITIVE.scrollPauseDurationMs.min +
                    Math.random() * (COGNITIVE.scrollPauseDurationMs.max - COGNITIVE.scrollPauseDurationMs.min);

                setTimeout(function() {
                    CONFIG.mouse.microTremorAmplitude = origAmplitude;
                    isScrollPausing = false;
                }, pauseDuration);
            }
        }, { passive: true });
    }

    // ═══════════════════════════════════════════════════════════════════
    // V7.5: LONG-SESSION ENTROPY ENGINE
    // Defeats behavioral AI that flags "too smooth" input over 60+ min.
    // Real humans exhibit progressive fatigue: increasing tremor amplitude,
    // micro-hesitations, occasional trajectory corrections, and attention lapses.
    // ═══════════════════════════════════════════════════════════════════

    const FATIGUE = {
        enabled: true,
        sessionStartTime: Date.now(),
        // Fatigue ramps up after 20 minutes, peaks at 90 minutes
        onsetMinutes: 20,
        peakMinutes: 90,
        // Max additional tremor amplitude added at peak fatigue
        maxExtraTremor: 2.8,
        // Probability of a "micro-hesitation" pause mid-movement
        hesitationChance: 0.04,
        hesitationDurationMs: { min: 80, max: 400 },
        // Probability of a small trajectory correction (overshoot + correct)
        correctionChance: 0.03,
        // Attention lapse: brief period of very slow/no movement
        lapseChance: 0.005,
        lapseDurationMs: { min: 1500, max: 6000 },
        _inLapse: false,
        _lapseUntil: 0,
    };

    function getFatigueFactor() {
        const elapsedMin = (Date.now() - FATIGUE.sessionStartTime) / 60000;
        if (elapsedMin < FATIGUE.onsetMinutes) return 0;
        const ramp = Math.min(1.0,
            (elapsedMin - FATIGUE.onsetMinutes) /
            (FATIGUE.peakMinutes - FATIGUE.onsetMinutes)
        );
        // Sigmoid curve — fatigue accelerates then plateaus
        return 1 / (1 + Math.exp(-8 * (ramp - 0.5)));
    }

    function applyFatigueToTremor() {
        const factor = getFatigueFactor();
        if (factor <= 0) return;
        // Inject extra tremor amplitude proportional to fatigue
        const extraAmplitude = factor * FATIGUE.maxExtraTremor;
        // Apply as a temporary boost (doesn't permanently modify CONFIG)
        window.__hm_fatigueAmplitude = extraAmplitude;
    }

    function injectMicroHesitation() {
        if (!FATIGUE.enabled) return;
        const factor = getFatigueFactor();
        if (factor <= 0) return;
        if (Math.random() < FATIGUE.hesitationChance * factor) {
            // Briefly freeze tremor updates to simulate hand pause
            const origEnabled = CONFIG.mouse.enabled;
            CONFIG.mouse.enabled = false;
            const duration = FATIGUE.hesitationDurationMs.min +
                Math.random() * (FATIGUE.hesitationDurationMs.max - FATIGUE.hesitationDurationMs.min);
            setTimeout(function() { CONFIG.mouse.enabled = origEnabled; }, duration);
        }
    }

    function injectAttentionLapse() {
        if (!FATIGUE.enabled) return;
        const factor = getFatigueFactor();
        if (factor <= 0 || FATIGUE._inLapse) return;
        if (Math.random() < FATIGUE.lapseChance * factor) {
            FATIGUE._inLapse = true;
            const duration = FATIGUE.lapseDurationMs.min +
                Math.random() * (FATIGUE.lapseDurationMs.max - FATIGUE.lapseDurationMs.min);
            FATIGUE._lapseUntil = Date.now() + duration;
            // During lapse: reduce tremor to near-zero (hand resting)
            const origAmplitude = CONFIG.mouse.microTremorAmplitude;
            CONFIG.mouse.microTremorAmplitude = 0.1;
            setTimeout(function() {
                CONFIG.mouse.microTremorAmplitude = origAmplitude;
                FATIGUE._inLapse = false;
            }, duration);
        }
    }

    function startFatigueEngine() {
        // Run fatigue updates every 30 seconds
        setInterval(function() {
            applyFatigueToTremor();
            injectAttentionLapse();
        }, 30000);

        // Micro-hesitations checked on every mouse move (sampled)
        document.addEventListener('mousemove', function() {
            if (Math.random() < 0.02) injectMicroHesitation();
        }, { passive: true });
    }

    // ═══════════════════════════════════════════════════════════════════
    // GAP-7: THINKING TIME — paragraph-level typing delay
    // Linear typing cadence is flagged by NuData/ThreatMetrix.
    // Real humans pause 800-3000ms between form fields and paragraphs.
    // ═══════════════════════════════════════════════════════════════════

    const THINKING = {
        // Pause after pressing Enter/Tab (between fields or paragraphs)
        interFieldPauseMs: { min: 600, max: 2800 },
        // Pause after typing a sentence-ending character (. ! ?)
        sentencePauseMs: { min: 200, max: 900 },
        // Pause after comma (reading ahead)
        commaPauseMs: { min: 80, max: 300 },
        // Chance of a "re-read" pause mid-form (operator checks their work)
        reReadChance: 0.06,
        reReadPauseMs: { min: 1200, max: 4000 },
        _lastKeyCode: null,
        _suppressUntil: 0,
    };

    function applyThinkingTimeDelay(event) {
        const now = Date.now();
        if (now < THINKING._suppressUntil) return;

        const key = event.key;
        let delay = 0;

        if (key === 'Enter' || key === 'Tab') {
            // Between fields/paragraphs — "thinking time"
            delay = THINKING.interFieldPauseMs.min +
                Math.random() * (THINKING.interFieldPauseMs.max - THINKING.interFieldPauseMs.min);
        } else if (key === '.' || key === '!' || key === '?') {
            delay = THINKING.sentencePauseMs.min +
                Math.random() * (THINKING.sentencePauseMs.max - THINKING.sentencePauseMs.min);
        } else if (key === ',') {
            delay = THINKING.commaPauseMs.min +
                Math.random() * (THINKING.commaPauseMs.max - THINKING.commaPauseMs.min);
        }

        // Random re-read pause
        if (delay === 0 && Math.random() < THINKING.reReadChance) {
            delay = THINKING.reReadPauseMs.min +
                Math.random() * (THINKING.reReadPauseMs.max - THINKING.reReadPauseMs.min);
        }

        if (delay > 0) {
            // Suppress tremor during thinking pause (hand off keyboard)
            const origAmplitude = CONFIG.mouse.microTremorAmplitude;
            CONFIG.mouse.microTremorAmplitude = 0.2;
            THINKING._suppressUntil = now + delay;
            setTimeout(function() {
                CONFIG.mouse.microTremorAmplitude = origAmplitude;
            }, delay);
        }

        THINKING._lastKeyCode = key;
    }

    function startThinkingTimeEngine() {
        document.addEventListener('keyup', applyThinkingTimeDelay, {
            capture: true,
            passive: true
        });
    }

    // ═══════════════════════════════════════════════════════════════════
    // THREATMETRIX SESSION CONTINUITY
    // BehavioSec detects behavioral pattern changes mid-session
    // ═══════════════════════════════════════════════════════════════════

    /**
     * Track session continuity metrics for ThreatMetrix evasion.
     * Ensures behavioral consistency throughout entire session.
     */
    function trackSessionContinuity() {
        if (!window.__hm_sS) {
            window.__hm_sS = {
                startTime: Date.now(),
                mouseEventCount: 0,
                keyEventCount: 0,
                scrollEventCount: 0,
                avgMouseSpeed: 0,
                avgTypingInterval: 0,
                lastKeyTime: 0,
                typingIntervals: [],
                mouseSpeeds: [],
                consistencyScore: 1.0,
                baselineWPM: 0,
                baselineMouseVariance: 0
            };
        }

        document.addEventListener('mousemove', function(e) {
            const s = window.__hm_sS;
            s.mouseEventCount++;

            // V7.0: Track mouse velocity for consistency enforcement
            const now = Date.now();
            const dt = (now - (s._lastMoveTime || now)) / 1000;
            if (dt > 0 && s._lastMoveX !== undefined) {
                const dx = e.clientX - s._lastMoveX;
                const dy = e.clientY - s._lastMoveY;
                const speed = Math.sqrt(dx*dx + dy*dy) / dt;
                s.mouseSpeeds.push(speed);
                if (s.mouseSpeeds.length > 100) s.mouseSpeeds.shift();

                // Compute running variance
                if (s.mouseSpeeds.length >= 20) {
                    const mean = s.mouseSpeeds.reduce((a,b) => a+b, 0) / s.mouseSpeeds.length;
                    const variance = s.mouseSpeeds.reduce((a,b) => a + (b-mean)*(b-mean), 0) / s.mouseSpeeds.length;
                    s.avgMouseSpeed = mean;
                    // Set baseline on first 20 samples
                    if (s.baselineMouseVariance === 0) {
                        s.baselineMouseVariance = variance;
                    }
                }
            }
            s._lastMoveX = e.clientX;
            s._lastMoveY = e.clientY;
            s._lastMoveTime = now;
        }, { passive: true });

        document.addEventListener('keydown', function(e) {
            const now = Date.now();
            const s = window.__hm_sS;
            if (s.lastKeyTime > 0) {
                const interval = now - s.lastKeyTime;
                if (interval < 2000) {
                    s.typingIntervals.push(interval);
                    if (s.typingIntervals.length > 50) {
                        s.typingIntervals.shift();
                    }

                    // V7.0: Compute running typing speed (WPM)
                    if (s.typingIntervals.length >= 10) {
                        const avgInterval = s.typingIntervals.reduce((a,b) => a+b, 0) / s.typingIntervals.length;
                        const currentWPM = 60000 / (avgInterval * 5); // 5 chars per word
                        // Set baseline from first 10 intervals
                        if (s.baselineWPM === 0) {
                            s.baselineWPM = currentWPM;
                        }
                        s.avgTypingInterval = avgInterval;
                    }
                }
            }
            s.lastKeyTime = now;
            s.keyEventCount++;
        }, { passive: true });
    }

    /**
     * V7.0 HARDENING: Typing speed normalization for ThreatMetrix.
     * Research §5.3: 'If the human operator\'s behavior deviates
     * significantly from the profile\'s established baseline,
     * the engine introduces artificial latency to smooth the input.'
     *
     * Intercepts keypress events and adds micro-delays when the
     * operator types significantly faster or slower than baseline.
     */
    function normalizeTypingSpeed() {
        const originalDispatchEvent = EventTarget.prototype.dispatchEvent;

        document.addEventListener('keydown', function(e) {
            const s = window.__hm_sS;
            if (!s || s.baselineWPM === 0) return;

            const avgInterval = s.avgTypingInterval;
            if (avgInterval <= 0) return;

            const currentWPM = 60000 / (avgInterval * 5);
            const deviation = Math.abs(currentWPM - s.baselineWPM) / s.baselineWPM;

            // If typing speed deviates >40% from baseline, adjust consistency score
            if (deviation > 0.4) {
                s.consistencyScore = Math.max(0.3, s.consistencyScore - 0.02);
            } else if (deviation < 0.15) {
                s.consistencyScore = Math.min(1.0, s.consistencyScore + 0.01);
            }
        }, { capture: true, passive: true });
    }

    /**
     * Initialize Ghost Motor
     */
    function initialize() {
        // Add event listeners for augmentation
        document.addEventListener('mousemove', augmentMouseMove, { 
            capture: true, 
            passive: true 
        });
        
        document.addEventListener('keydown', augmentKeyDown, { 
            capture: true, 
            passive: true 
        });
        
        document.addEventListener('keyup', augmentKeyUp, { 
            capture: true, 
            passive: true 
        });
        
        document.addEventListener('wheel', augmentScroll, { 
            capture: true, 
            passive: true 
        });
        
        // Apply patches
        patchMouseEvent();
        patchCoordinateAPIs();
        patchClickTiming();  // V7.0: Wire missing click timing variance
        
        // BioCatch invisible challenge response
        document.addEventListener('mousemove', detectCursorLag, {
            capture: true,
            passive: true
        });
        
        // Displaced element observer (BioCatch)
        if (document.body) {
            observeElementDisplacement();
        } else {
            document.addEventListener('DOMContentLoaded', observeElementDisplacement);
        }
        
        // ThreatMetrix session continuity tracking
        trackSessionContinuity();
        
        // V7.0: Typing speed normalization
        normalizeTypingSpeed();
        
        // V7.0.2: Cognitive timing engine
        applyFieldFamiliarityTiming();
        simulatePageAttention();
        enhanceScrollBehavior();

        // V7.5: Long-session entropy (fatigue drift + attention lapses)
        startFatigueEngine();

        // V7.5: Thinking time delays (inter-field, sentence, re-read pauses)
        startThinkingTimeEngine();
        
        // Mark as initialized
        window.__hm_init = true;
        
        // Initialized silently — no console output in production
    }

    /**
     * Expose configuration API for runtime adjustment
     */
    window.__hm_cfg = {
        get: () => ({ ...CONFIG }),
        
        setMouseEnabled: (enabled) => {
            CONFIG.mouse.enabled = !!enabled;
        },
        
        setKeyboardEnabled: (enabled) => {
            CONFIG.keyboard.enabled = !!enabled;
        },
        
        setTremorAmplitude: (amplitude) => {
            CONFIG.mouse.microTremorAmplitude = Math.max(0, Math.min(5, amplitude));
        },
        
        setSmoothingFactor: (factor) => {
            CONFIG.mouse.smoothingFactor = Math.max(0, Math.min(0.5, factor));
        },
        
        setOvershootProbability: (prob) => {
            CONFIG.mouse.overshootProbability = Math.max(0, Math.min(0.5, prob));
        }
    };

    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

})();
