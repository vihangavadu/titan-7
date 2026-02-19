// LUCID EMPIRE TITAN - TCP Fingerprint Masquerade eBPF Program
// Kernel-level packet manipulation for OS fingerprint spoofing
// Requires Linux kernel 5.15+ with BTF support

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

// --- SELF-SUFFICIENT DEFINITIONS ---
// Define TC action codes explicitly (not all systems have linux/pkt_cls.h)
#ifndef TC_ACT_OK
#define TC_ACT_OK 0
#endif

#ifndef TC_ACT_SHOT
#define TC_ACT_SHOT 2
#endif

#ifndef TC_ACT_UNSPEC
#define TC_ACT_UNSPEC -1
#endif

// Define standard integer types if missing (fixes asm/types.h not found)
#ifndef __u8_defined
typedef unsigned char __u8;
typedef unsigned short __u16;
typedef unsigned int __u32;
typedef unsigned long long __u64;
typedef signed char __s8;
typedef signed short __s16;
typedef signed int __s32;
typedef signed long long __s64;
#define __u8_defined
#endif
// --- END SELF-SUFFICIENT DEFINITIONS ---

// TCP fingerprint configuration map
struct tcp_config {
    __u8 ttl;                  // Time-To-Live value
    __u16 window_size;         // TCP window size
    __u16 mss;                 // Maximum Segment Size
    __u8 window_scale;         // Window scaling factor
    __u8 sack_permitted;       // SACK permitted flag
    __u8 timestamps;           // TCP timestamps enabled
    __u32 timestamp_offset;    // Timestamp offset for aging
};

// OS fingerprint profiles
#define OS_WINDOWS   1
#define OS_MACOS     2
#define OS_LINUX     3
#define OS_IOS       4
#define OS_ANDROID   5

// BPF maps for configuration
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct tcp_config);
} tcp_config_map SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u32);
} stats_map SEC(".maps");

// Predefined OS profiles
static __always_inline void get_windows_profile(struct tcp_config *config) {
    config->ttl = 128;
    config->window_size = 65535;
    config->mss = 1460;
    config->window_scale = 8;
    config->sack_permitted = 1;
    config->timestamps = 0;  // Windows often disables timestamps
}

static __always_inline void get_macos_profile(struct tcp_config *config) {
    config->ttl = 64;
    config->window_size = 65535;
    config->mss = 1460;
    config->window_scale = 6;
    config->sack_permitted = 1;
    config->timestamps = 1;
}

static __always_inline void get_linux_profile(struct tcp_config *config) {
    config->ttl = 64;
    config->window_size = 29200;
    config->mss = 1460;
    config->window_scale = 7;
    config->sack_permitted = 1;
    config->timestamps = 1;
}

// Recalculate IP header checksum
static __always_inline __u16 csum_fold_helper(__u64 csum) {
    int i;
    for (i = 0; i < 4; i++) {
        if (csum >> 16)
            csum = (csum & 0xffff) + (csum >> 16);
    }
    return ~csum;
}

static __always_inline void update_ip_checksum(struct iphdr *iph) {
    __u16 *ptr = (__u16 *)iph;
    __u32 csum = 0;
    int i;
    
    iph->check = 0;
    for (i = 0; i < (int)sizeof(*iph) >> 1; i++)
        csum += *ptr++;
    
    iph->check = csum_fold_helper(csum);
}

// Update TCP checksum after modifications
static __always_inline void update_tcp_checksum(struct iphdr *iph, struct tcphdr *tcph, void *data_end) {
    __u32 csum = 0;
    __u16 *ptr;
    __u32 tcp_len = bpf_ntohs(iph->tot_len) - (iph->ihl << 2);
    
    // Pseudo header
    csum += (iph->saddr >> 16) & 0xFFFF;
    csum += iph->saddr & 0xFFFF;
    csum += (iph->daddr >> 16) & 0xFFFF;
    csum += iph->daddr & 0xFFFF;
    csum += bpf_htons(IPPROTO_TCP);
    csum += bpf_htons(tcp_len);
    
    // TCP header + data
    tcph->check = 0;
    ptr = (__u16 *)tcph;
    
    #pragma unroll
    for (int i = 0; i < 10; i++) {  // First 20 bytes of TCP header
        if ((void *)(ptr + 1) > data_end)
            break;
        csum += *ptr++;
    }
    
    tcph->check = csum_fold_helper(csum);
}

// Main XDP program for egress packet modification
SEC("xdp")
int tcp_fingerprint_xdp(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    // Parse Ethernet header
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;
    
    // Only process IPv4
    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;
    
    // Parse IP header
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end)
        return XDP_PASS;
    
    // Only process TCP
    if (iph->protocol != IPPROTO_TCP)
        return XDP_PASS;
    
    // Parse TCP header
    struct tcphdr *tcph = (void *)iph + (iph->ihl << 2);
    if ((void *)(tcph + 1) > data_end)
        return XDP_PASS;
    
    // Get configuration from map
    __u32 key = 0;
    struct tcp_config *config = bpf_map_lookup_elem(&tcp_config_map, &key);
    
    if (!config) {
        // Use default Windows profile if no config
        struct tcp_config default_config;
        get_windows_profile(&default_config);
        
        // Apply TTL modification
        iph->ttl = default_config.ttl;
        
        // Apply window size (only for SYN packets)
        if (tcph->syn && !tcph->ack) {
            tcph->window = bpf_htons(default_config.window_size);
        }
    } else {
        // Apply custom configuration
        iph->ttl = config->ttl;
        
        if (tcph->syn && !tcph->ack) {
            tcph->window = bpf_htons(config->window_size);
        }
        
        // ── TCP Timestamp Value Randomization ────────────────────
        // Prevents uptime leakage via tsval. Real Windows users have
        // randomized boot-time offsets. Without this, tsval reveals
        // exact system uptime → detectable as Linux/server.
        if (config->timestamp_offset != 0) {
            __u8 tcp_hdr_len = tcph->doff * 4;
            if (tcp_hdr_len > 20) {
                __u8 *opts = (__u8 *)tcph + 20;
                __u8 *opts_end = (__u8 *)tcph + tcp_hdr_len;
                if ((void *)opts_end <= data_end) {
                    #pragma unroll
                    for (int i = 0; i < 40 && opts + i < opts_end; i++) {
                        if (opts[i] == 0) break;      // EOL
                        if (opts[i] == 1) continue;    // NOP
                        if (opts[i] == 8 && i + 9 < tcp_hdr_len - 20) {
                            // TCP Timestamp option: kind=8, len=10, tsval(4), tsecr(4)
                            __u32 *tsval = (__u32 *)(opts + i + 2);
                            if ((void *)(tsval + 1) <= data_end) {
                                *tsval = bpf_htonl(bpf_ntohl(*tsval) + config->timestamp_offset);
                            }
                            break;
                        }
                        __u8 opt_len = opts[i + 1];
                        if (opt_len < 2) break;
                        i += opt_len - 1;
                    }
                }
            }
        }
        
        // ── MSS Clamping ─────────────────────────────────────────
        // VPNs reduce MTU (typically 1300-1420). If MSS < 1460,
        // it reveals tunnel overhead. Clamp to 1460 (standard Ethernet)
        // to match native Windows connection without VPN.
        if (tcph->syn && config->mss > 0) {
            __u8 tcp_hdr_len2 = tcph->doff * 4;
            if (tcp_hdr_len2 > 20) {
                __u8 *opts2 = (__u8 *)tcph + 20;
                __u8 *opts2_end = (__u8 *)tcph + tcp_hdr_len2;
                if ((void *)opts2_end <= data_end) {
                    #pragma unroll
                    for (int j = 0; j < 40 && opts2 + j < opts2_end; j++) {
                        if (opts2[j] == 0) break;
                        if (opts2[j] == 1) continue;
                        if (opts2[j] == 2 && j + 3 < tcp_hdr_len2 - 20) {
                            // MSS option: kind=2, len=4, value(2)
                            __u16 *mss_val = (__u16 *)(opts2 + j + 2);
                            if ((void *)(mss_val + 1) <= data_end) {
                                __u16 current_mss = bpf_ntohs(*mss_val);
                                if (current_mss < config->mss) {
                                    *mss_val = bpf_htons(config->mss);
                                }
                            }
                            break;
                        }
                        __u8 opt_len2 = opts2[j + 1];
                        if (opt_len2 < 2) break;
                        j += opt_len2 - 1;
                    }
                }
            }
        }
    }
    
    // Recalculate checksums
    update_ip_checksum(iph);
    update_tcp_checksum(iph, tcph, data_end);
    
    // Update stats
    __u32 stats_key = 0;
    __u32 *packets = bpf_map_lookup_elem(&stats_map, &stats_key);
    if (packets)
        __sync_fetch_and_add(packets, 1);
    
    return XDP_PASS;
}

// TC (Traffic Control) program for more complex modifications
SEC("tc")
int tcp_fingerprint_tc(struct __sk_buff *skb) {
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return TC_ACT_OK;
    
    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return TC_ACT_OK;
    
    struct iphdr *iph = (void *)(eth + 1);
    if ((void *)(iph + 1) > data_end)
        return TC_ACT_OK;
    
    if (iph->protocol != IPPROTO_TCP)
        return TC_ACT_OK;
    
    struct tcphdr *tcph = (void *)iph + (iph->ihl << 2);
    if ((void *)(tcph + 1) > data_end)
        return TC_ACT_OK;
    
    // Get config
    __u32 key = 0;
    struct tcp_config *config = bpf_map_lookup_elem(&tcp_config_map, &key);
    if (!config)
        return TC_ACT_OK;
    
    // Modify TTL
    iph->ttl = config->ttl;
    
    // Modify window for SYN packets
    if (tcph->syn) {
        tcph->window = bpf_htons(config->window_size);
    }
    
    // Recompute checksums
    bpf_l3_csum_replace(skb, 
        sizeof(struct ethhdr) + offsetof(struct iphdr, check),
        0, 0, 0);
    
    return TC_ACT_OK;
}

char LICENSE[] SEC("license") = "GPL";
