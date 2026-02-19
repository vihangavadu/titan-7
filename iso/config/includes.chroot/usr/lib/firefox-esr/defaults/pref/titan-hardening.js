// TITAN V7.0 SINGULARITY — Firefox ESR Hardening Defaults
// Applied at chroot level for vanilla Firefox ESR fallback
// Camoufox has its own hardening; this covers the ESR safety net

// ═══ WebRTC Leak Prevention ═══
pref("media.peerconnection.enabled", false);
pref("media.peerconnection.ice.default_address_only", true);
pref("media.peerconnection.ice.no_host", true);
pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);
pref("media.peerconnection.turn.disable", true);

// ═══ DNS Privacy (DoH mode 3 = HTTPS only) ═══
pref("network.trr.mode", 3);
pref("network.trr.uri", "https://cloudflare-dns.com/dns-query");
pref("network.trr.bootstrapAddr", "1.1.1.1");

// ═══ Anti-Automation Detection ═══
pref("dom.webdriver.enabled", false);

// ═══ Disable Leaky APIs ═══
pref("dom.battery.enabled", false);
pref("device.sensors.enabled", false);
pref("dom.gamepad.enabled", false);
pref("dom.vr.enabled", false);
pref("dom.vibrator.enabled", false);
pref("geo.enabled", false);

// ═══ Telemetry — All Disabled ═══
pref("toolkit.telemetry.enabled", false);
pref("toolkit.telemetry.unified", false);
pref("toolkit.telemetry.archive.enabled", false);
pref("toolkit.telemetry.updatePing.enabled", false);
pref("toolkit.telemetry.bhrPing.enabled", false);
pref("toolkit.telemetry.firstShutdownPing.enabled", false);
pref("toolkit.telemetry.newProfilePing.enabled", false);
pref("datareporting.healthreport.uploadEnabled", false);

// ═══ Safe Browsing — Disabled (phones home to Google) ═══
pref("browser.safebrowsing.malware.enabled", false);
pref("browser.safebrowsing.phishing.enabled", false);
pref("browser.safebrowsing.downloads.enabled", false);
pref("browser.safebrowsing.downloads.remote.enabled", false);

// ═══ Captive Portal — Disabled (leaks real IP) ═══
pref("network.captive-portal-service.enabled", false);
pref("captivedetect.canonicalURL", "");

// ═══ Auto-Update — Disabled (ISO is versioned) ═══
pref("app.update.enabled", false);
pref("app.update.auto", false);
pref("extensions.update.enabled", false);

// ═══ Privacy Hardening ═══
pref("privacy.resistFingerprinting", false);
pref("privacy.trackingprotection.enabled", true);
pref("network.cookie.cookieBehavior", 1);
pref("dom.storage.enabled", true);

// ═══ Network Prefetch — Disabled ═══
pref("network.prefetch-next", false);
pref("network.dns.disablePrefetch", true);
pref("network.http.speculative-parallel-limit", 0);
