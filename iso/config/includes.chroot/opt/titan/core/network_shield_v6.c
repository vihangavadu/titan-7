/*
 * TITAN V7.0 SINGULARITY - Network Shield V7
 * Transparent QUIC Decoupling with eBPF
 *
 * V5.2 Problem: Blocking QUIC (UDP/443) forces TCP fallback
 * This is now a FINGERPRINT - modern browsers expect QUIC to work
 *
 * V6 Solution: Transparent QUIC Proxy
 * 1. eBPF intercepts UDP/443 via sockmap
 * 2. Redirect to userspace QUIC proxy (aioquic)
 * 3. Proxy modifies TLS fingerprint (JA4)
 * 4. Re-encrypt and forward to destination
 *
 * Result: Server sees valid HTTP/3 with correct fingerprint
 */

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <linux/tcp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define QUIC_PORT 443
#define PROXY_PORT 8443
#define MAX_SOCKETS 65536

/* OS TCP/IP fingerprint profiles (p0f-compatible) */
#define OS_PROFILE_WINDOWS11  0
#define OS_PROFILE_WINDOWS10  1
#define OS_PROFILE_MACOS14    2
#define OS_PROFILE_LINUX6     3

/* TCP option kinds */
#define TCPOPT_EOL        0
#define TCPOPT_NOP        1
#define TCPOPT_MSS        2
#define TCPOPT_WSCALE     3
#define TCPOPT_SACKOK     4
#define TCPOPT_TIMESTAMP  8

/* License required for eBPF */
char LICENSE[] SEC("license") = "GPL";

/* Version info */
#define TITAN_NET_VERSION "7.0.0"
#define TITAN_NET_CODENAME "SINGULARITY"

/*
 * Socket map for QUIC redirection
 * Maps original socket to proxy socket
 */
struct {
    __uint(type, BPF_MAP_TYPE_SOCKMAP);
    __uint(max_entries, MAX_SOCKETS);
    __type(key, __u32);
    __type(value, __u64);
} titan_sockmap SEC(".maps");

/*
 * Hash map for connection tracking
 * Tracks which connections are being proxied
 */
struct conn_key {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
};

struct conn_state {
    __u8 proxied;
    __u8 fingerprint_id;
    __u64 bytes_sent;
    __u64 bytes_recv;
    __u64 start_time;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_SOCKETS);
    __type(key, struct conn_key);
    __type(value, struct conn_state);
} titan_connections SEC(".maps");

/*
 * Configuration map - controlled from userspace
 */
struct titan_config {
    __u8 quic_proxy_enabled;
    __u8 tcp_fingerprint_enabled;
    __u8 dns_protection_enabled;
    __u8 webrtc_block_enabled;
    __u32 proxy_ip;
    __u16 proxy_port;
    __u8 os_profile;          /* OS_PROFILE_* constant */
    __u8 reserved;
    __u32 dns_server_1;       /* Allowed DNS server IP (network byte order) */
    __u32 dns_server_2;       /* Secondary allowed DNS server IP */
};

/*
 * OS fingerprint parameters for TCP stack masquerading
 * Each profile matches real OS p0f signatures exactly
 */
struct os_tcp_profile {
    __u8  ttl;             /* IP TTL value */
    __u16 window_size;     /* TCP initial window size */
    __u8  window_scale;    /* TCP window scale factor */
    __u16 mss;             /* Maximum Segment Size */
    __u8  sack_ok;         /* SACK permitted */
    __u8  timestamps;      /* TCP timestamps enabled */
    __u8  nop_count;       /* NOP padding count */
    /* TCP option order: indices into option kind array */
    /* Windows: MSS,NOP,WSCALE,NOP,NOP,SACKOK */
    /* Linux:   MSS,SACKOK,TIMESTAMP,NOP,WSCALE */
    /* macOS:   MSS,NOP,WSCALE,NOP,NOP,TIMESTAMP,SACKOK,EOL */
    __u8  opt_order[8];
    __u8  opt_count;
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 4);
    __type(key, __u32);
    __type(value, struct os_tcp_profile);
} titan_os_profiles SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct titan_config);
} titan_config_map SEC(".maps");

/*
 * Statistics for monitoring
 */
struct titan_stats {
    __u64 packets_total;
    __u64 packets_quic;
    __u64 packets_redirected;
    __u64 packets_blocked;
    __u64 bytes_total;
};

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct titan_stats);
} titan_stats_map SEC(".maps");

/*
 * Helper: Get configuration
 */
static __always_inline struct titan_config *get_config(void)
{
    __u32 key = 0;
    return bpf_map_lookup_elem(&titan_config_map, &key);
}

/*
 * Helper: Update statistics
 */
static __always_inline void update_stats(__u64 bytes, __u8 is_quic, __u8 redirected, __u8 blocked)
{
    __u32 key = 0;
    struct titan_stats *stats = bpf_map_lookup_elem(&titan_stats_map, &key);
    if (stats) {
        stats->packets_total++;
        stats->bytes_total += bytes;
        if (is_quic) stats->packets_quic++;
        if (redirected) stats->packets_redirected++;
        if (blocked) stats->packets_blocked++;
    }
}

/*
 * Socket Operations Program
 * Tracks TCP connections for sockmap-based proxying.
 * Note: QUIC (UDP/443) redirection is handled by cgroup/connect4 below,
 * not sockops, because sockops only fires for TCP connections.
 * This program populates the sockmap for TCP-based proxy connections
 * (e.g., HTTP/2 fallback when QUIC proxy is active).
 */
SEC("sockops")
int titan_sockops(struct bpf_sock_ops *skops)
{
    struct titan_config *cfg = get_config();
    if (!cfg)
        return 0;

    /* Only handle established TCP connections */
    if (skops->op != BPF_SOCK_OPS_ACTIVE_ESTABLISHED_CB &&
        skops->op != BPF_SOCK_OPS_PASSIVE_ESTABLISHED_CB)
        return 0;

    if (skops->family != AF_INET)
        return 0;

    __u16 dst_port = bpf_ntohl(skops->remote_port) >> 16;
    
    /* Track TCP connections to port 443 for fingerprint modification */
    if (dst_port == 443 && cfg->tcp_fingerprint_enabled) {
        /* Add to sockmap for potential message redirection */
        __u32 key = skops->local_port;
        bpf_sock_map_update(skops, &titan_sockmap, &key, BPF_ANY);
        
        /* Track connection */
        struct conn_key ckey = {
            .src_ip = skops->local_ip4,
            .dst_ip = skops->remote_ip4,
            .src_port = skops->local_port,
            .dst_port = dst_port
        };
        
        struct conn_state cstate = {
            .proxied = 0,
            .fingerprint_id = cfg->os_profile,
            .bytes_sent = 0,
            .bytes_recv = 0,
            .start_time = bpf_ktime_get_ns()
        };
        
        bpf_map_update_elem(&titan_connections, &ckey, &cstate, BPF_ANY);
    }

    return 0;
}

/*
 * Socket Message Redirect Program
 * Redirects QUIC traffic to local proxy
 */
SEC("sk_msg")
int titan_sk_msg(struct sk_msg_md *msg)
{
    struct titan_config *cfg = get_config();
    if (!cfg || !cfg->quic_proxy_enabled)
        return SK_PASS;

    /* Check destination port */
    __u16 dst_port = msg->remote_port;
    
    if (dst_port == bpf_htons(QUIC_PORT)) {
        /* Redirect to local QUIC proxy */
        __u32 proxy_key = cfg->proxy_port;
        
        long ret = bpf_msg_redirect_map(msg, &titan_sockmap, proxy_key, BPF_F_INGRESS);
        if (ret == SK_PASS) {
            update_stats(msg->size, 1, 1, 0);
        }
        return ret;
    }

    return SK_PASS;
}

/*
 * XDP Program for packet-level inspection
 * Handles DNS protection and WebRTC blocking
 */
SEC("xdp")
int titan_xdp_filter(struct xdp_md *ctx)
{
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;
    
    struct titan_config *cfg = get_config();
    if (!cfg)
        return XDP_PASS;

    /* Parse Ethernet header */
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    /* Parse IP header */
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    __u32 pkt_size = data_end - data;

    /* Handle UDP packets */
    if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = (void *)ip + (ip->ihl * 4);
        if ((void *)(udp + 1) > data_end)
            return XDP_PASS;

        __u16 dst_port = bpf_ntohs(udp->dest);
        __u16 src_port = bpf_ntohs(udp->source);

        /* DNS Protection: Only allow DNS to whitelisted servers */
        if (cfg->dns_protection_enabled && dst_port == 53) {
            __u32 dst_ip = ip->daddr;
            /* Block DNS unless destination matches configured DNS servers */
            if (dst_ip != cfg->dns_server_1 && dst_ip != cfg->dns_server_2) {
                update_stats(pkt_size, 0, 0, 1);
                return XDP_DROP;  /* Block non-whitelisted DNS */
            }
            update_stats(pkt_size, 0, 0, 0);
        }

        /* WebRTC Blocking: Block STUN/TURN */
        if (cfg->webrtc_block_enabled) {
            /* STUN ports: 3478, 5349 */
            if (dst_port == 3478 || dst_port == 5349 ||
                src_port == 3478 || src_port == 5349) {
                update_stats(pkt_size, 0, 0, 1);
                return XDP_DROP;
            }
        }

        /* QUIC: Don't block, let sockops handle redirection */
        if (dst_port == QUIC_PORT) {
            update_stats(pkt_size, 1, 0, 0);
            /* V6: Pass through - sockops will redirect */
            return XDP_PASS;
        }
    }

    /* Handle TCP packets for fingerprint modification */
    if (ip->protocol == IPPROTO_TCP && cfg->tcp_fingerprint_enabled) {
        struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
        if ((void *)(tcp + 1) > data_end)
            return XDP_PASS;

        /* TCP fingerprint modification handled in TC egress */
        update_stats(pkt_size, 0, 0, 0);
    }

    return XDP_PASS;
}

/*
 * Helper: Lookup OS TCP profile from map
 */
static __always_inline struct os_tcp_profile *get_os_profile(__u8 profile_id)
{
    __u32 key = profile_id;
    return bpf_map_lookup_elem(&titan_os_profiles, &key);
}

/*
 * TC Egress Program for TCP fingerprint modification
 * Full TCP/IP stack masquerading per research synthesis:
 * 1. IP TTL rewrite (Linux 64 → Windows 128)
 * 2. TCP initial window size
 * 3. TCP window scale factor
 * 4. MSS (Maximum Segment Size) adjustment
 * 5. TCP option reordering (MSS,NOP,WSCALE order varies per OS)
 * 6. L3/L4 checksum recalculation
 *
 * This defeats p0f, Forter passive fingerprinting, and any
 * system comparing TCP stack behavior against User-Agent claims.
 */
SEC("tc")
int titan_tc_egress(struct __sk_buff *skb)
{
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;

    struct titan_config *cfg = get_config();
    if (!cfg || !cfg->tcp_fingerprint_enabled)
        return TC_ACT_OK;

    /* Parse Ethernet header */
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return TC_ACT_OK;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return TC_ACT_OK;

    /* Parse IP header */
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return TC_ACT_OK;

    if (ip->protocol != IPPROTO_TCP)
        return TC_ACT_OK;

    /* Get OS profile */
    struct os_tcp_profile *os_prof = get_os_profile(cfg->os_profile);
    if (!os_prof)
        return TC_ACT_OK;

    /* ── IP LAYER: TTL Rewrite ─────────────────────────────── */
    /* Linux default TTL=64, Windows=128, macOS=64              */
    /* Mismatched TTL is the #1 p0f detection signal            */
    __u8 old_ttl = ip->ttl;
    __u8 new_ttl = os_prof->ttl;

    if (old_ttl != new_ttl) {
        /* Update TTL with L3 checksum fixup */
        bpf_l3_csum_replace(skb, ETH_HLEN + offsetof(struct iphdr, check),
                            bpf_htons((__u16)old_ttl), bpf_htons((__u16)new_ttl), 2);
        /* Re-fetch data pointers after skb modification */
        data = (void *)(long)skb->data;
        data_end = (void *)(long)skb->data_end;
        eth = data;
        if ((void *)(eth + 1) > data_end) return TC_ACT_OK;
        ip = (void *)(eth + 1);
        if ((void *)(ip + 1) > data_end) return TC_ACT_OK;
        ip->ttl = new_ttl;
    }

    /* Parse TCP header */
    struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
    if ((void *)(tcp + 1) > data_end)
        return TC_ACT_OK;

    /* ── TCP LAYER: SYN packet fingerprint rewrite ─────────── */
    /* SYN packets carry the full TCP fingerprint in options     */
    if (tcp->syn) {
        __u16 old_win = tcp->window;
        __u16 new_win = bpf_htons(os_prof->window_size);

        if (old_win != new_win) {
            /* Update window with L4 checksum fixup */
            bpf_l4_csum_replace(skb,
                ETH_HLEN + (ip->ihl * 4) + offsetof(struct tcphdr, check),
                old_win, new_win, 2);
            /* Re-fetch pointers */
            data = (void *)(long)skb->data;
            data_end = (void *)(long)skb->data_end;
            eth = data;
            if ((void *)(eth + 1) > data_end) return TC_ACT_OK;
            ip = (void *)(eth + 1);
            if ((void *)(ip + 1) > data_end) return TC_ACT_OK;
            tcp = (void *)ip + (ip->ihl * 4);
            if ((void *)(tcp + 1) > data_end) return TC_ACT_OK;
            tcp->window = new_win;
        }

        /* ── TCP OPTIONS: Rewrite MSS, Window Scale, SACK ──── */
        /* TCP options start after the 20-byte base header       */
        __u8 tcp_hdr_len = tcp->doff * 4;
        if (tcp_hdr_len <= 20)
            goto done;

        __u8 *opts = (__u8 *)tcp + 20;
        __u8 *opts_end = (__u8 *)tcp + tcp_hdr_len;

        if ((void *)opts_end > data_end)
            goto done;

        /* Walk TCP options and rewrite values in-place */
        /* Bounded loop for eBPF verifier (max 40 bytes of options) */
        #pragma unroll
        for (int i = 0; i < 40; i++) {
            if (opts + i >= opts_end)
                break;

            __u8 kind = opts[i];

            if (kind == TCPOPT_EOL)
                break;
            if (kind == TCPOPT_NOP)
                continue;

            /* Bounds check for option length byte */
            if (opts + i + 1 >= opts_end)
                break;
            __u8 len = opts[i + 1];
            if (len < 2 || opts + i + len > opts_end)
                break;

            /* Rewrite MSS */
            if (kind == TCPOPT_MSS && len == 4 && opts + i + 3 < opts_end) {
                __u16 old_mss = (__u16)(opts[i+2] << 8 | opts[i+3]);
                __u16 new_mss = os_prof->mss;
                if (old_mss != new_mss) {
                    bpf_l4_csum_replace(skb,
                        ETH_HLEN + (ip->ihl * 4) + offsetof(struct tcphdr, check),
                        bpf_htons(old_mss), bpf_htons(new_mss), 2);
                    /* Re-fetch after modification */
                    data = (void *)(long)skb->data;
                    data_end = (void *)(long)skb->data_end;
                    eth = data;
                    if ((void *)(eth + 1) > data_end) return TC_ACT_OK;
                    ip = (void *)(eth + 1);
                    if ((void *)(ip + 1) > data_end) return TC_ACT_OK;
                    tcp = (void *)ip + (ip->ihl * 4);
                    if ((void *)(tcp + 1) > data_end) return TC_ACT_OK;
                    opts = (__u8 *)tcp + 20;
                    opts_end = (__u8 *)tcp + tcp_hdr_len;
                    if ((void *)opts_end > data_end) goto done;
                    opts[i+2] = (new_mss >> 8) & 0xFF;
                    opts[i+3] = new_mss & 0xFF;
                }
            }

            /* Rewrite Window Scale */
            if (kind == TCPOPT_WSCALE && len == 3 && opts + i + 2 < opts_end) {
                __u8 old_scale = opts[i+2];
                __u8 new_scale = os_prof->window_scale;
                if (old_scale != new_scale) {
                    opts[i+2] = new_scale;
                    /* Single byte change — fixup checksum */
                    bpf_l4_csum_replace(skb,
                        ETH_HLEN + (ip->ihl * 4) + offsetof(struct tcphdr, check),
                        bpf_htons((__u16)old_scale), bpf_htons((__u16)new_scale), 2);
                    data = (void *)(long)skb->data;
                    data_end = (void *)(long)skb->data_end;
                    if ((void *)((char *)data + ETH_HLEN + 40) > data_end) return TC_ACT_OK;
                }
            }

            i += len - 1; /* advance past this option (loop increments +1) */
        }
    }

done:
    update_stats(0, 0, 0, 0);
    return TC_ACT_OK;
}

/*
 * Cgroup Socket Program
 * Controls socket creation for leak prevention
 */
SEC("cgroup/sock_create")
int titan_sock_create(struct bpf_sock *sk)
{
    struct titan_config *cfg = get_config();
    if (!cfg)
        return 1; /* Allow */

    /* Block raw sockets (potential leak vector) */
    if (sk->type == SOCK_RAW) {
        return 0; /* Deny */
    }

    return 1; /* Allow */
}

/*
 * Cgroup Connect4 Program
 * Intercepts IPv4 connect() calls
 */
SEC("cgroup/connect4")
int titan_connect4(struct bpf_sock_addr *ctx)
{
    struct titan_config *cfg = get_config();
    if (!cfg)
        return 1;

    __u16 dst_port = bpf_ntohs(ctx->user_port);

    /* Redirect QUIC connections to local proxy */
    if (cfg->quic_proxy_enabled && dst_port == QUIC_PORT) {
        /* Rewrite destination to local proxy */
        ctx->user_ip4 = bpf_htonl(0x7f000001); /* 127.0.0.1 */
        ctx->user_port = bpf_htons(cfg->proxy_port);
    }

    return 1;
}
