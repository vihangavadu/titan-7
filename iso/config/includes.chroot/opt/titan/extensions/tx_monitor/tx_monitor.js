/**
 * TITAN V7.0.3 SINGULARITY — TX Monitor (Content Script)
 * 
 * Intercepts payment-related network requests and captures:
 * - PSP response codes (Stripe, Adyen, Braintree, Auth.net, Shopify)
 * - Approval/decline status
 * - 3DS challenge triggers
 * - AVS/CVV results
 * - Transaction amounts and merchant info
 * 
 * Sends captured data to local Python backend at http://127.0.0.1:7443/api/tx
 * 
 * Detection method: Hooks XMLHttpRequest and fetch() to intercept payment
 * API responses without modifying any page behavior.
 */

(function() {
    'use strict';

    const BACKEND_URL = 'http://127.0.0.1:7443/api/tx';

    // ═══════════════════════════════════════════════════════════════════
    // PSP ENDPOINT PATTERNS — URLs that indicate payment processing
    // ═══════════════════════════════════════════════════════════════════

    const PSP_PATTERNS = {
        stripe: [
            /api\.stripe\.com\/v1\/payment_intents/i,
            /api\.stripe\.com\/v1\/charges/i,
            /api\.stripe\.com\/v1\/tokens/i,
            /api\.stripe\.com\/v1\/setup_intents/i,
            /api\.stripe\.com\/v1\/payment_methods/i,
            /api\.stripe\.com\/v1\/sources/i,
            /api\.stripe\.com\/v1\/3d_secure/i,
        ],
        adyen: [
            /checkoutshopper.*\.adyen\.com\/.*\/payments/i,
            /pal-.*\.adyen\.com\/.*\/authorise/i,
            /checkout.*\.adyen\.com\/.*\/payments\/details/i,
            /adyen\.com\/.*\/submitThreeDS2Fingerprint/i,
        ],
        braintree: [
            /payments\.braintree-api\.com/i,
            /api\.braintreegateway\.com.*\/transactions/i,
            /client-analytics\.braintreegateway\.com/i,
        ],
        shopify: [
            /shopify\.com\/.*\/checkouts\/.*\/processing/i,
            /shopify\.com\/.*\/checkouts\/.*\/payments/i,
            /shop\.app\/pay/i,
            /shopify\.com\/.*\/wallets\/checkouts/i,
        ],
        authorize_net: [
            /accept\.authorize\.net/i,
            /api2?\.authorize\.net.*\/transaction/i,
            /secure\.authorize\.net/i,
        ],
        cybersource: [
            /cybersource\.com.*\/flex\/v2/i,
            /cybersource\.com.*\/pts\/v2\/payments/i,
        ],
        worldpay: [
            /payments\.worldpay\.com/i,
            /secure\.worldpay\.com.*\/wcc\/dispatcher/i,
        ],
        checkout_com: [
            /api\.checkout\.com\/payments/i,
            /cko-session-id/i,
        ],
        square: [
            /connect\.squareup\.com.*\/payments/i,
            /pci-connect\.squareup\.com/i,
        ],
        paypal: [
            /api\.paypal\.com\/v2\/checkout\/orders/i,
            /api\.paypal\.com\/v1\/payments/i,
        ],
    };

    // 3DS-related URL patterns
    const THREE_DS_PATTERNS = [
        /3dsecure/i,
        /three-d-secure/i,
        /3ds2/i,
        /cardinalcommerce\.com/i,
        /arcot\.com/i,
        /centinelapistag/i,
        /acs\./i,
        /\/3ds\//i,
        /threedsmethod/i,
    ];

    // ═══════════════════════════════════════════════════════════════════
    // RESPONSE PARSERS — Extract status/codes from PSP responses
    // ═══════════════════════════════════════════════════════════════════

    function detectPSP(url) {
        for (const [psp, patterns] of Object.entries(PSP_PATTERNS)) {
            for (const pattern of patterns) {
                if (pattern.test(url)) return psp;
            }
        }
        return null;
    }

    function is3DSRequest(url) {
        return THREE_DS_PATTERNS.some(p => p.test(url));
    }

    function parseStripeResponse(data) {
        const result = { status: 'unknown', code: '', amount: null, three_ds: false };
        try {
            const obj = typeof data === 'string' ? JSON.parse(data) : data;
            if (obj.status === 'succeeded' || obj.status === 'active') {
                result.status = 'approved';
                result.code = 'approve';
            } else if (obj.status === 'requires_action' || obj.status === 'requires_source_action') {
                result.status = 'pending_3ds';
                result.code = 'authentication_required';
                result.three_ds = true;
            } else if (obj.last_payment_error) {
                result.status = 'declined';
                result.code = obj.last_payment_error.decline_code || obj.last_payment_error.code || 'generic_decline';
            } else if (obj.error) {
                result.status = 'declined';
                result.code = obj.error.decline_code || obj.error.code || 'error';
            } else if (obj.outcome && obj.outcome.seller_message) {
                result.status = obj.outcome.type === 'authorized' ? 'approved' : 'declined';
                result.code = obj.outcome.reason || obj.outcome.type;
            }
            result.amount = obj.amount ? obj.amount / 100 : null;
            result.currency = obj.currency || 'usd';
        } catch(e) {}
        return result;
    }

    function parseAdyenResponse(data) {
        const result = { status: 'unknown', code: '', amount: null, three_ds: false };
        try {
            const obj = typeof data === 'string' ? JSON.parse(data) : data;
            const rc = obj.resultCode || obj.status || '';
            if (rc === 'Authorised' || rc === 'Received') {
                result.status = 'approved';
                result.code = rc;
            } else if (rc === 'Refused' || rc === 'Declined') {
                result.status = 'declined';
                result.code = obj.refusalReasonCode || obj.refusalReason || rc;
            } else if (rc === 'RedirectShopper' || rc === 'ChallengeShopper' || rc === 'IdentifyShopper') {
                result.status = 'pending_3ds';
                result.code = rc;
                result.three_ds = true;
            } else if (rc === 'Error') {
                result.status = 'declined';
                result.code = 'Error';
            } else if (rc === 'Cancelled') {
                result.status = 'declined';
                result.code = 'Cancelled';
            }
            if (obj.amount) result.amount = obj.amount.value ? obj.amount.value / 100 : obj.amount;
            result.refusalReason = obj.refusalReason || '';
        } catch(e) {}
        return result;
    }

    function parseBraintreeResponse(data) {
        const result = { status: 'unknown', code: '', amount: null, three_ds: false };
        try {
            const obj = typeof data === 'string' ? JSON.parse(data) : data;
            const tx = obj.transaction || obj.data?.transaction || obj;
            if (tx.status === 'authorized' || tx.status === 'submitted_for_settlement' || tx.status === 'settled') {
                result.status = 'approved';
                result.code = 'approved';
            } else if (tx.status === 'gateway_rejected' || tx.status === 'processor_declined') {
                result.status = 'declined';
                result.code = tx.processorResponseCode || tx.gatewayRejectionReason || 'declined';
            }
            result.amount = tx.amount ? parseFloat(tx.amount) : null;
            if (tx.threeDSecureInfo) result.three_ds = true;
        } catch(e) {}
        return result;
    }

    function parseShopifyResponse(data) {
        const result = { status: 'unknown', code: '', amount: null, three_ds: false };
        try {
            const obj = typeof data === 'string' ? JSON.parse(data) : data;
            if (obj.checkout || obj.order) {
                const checkout = obj.checkout || obj.order;
                if (checkout.financial_status === 'paid' || checkout.order_id) {
                    result.status = 'approved';
                    result.code = 'approved';
                } else if (checkout.errors || checkout.payment_failed_message) {
                    result.status = 'declined';
                    result.code = checkout.payment_failed_message || 'declined';
                }
                result.amount = checkout.total_price ? parseFloat(checkout.total_price) : null;
            }
            if (obj.requires_action || obj.redirect_url) {
                result.three_ds = true;
            }
        } catch(e) {}
        return result;
    }

    function parseGenericResponse(data, httpStatus) {
        const result = { status: 'unknown', code: '', amount: null, three_ds: false };
        try {
            const obj = typeof data === 'string' ? JSON.parse(data) : data;
            // Look for common patterns
            const text = JSON.stringify(obj).toLowerCase();
            if (text.includes('"approved"') || text.includes('"succeeded"') || 
                text.includes('"authorized"') || text.includes('"success"')) {
                result.status = 'approved';
                result.code = 'approved';
            } else if (text.includes('"declined"') || text.includes('"refused"') ||
                       text.includes('"failed"') || text.includes('"error"')) {
                result.status = 'declined';
                // Try to extract code
                const codeMatch = text.match(/"(?:decline_?code|error_?code|reason_?code|code)"\s*:\s*"([^"]+)"/i);
                result.code = codeMatch ? codeMatch[1] : 'generic_decline';
            }
            if (text.includes('3dsecure') || text.includes('three_d') || text.includes('authentication_required')) {
                result.three_ds = true;
            }
            // Try to find amount
            const amtMatch = text.match(/"(?:amount|total|price)"\s*:\s*(\d+\.?\d*)/i);
            if (amtMatch) result.amount = parseFloat(amtMatch[1]);
        } catch(e) {
            if (httpStatus >= 400) {
                result.status = 'declined';
                result.code = `http_${httpStatus}`;
            }
        }
        return result;
    }

    const PSP_PARSERS = {
        stripe: parseStripeResponse,
        adyen: parseAdyenResponse,
        braintree: parseBraintreeResponse,
        shopify: parseShopifyResponse,
    };

    // ═══════════════════════════════════════════════════════════════════
    // SEND TO BACKEND
    // ═══════════════════════════════════════════════════════════════════

    // Save originals BEFORE hooking — sendToBackend must bypass our hooks
    const originalXHROpen = XMLHttpRequest.prototype.open;
    const originalXHRSend = XMLHttpRequest.prototype.send;

    function sendToBackend(txData) {
        try {
            const xhr = new XMLHttpRequest();
            originalXHROpen.call(xhr, 'POST', BACKEND_URL, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            originalXHRSend.call(xhr, JSON.stringify(txData));
        } catch(e) {
            // Backend not running — silently ignore
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // INTERCEPT XMLHttpRequest
    // ═══════════════════════════════════════════════════════════════════

    XMLHttpRequest.prototype.open = function(method, url) {
        this._rqU = url;
        this._rqM = method;
        return originalXHROpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function(body) {
        const url = this._rqU || '';
        const psp = detectPSP(url);
        const is3ds = is3DSRequest(url);

        if (psp || is3ds) {
            this.addEventListener('load', function() {
                try {
                    const parser = PSP_PARSERS[psp] || parseGenericResponse;
                    const parsed = parser(this.responseText, this.status);

                    if (parsed.status !== 'unknown') {
                        sendToBackend({
                            timestamp: new Date().toISOString(),
                            domain: window.location.hostname,
                            url: url.substring(0, 200),
                            psp: psp || 'unknown',
                            method: this._rqM,
                            http_status: this.status,
                            response_code: parsed.code,
                            status: parsed.status,
                            amount: parsed.amount,
                            currency: parsed.currency || 'USD',
                            three_ds: parsed.three_ds || is3ds,
                            card_bin: document.querySelector('input[name*="card"][name*="number"], input[data-stripe="number"]')?.value?.substring(0, 6) || '',
                            card_last4: document.querySelector('input[name*="card"][name*="number"], input[data-stripe="number"]')?.value?.slice(-4) || '',
                            raw_response: this.responseText?.substring(0, 500) || '',
                        });
                    }
                } catch(e) {}
            });
        }

        return originalXHRSend.apply(this, arguments);
    };

    // ═══════════════════════════════════════════════════════════════════
    // INTERCEPT fetch()
    // ═══════════════════════════════════════════════════════════════════

    const originalFetch = window.fetch;

    window.fetch = function(input, init) {
        const url = typeof input === 'string' ? input : (input?.url || '');
        const psp = detectPSP(url);
        const is3ds = is3DSRequest(url);

        if (!psp && !is3ds) {
            return originalFetch.apply(this, arguments);
        }

        return originalFetch.apply(this, arguments).then(response => {
            // Clone the response so we can read it without consuming it
            const cloned = response.clone();
            
            cloned.text().then(text => {
                try {
                    const parser = PSP_PARSERS[psp] || parseGenericResponse;
                    const parsed = parser(text, response.status);

                    if (parsed.status !== 'unknown') {
                        sendToBackend({
                            timestamp: new Date().toISOString(),
                            domain: window.location.hostname,
                            url: url.substring(0, 200),
                            psp: psp || 'unknown',
                            method: init?.method || 'GET',
                            http_status: response.status,
                            response_code: parsed.code,
                            status: parsed.status,
                            amount: parsed.amount,
                            currency: parsed.currency || 'USD',
                            three_ds: parsed.three_ds || is3ds,
                            card_bin: document.querySelector('input[name*="card"][name*="number"], input[data-stripe="number"]')?.value?.substring(0, 6) || '',
                            card_last4: document.querySelector('input[name*="card"][name*="number"], input[data-stripe="number"]')?.value?.slice(-4) || '',
                            raw_response: text?.substring(0, 500) || '',
                        });
                    }
                } catch(e) {}
            }).catch(() => {});

            return response;
        });
    };

    // ═══════════════════════════════════════════════════════════════════
    // CHECKOUT PAGE DETECTION — Monitor for order confirmation/decline
    // ═══════════════════════════════════════════════════════════════════

    function scanPageForResults() {
        const text = document.body?.innerText?.toLowerCase() || '';
        const url = window.location.href.toLowerCase();
        
        // Order confirmation patterns
        const successPatterns = [
            /order\s*(?:confirmed|placed|complete|successful)/i,
            /thank\s*you\s*for\s*(?:your\s*)?(?:order|purchase)/i,
            /payment\s*(?:successful|accepted|approved)/i,
            /order\s*#?\s*\d+/i,
        ];
        
        // Decline patterns
        const declinePatterns = [
            /payment\s*(?:declined|failed|unsuccessful|rejected)/i,
            /card\s*(?:declined|rejected|not\s*accepted)/i,
            /transaction\s*(?:failed|declined|unsuccessful)/i,
            /unable\s*to\s*process\s*(?:your\s*)?payment/i,
            /insufficient\s*funds/i,
        ];
        
        for (const pattern of successPatterns) {
            if (pattern.test(text) || pattern.test(url)) {
                sendToBackend({
                    timestamp: new Date().toISOString(),
                    domain: window.location.hostname,
                    url: window.location.href.substring(0, 200),
                    psp: 'page_detection',
                    status: 'approved',
                    response_code: 'page_confirmed',
                    notes: 'Detected via page content analysis',
                });
                return;
            }
        }
        
        for (const pattern of declinePatterns) {
            if (pattern.test(text)) {
                // Try to extract specific error message
                const errorEl = document.querySelector(
                    '.error-message, .payment-error, .decline-message, ' +
                    '[class*="error"], [class*="decline"], [class*="failed"]'
                );
                const errorText = errorEl?.textContent?.trim()?.substring(0, 200) || '';
                
                sendToBackend({
                    timestamp: new Date().toISOString(),
                    domain: window.location.hostname,
                    url: window.location.href.substring(0, 200),
                    psp: 'page_detection',
                    status: 'declined',
                    response_code: 'page_declined',
                    notes: errorText || 'Detected via page content analysis',
                });
                return;
            }
        }
    }

    // Scan after page loads and on URL changes
    if (document.readyState === 'complete') {
        setTimeout(scanPageForResults, 2000);
    } else {
        window.addEventListener('load', () => setTimeout(scanPageForResults, 2000));
    }

    // Watch for SPA navigation (URL changes without reload)
    let lastUrl = window.location.href;
    const urlObserver = new MutationObserver(() => {
        if (window.location.href !== lastUrl) {
            lastUrl = window.location.href;
            setTimeout(scanPageForResults, 2000);
        }
    });
    urlObserver.observe(document.documentElement, { childList: true, subtree: true });

})();
