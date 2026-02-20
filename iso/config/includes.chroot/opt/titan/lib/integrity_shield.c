/*
 * TITAN V7.0.3 SINGULARITY — Integrity Shield
 * LD_PRELOAD library that hides v4l2loopback from KYC provider detection.
 *
 * KYC providers (Jumio, Onfido, Veriff, Au10tix) detect virtual cameras by:
 * 1. Reading /proc/modules to find v4l2loopback
 * 2. Reading /sys/module/v4l2loopback/
 * 3. Checking USB device tree for virtual devices
 * 4. Enumerating /dev/video* and checking driver names via ioctl
 *
 * This library hooks open(), read(), and fopen() to filter out
 * v4l2loopback references from these system files.
 *
 * Build:
 *   gcc -shared -fPIC -o integrity_shield.so integrity_shield.c -ldl
 *
 * Usage:
 *   LD_PRELOAD=/opt/titan/lib/integrity_shield.so firefox
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <dlfcn.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>

/* Strings to filter from /proc/modules and similar files */
static const char *FILTER_STRINGS[] = {
    "v4l2loopback",
    "v4l2_loopback",
    "loopback_video",
    "virtual_camera",
    "vcam",
    NULL
};

/* Paths that should have v4l2loopback references filtered */
static const char *FILTER_PATHS[] = {
    "/proc/modules",
    "/proc/bus/usb",
    "/sys/module/",
    "/sys/bus/usb/",
    "/sys/devices/virtual/video4linux/",
    NULL
};

/* Original function pointers */
static FILE *(*real_fopen)(const char *, const char *) = NULL;
static ssize_t (*real_read)(int, void *, size_t) = NULL;
static int (*real_open)(const char *, int, ...) = NULL;

/* Check if path should be filtered */
static int should_filter_path(const char *path) {
    if (!path) return 0;
    
    for (int i = 0; FILTER_PATHS[i]; i++) {
        if (strstr(path, FILTER_PATHS[i])) return 1;
    }
    return 0;
}

/* Check if a line contains v4l2loopback references */
static int line_contains_filter(const char *line) {
    if (!line) return 0;
    
    for (int i = 0; FILTER_STRINGS[i]; i++) {
        if (strstr(line, FILTER_STRINGS[i])) return 1;
    }
    return 0;
}

/* Block access to v4l2loopback sysfs entries */
static int should_block_path(const char *path) {
    if (!path) return 0;
    
    if (strstr(path, "/sys/module/v4l2loopback")) return 1;
    if (strstr(path, "/sys/module/v4l2_loopback")) return 1;
    
    return 0;
}

/* Initialize real function pointers */
static void init_real_functions(void) {
    if (!real_fopen) real_fopen = dlsym(RTLD_NEXT, "fopen");
    if (!real_read) real_read = dlsym(RTLD_NEXT, "read");
    if (!real_open) real_open = dlsym(RTLD_NEXT, "open");
}

/*
 * Hooked fopen() — intercepts /proc/modules reads
 * Returns a filtered version that excludes v4l2loopback lines
 */
FILE *fopen(const char *pathname, const char *mode) {
    init_real_functions();
    
    /* Block sysfs v4l2loopback paths entirely */
    if (should_block_path(pathname)) {
        errno = ENOENT;
        return NULL;
    }
    
    /* For /proc/modules, create a filtered temp file */
    if (pathname && strcmp(pathname, "/proc/modules") == 0 &&
        getenv("TITAN_HIDE_V4L2LOOPBACK")) {
        
        FILE *real_file = real_fopen(pathname, mode);
        if (!real_file) return NULL;
        
        /* Create temp file with filtered content */
        FILE *tmp = tmpfile();
        if (!tmp) {
            fclose(real_file);
            return real_fopen(pathname, mode);
        }
        
        char line[4096];
        while (fgets(line, sizeof(line), real_file)) {
            if (!line_contains_filter(line)) {
                fputs(line, tmp);
            }
        }
        fclose(real_file);
        
        rewind(tmp);
        return tmp;
    }
    
    return real_fopen(pathname, mode);
}

/*
 * Hooked open() — blocks access to v4l2loopback sysfs entries
 */
int open(const char *pathname, int flags, ...) {
    init_real_functions();
    
    if (should_block_path(pathname) && getenv("TITAN_HIDE_V4L2LOOPBACK")) {
        errno = ENOENT;
        return -1;
    }
    
    /* Handle variadic mode argument */
    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode_t m = va_arg(ap, mode_t);
        va_end(ap);
        return real_open(pathname, flags, m);
    }
    
    return real_open(pathname, flags);
}

/*
 * Hooked read() — filters v4l2loopback from read buffers
 * This catches cases where /proc/modules is read via read() instead of fgets()
 */
ssize_t read(int fd, void *buf, size_t count) {
    init_real_functions();
    
    ssize_t ret = real_read(fd, buf, count);
    
    if (ret > 0 && getenv("TITAN_HIDE_V4L2LOOPBACK")) {
        /* Check if this fd is /proc/modules by looking at /proc/self/fd/N */
        char fd_path[64];
        char link_target[256];
        snprintf(fd_path, sizeof(fd_path), "/proc/self/fd/%d", fd);
        ssize_t link_len = readlink(fd_path, link_target, sizeof(link_target) - 1);
        
        if (link_len > 0) {
            link_target[link_len] = '\0';
            
            if (should_filter_path(link_target)) {
                /* Filter v4l2loopback lines from buffer */
                char *src = (char *)buf;
                char *dst = (char *)buf;
                char *end = src + ret;
                ssize_t new_len = 0;
                
                while (src < end) {
                    /* Find end of line */
                    char *eol = memchr(src, '\n', end - src);
                    size_t line_len = eol ? (size_t)(eol - src + 1) : (size_t)(end - src);
                    
                    /* Check if line should be filtered */
                    char line_buf[4096];
                    size_t copy_len = line_len < sizeof(line_buf) - 1 ? line_len : sizeof(line_buf) - 1;
                    memcpy(line_buf, src, copy_len);
                    line_buf[copy_len] = '\0';
                    
                    if (!line_contains_filter(line_buf)) {
                        if (dst != src) memmove(dst, src, line_len);
                        dst += line_len;
                        new_len += line_len;
                    }
                    
                    src += line_len;
                }
                
                return new_len;
            }
        }
    }
    
    return ret;
}
