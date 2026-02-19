// LUCID EMPIRE :: HARDWARE SHIELD (LD_PRELOAD)
// AUTHORITY: Dva.12 | TITAN V7.0 SINGULARITY
// PURPOSE: Force Standard Firefox/Chrome to report fake hardware without extensions
// 
// This is the core of the "Naked Browser Protocol" - we intercept system calls
// at the library level, making vanilla browsers lie about the machine they run on.

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>

// ============================================================================
// CONFIGURATION: Read from profile or use defaults
// ============================================================================
static char* gpu_vendor = NULL;
static char* gpu_renderer = NULL;
static int cpu_cores = 0;
static int initialized = 0;

static void load_hardware_config(void) {
    if (initialized) return;
    initialized = 1;
    
    // Try to load from active profile
    char* profile_path = getenv("LUCID_PROFILE_PATH");
    if (!profile_path) profile_path = "/opt/lucid-empire/profiles/active";
    
    char config_path[512];
    snprintf(config_path, sizeof(config_path), "%s/hardware.conf", profile_path);
    
    FILE* f = fopen(config_path, "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            char key[64], value[192];
            if (sscanf(line, "%63[^=]=%191[^\n]", key, value) == 2) {
                if (strcmp(key, "GPU_VENDOR") == 0) {
                    gpu_vendor = strdup(value);
                } else if (strcmp(key, "GPU_RENDERER") == 0) {
                    gpu_renderer = strdup(value);
                } else if (strcmp(key, "CPU_CORES") == 0) {
                    cpu_cores = atoi(value);
                }
            }
        }
        fclose(f);
    }
    
    // Defaults: High-end Windows gaming rig (most common for ecommerce)
    if (!gpu_vendor) gpu_vendor = "Google Inc. (NVIDIA)";
    if (!gpu_renderer) gpu_renderer = "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)";
    if (!cpu_cores) cpu_cores = 16;
}

// ============================================================================
// TARGET 1: WebGL Vendor/Renderer Spoofing
// Browsers call glGetString to identify GPU - we intercept and lie
// ============================================================================
typedef const unsigned char* (*glGetString_t)(unsigned int);
typedef const unsigned char* (*glGetStringi_t)(unsigned int, unsigned int);

const unsigned char* glGetString(unsigned int name) {
    load_hardware_config();
    
    // GL_VENDOR = 0x1F00
    // GL_RENDERER = 0x1F01  
    // GL_VERSION = 0x1F02
    // GL_SHADING_LANGUAGE_VERSION = 0x8B8C
    
    switch (name) {
        case 0x1F00: // GL_VENDOR
            return (const unsigned char*)gpu_vendor;
        case 0x1F01: // GL_RENDERER
            return (const unsigned char*)gpu_renderer;
        case 0x1F02: // GL_VERSION
            return (const unsigned char*)"OpenGL ES 3.0 (ANGLE 2.1.0.4)";
        case 0x8B8C: // GL_SHADING_LANGUAGE_VERSION
            return (const unsigned char*)"OpenGL ES GLSL ES 3.00 (ANGLE 2.1.0.4)";
    }
    
    // Fallback to real function
    glGetString_t real_fn = (glGetString_t)dlsym(RTLD_NEXT, "glGetString");
    if (real_fn) return real_fn(name);
    return NULL;
}

const unsigned char* glGetStringi(unsigned int name, unsigned int index) {
    load_hardware_config();
    
    // GL_EXTENSIONS indexed query - return common Windows extensions
    if (name == 0x1F03 && index == 0) { // GL_EXTENSIONS
        return (const unsigned char*)"GL_ANGLE_instanced_arrays";
    }
    
    glGetStringi_t real_fn = (glGetStringi_t)dlsym(RTLD_NEXT, "glGetStringi");
    if (real_fn) return real_fn(name, index);
    return NULL;
}

// ============================================================================
// TARGET 2: CPU Information Spoofing
// Intercept sysconf to lie about CPU core count
// ============================================================================
typedef long (*sysconf_t)(int);

long sysconf(int name) {
    load_hardware_config();
    
    // _SC_NPROCESSORS_ONLN = 84 (Linux)
    // _SC_NPROCESSORS_CONF = 83 (Linux)
    if (name == 84 || name == 83) {
        return cpu_cores;
    }
    
    sysconf_t real_fn = (sysconf_t)dlsym(RTLD_NEXT, "sysconf");
    if (real_fn) return real_fn(name);
    return -1;
}

// ============================================================================
// TARGET 3: /proc/cpuinfo Redirection
// When browser reads /proc/cpuinfo, serve fake file instead
// ============================================================================
typedef FILE* (*fopen_t)(const char*, const char*);
typedef int (*open_t)(const char*, int, ...);

static const char* FAKE_CPUINFO_PATH = "/opt/lucid-empire/profiles/active/cpuinfo";

FILE* fopen(const char* path, const char* mode) {
    load_hardware_config();
    
    fopen_t real_fopen = (fopen_t)dlsym(RTLD_NEXT, "fopen");
    if (!real_fopen) return NULL;
    
    // Redirect /proc/cpuinfo to our fake version
    if (path && strcmp(path, "/proc/cpuinfo") == 0) {
        char* profile_path = getenv("LUCID_PROFILE_PATH");
        if (profile_path) {
            char fake_path[512];
            snprintf(fake_path, sizeof(fake_path), "%s/cpuinfo", profile_path);
            FILE* f = real_fopen(fake_path, mode);
            if (f) return f;
        }
        // Fallback to default fake
        FILE* f = real_fopen(FAKE_CPUINFO_PATH, mode);
        if (f) return f;
    }
    
    // Redirect /proc/meminfo for RAM spoofing
    if (path && strcmp(path, "/proc/meminfo") == 0) {
        char* profile_path = getenv("LUCID_PROFILE_PATH");
        if (profile_path) {
            char fake_path[512];
            snprintf(fake_path, sizeof(fake_path), "%s/meminfo", profile_path);
            FILE* f = real_fopen(fake_path, mode);
            if (f) return f;
        }
    }
    
    return real_fopen(path, mode);
}

// ============================================================================
// TARGET 4: Audio Context Spoofing
// Browsers use audio fingerprinting - we add consistent noise
// ============================================================================
typedef int (*pa_context_get_server_info_t)(void*, void*, void*);

// Note: Full audio spoofing requires hooking into PulseAudio/ALSA
// This is a placeholder for the architecture - full implementation
// intercepts AudioContext.getChannelData and adds deterministic noise

// ============================================================================
// TARGET 5: Canvas Fingerprinting Defense
// Inject imperceptible noise into canvas operations
// ============================================================================
// Note: Canvas spoofing at LD_PRELOAD level requires hooking into
// the graphics library. For maximum stealth, we use the profile-based
// approach where canvas noise parameters are stored in the profile
// and applied via browser content script injection at runtime.
// See: /opt/lucid-empire/content-scripts/canvas-shield.js

// ============================================================================
// TARGET 6: Screen Resolution Spoofing
// ============================================================================
typedef int (*XDisplayWidth_t)(void*, int);
typedef int (*XDisplayHeight_t)(void*, int);

int XDisplayWidth(void* display, int screen) {
    char* override = getenv("LUCID_SCREEN_WIDTH");
    if (override) return atoi(override);
    
    XDisplayWidth_t real_fn = (XDisplayWidth_t)dlsym(RTLD_NEXT, "XDisplayWidth");
    if (real_fn) return real_fn(display, screen);
    return 1920;
}

int XDisplayHeight(void* display, int screen) {
    char* override = getenv("LUCID_SCREEN_HEIGHT");
    if (override) return atoi(override);
    
    XDisplayHeight_t real_fn = (XDisplayHeight_t)dlsym(RTLD_NEXT, "XDisplayHeight");
    if (real_fn) return real_fn(display, screen);
    return 1080;
}

// ============================================================================
// NAVIGATOR.WEBDRIVER DEFENSE
// This flag is automatically FALSE when using standard Firefox
// because we're not using WebDriver automation at runtime.
// The Genesis Engine uses headless automation, then TERMINATES.
// When user opens Firefox manually, webdriver flag is naturally false.
// ============================================================================

// ============================================================================
// INITIALIZATION: Run on library load
// ============================================================================
__attribute__((constructor))
static void hardware_shield_init(void) {
    load_hardware_config();
    
    // Set environment hints for nested processes
    setenv("LIBGL_ALWAYS_SOFTWARE", "0", 0);
    
    // Log shield activation (only in debug mode)
    if (getenv("LUCID_DEBUG")) {
        fprintf(stderr, "[LUCID] Hardware Shield Active: %s / %d cores\n", 
                gpu_renderer, cpu_cores);
    }
}
