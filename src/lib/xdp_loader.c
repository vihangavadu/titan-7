/* LUCID EMPIRE TITAN Class - eBPF Loader
 * Purpose: Load and manage XDP network shield at kernel level
 * Platform: Linux with kernel 5.8+
 * Dependencies: libbpf, clang, llvm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#include <bpf/bpf.h>
#include <bpf/libbpf.h>
#include <linux/if_link.h>
#include <sys/resource.h>
#include <net/if.h>

/* XDP program configuration */
#define XDP_OBJECT_PATH "./xdp_outbound.o"
#define STATS_MAP_NAME "stats_map"
#define CONFIG_MAP_NAME "config_map"

/* Interface configuration */
#define DEFAULT_INTERFACE "eth0"

/* Global state */
static struct bpf_object *obj = NULL;
static int ifindex = -1;
static int xdp_flags = 0;
static bool running = true;

/* Signal handler for graceful shutdown */
static void sig_handler(int signo)
{
    printf("\n[*] Received signal %d, shutting down...\n", signo);
    running = false;
}

/* Set resource limits for eBPF */
static int set_rlimit(void)
{
    struct rlimit r = {
        .rlim_cur = RLIM_INFINITY,
        .rlim_max = RLIM_INFINITY,
    };
    
    if (setrlimit(RLIMIT_MEMLOCK, &r)) {
        fprintf(stderr, "[-] Failed to set RLIMIT_MEMLOCK: %s\n", strerror(errno));
        return -1;
    }
    
    return 0;
}

/* Load and attach XDP program */
static int load_xdp_program(const char *interface)
{
    struct bpf_program *prog;
    int prog_fd;
    __u32 key = 0;
    __u64 value = 0;
    int err;
    
    /* Get interface index */
    ifindex = if_nametoindex(interface);
    if (ifindex == 0) {
        fprintf(stderr, "[-] Interface %s not found: %s\n", interface, strerror(errno));
        return -1;
    }
    
    printf("[*] Using interface %s (index: %d)\n", interface, ifindex);
    
    /* Load eBPF object file */
    obj = bpf_object__open_file(XDP_OBJECT_PATH, NULL);
    if (libbpf_get_error(obj)) {
        fprintf(stderr, "[-] Failed to open eBPF object: %s\n", strerror(errno));
        return -1;
    }
    
    /* Load eBPF program into kernel */
    err = bpf_object__load(obj);
    if (err) {
        fprintf(stderr, "[-] Failed to load eBPF object: %s\n", strerror(-err));
        bpf_object__close(obj);
        return -1;
    }
    
    /* Find XDP program */
    prog = bpf_object__find_program_by_name(obj, "xdp_outbound_masking");
    if (!prog) {
        fprintf(stderr, "[-] XDP program not found\n");
        bpf_object__close(obj);
        return -1;
    }
    
    prog_fd = bpf_program__fd(prog);
    
    /* Attach XDP program to interface */
    err = bpf_set_link_xdp_fd(ifindex, prog_fd, xdp_flags);
    if (err < 0) {
        fprintf(stderr, "[-] Failed to attach XDP program: %s\n", strerror(-err));
        
        /* Try with SKB mode if native mode fails */
        if (xdp_flags == 0) {
            printf("[*] Retrying with XDP_FLAGS_SKB_MODE...\n");
            xdp_flags = XDP_FLAGS_SKB_MODE;
            err = bpf_set_link_xdp_fd(ifindex, prog_fd, xdp_flags);
        }
        
        if (err < 0) {
            fprintf(stderr, "[-] XDP attachment failed completely\n");
            bpf_object__close(obj);
            return -1;
        }
    }
    
    printf("[+] XDP program attached successfully\n");
    
    /* Initialize statistics map */
    struct bpf_map *stats_map = bpf_object__find_map_by_name(obj, STATS_MAP_NAME);
    if (!stats_map) {
        fprintf(stderr, "[-] Statistics map not found\n");
        return -1;
    }
    
    /* Reset statistics counters */
    int stats_fd = bpf_map__fd(stats_map);
    for (int i = 0; i < 10; i++) {
        key = i;
        value = 0;
        bpf_map_update_elem(stats_fd, &key, &value, BPF_ANY);
    }
    
    printf("[+] Statistics initialized\n");
    
    return 0;
}

/* Detach XDP program */
static void detach_xdp_program(void)
{
    if (ifindex >= 0) {
        bpf_set_link_xdp_fd(ifindex, -1, xdp_flags);
        printf("[*] XDP program detached\n");
    }
    
    if (obj) {
        bpf_object__close(obj);
        obj = NULL;
    }
}

/* Print statistics */
static void print_stats(void)
{
    struct bpf_map *stats_map;
    int stats_fd;
    __u32 key;
    __u64 value;
    const char *stat_names[] = {
        "Packets Processed",
        "TTL Modified",
        "Window Modified", 
        "Bytes Processed",
        "Parse Errors",
        "Checksum Errors"
    };
    
    stats_map = bpf_object__find_map_by_name(obj, STATS_MAP_NAME);
    if (!stats_map) {
        fprintf(stderr, "[-] Cannot find statistics map\n");
        return;
    }
    
    stats_fd = bpf_map__fd(stats_map);
    
    printf("\n=== XDP Network Shield Statistics ===\n");
    for (int i = 0; i < 6; i++) {
        key = i;
        if (bpf_map_lookup_elem(stats_fd, &key, &value) == 0) {
            printf("%-20s: %llu\n", stat_names[i], value);
        }
    }
    printf("=====================================\n\n");
}

/* Main monitoring loop */
static void monitor_loop(void)
{
    printf("[*] Monitoring XDP network shield (Ctrl+C to stop)\n");
    
    while (running) {
        sleep(5);
        print_stats();
    }
}

/* Print usage information */
static void print_usage(const char *prog_name)
{
    printf("LUCID EMPIRE TITAN Class - XDP Network Shield\n\n");
    printf("Usage: %s [options]\n\n", prog_name);
    printf("Options:\n");
    printf("  -i, --interface IFACE  Network interface (default: %s)\n", DEFAULT_INTERFACE);
    printf("  -h, --help            Show this help\n\n");
    printf("Iron Rules Compliance:\n");
    printf("  - Requires root privileges or CAP_NET_ADMIN\n");
    printf("  - Kernel 5.8+ required for XDP support\n");
    printf("  - Interface binding is mandatory\n\n");
}

int main(int argc, char **argv)
{
    const char *interface = DEFAULT_INTERFACE;
    int opt;
    
    /* Parse command line arguments */
    static struct option long_opts[] = {
        {"interface", required_argument, 0, 'i'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };
    
    while ((opt = getopt_long(argc, argv, "i:h", long_opts, NULL)) != -1) {
        switch (opt) {
        case 'i':
            interface = optarg;
            break;
        case 'h':
            print_usage(argv[0]);
            return 0;
        default:
            print_usage(argv[0]);
            return 1;
        }
    }
    
    printf("LUCID EMPIRE TITAN Class - XDP Network Shield\n");
    printf("==========================================\n");
    
    /* Verify privileges (Iron Rule LR-1) */
    if (geteuid() != 0) {
        fprintf(stderr, "[-] Error: This program requires root privileges (Iron Rule LR-1)\n");
        fprintf(stderr, "[-] Run with: sudo %s\n", argv[0]);
        return 1;
    }
    
    /* Set up signal handlers */
    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);
    
    /* Set resource limits */
    if (set_rlimit() < 0) {
        return 1;
    }
    
    /* Load XDP program */
    if (load_xdp_program(interface) < 0) {
        fprintf(stderr, "[-] Failed to load XDP program\n");
        return 1;
    }
    
    printf("[+] Network shield active - OS masquerading enabled\n");
    printf("[+] TTL: Linux(64) -> Windows(128)\n");
    printf("[+] TCP Window: Linux(5840) -> Windows(65535)\n");
    
    /* Monitor statistics */
    monitor_loop();
    
    /* Cleanup */
    detach_xdp_program();
    printf("[*] Shutdown complete\n");
    
    return 0;
}
