/**
 * TITAN V7.0.3 — TX Monitor Background Service Worker
 * 
 * Uses webRequest API to monitor payment-related HTTP responses
 * at the network level (catches requests content scripts might miss).
 */

const BACKEND_URL = 'http://127.0.0.1:7443/api/tx';

const PAYMENT_URL_FILTERS = [
    '*://api.stripe.com/*',
    '*://*.adyen.com/*',
    '*://*.braintreegateway.com/*',
    '*://*.braintree-api.com/*',
    '*://accept.authorize.net/*',
    '*://*.authorize.net/*',
    '*://*.cybersource.com/*',
    '*://*.worldpay.com/*',
    '*://api.checkout.com/*',
    '*://*.squareup.com/*',
    '*://api.paypal.com/*',
    '*://*.cardinalcommerce.com/*',
    '*://*.3dsecure.io/*',
    '*://*.arcot.com/*',
];

// Track payment requests
chrome.webRequest.onCompleted.addListener(
    function(details) {
        if (details.statusCode && details.url) {
            // Determine PSP from URL
            let psp = 'unknown';
            const url = details.url.toLowerCase();
            if (url.includes('stripe.com')) psp = 'stripe';
            else if (url.includes('adyen.com')) psp = 'adyen';
            else if (url.includes('braintree')) psp = 'braintree';
            else if (url.includes('authorize.net')) psp = 'authorize_net';
            else if (url.includes('cybersource')) psp = 'cybersource';
            else if (url.includes('worldpay')) psp = 'worldpay';
            else if (url.includes('checkout.com')) psp = 'checkout_com';
            else if (url.includes('paypal.com')) psp = 'paypal';
            else if (url.includes('cardinal') || url.includes('3dsecure') || url.includes('arcot')) psp = '3ds_provider';

            // Determine if this is a 3DS request
            const is3DS = /3ds|cardinal|arcot|threedsecure/i.test(url);

            // Log network-level payment request
            const txData = {
                timestamp: new Date().toISOString(),
                domain: new URL(details.initiator || details.url).hostname || 'unknown',
                url: details.url.substring(0, 200),
                psp: psp,
                http_status: details.statusCode,
                method: details.method,
                status: details.statusCode >= 200 && details.statusCode < 300 ? 'network_ok' : 'network_error',
                response_code: `http_${details.statusCode}`,
                three_ds: is3DS,
                notes: `Network-level capture. Tab: ${details.tabId}`,
            };

            // Send to backend
            fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(txData),
            }).catch(() => {});
        }
    },
    { urls: PAYMENT_URL_FILTERS },
    []
);

// Track 3DS redirects
chrome.webRequest.onBeforeRedirect.addListener(
    function(details) {
        const url = details.redirectUrl || '';
        if (/3dsecure|cardinal|arcot|threedsmethod/i.test(url)) {
            fetch(BACKEND_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    timestamp: new Date().toISOString(),
                    domain: new URL(details.initiator || details.url).hostname || 'unknown',
                    url: url.substring(0, 200),
                    psp: '3ds_redirect',
                    status: 'pending_3ds',
                    response_code: '3ds_redirect',
                    three_ds: true,
                    notes: `3DS redirect detected. From: ${details.url.substring(0, 100)}`,
                }),
            }).catch(() => {});
        }
    },
    { urls: ['<all_urls>'] },
    []
);

// Heartbeat — check if backend is alive every 60s
setInterval(() => {
    fetch('http://127.0.0.1:7443/api/heartbeat')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'alive') {
                console.log('[TX Monitor] Backend alive');
            }
        })
        .catch(() => {
            console.log('[TX Monitor] Backend not running');
        });
}, 60000);
