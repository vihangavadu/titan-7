# TitanXanti Website — titanxanti.site

## Overview

Professional 5-page landing website for TitanXanti, deployed on Hostinger VPS with Nginx and Let's Encrypt SSL.

**Live URL:** https://titanxanti.site

---

## Architecture

| Component | Technology |
|-----------|-----------|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Fonts** | Google Fonts (Inter, JetBrains Mono) |
| **Web Server** | Nginx 1.22 |
| **SSL** | Let's Encrypt (auto-renewing via Certbot) |
| **Hosting** | Hostinger KVM 2 VPS (187.77.186.252) |
| **Domain** | titanxanti.site (Hostinger DNS) |
| **OS** | Debian 12 (bookworm) |

---

## Pages

| # | Page | File | Description |
|---|------|------|-------------|
| 1 | **Home** | `index.html` | Hero section with animated terminal, feature grid (6 cards), AI tech showcase with code block, stats counter, CTA |
| 2 | **About** | `about.html` | Mission statement, 4 core values, 3 leadership cards, company timeline |
| 3 | **Services** | `services.html` | 5 detailed service blocks with metric visualizations, 3-tier pricing cards |
| 4 | **Documentation** | `docs.html` | Full docs with sidebar navigation, quick start guide, API reference (6 endpoints), SDK install, webhooks, changelog, FAQ |
| 5 | **Contact** | `contact.html` | Contact form (with JS validation/submission), 4 info cards, FAQ section |

---

## File Structure

```
website/
├── index.html              # Home page
├── about.html              # About page
├── services.html           # Services page
├── docs.html               # Documentation page
├── contact.html            # Contact page
├── css/
│   └── style.css           # All styles (~1100 lines)
├── js/
│   └── main.js             # Interactions, animations, form handling
├── assets/
│   └── favicon.svg         # SVG favicon (hexagonal logo)
├── deploy.sh               # Deployment script (Nginx + Certbot)
└── README.md               # This file
```

---

## Design System

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0a0a0f` | Page background |
| `--bg-card` | `#16162a` | Card backgrounds |
| `--accent` | `#00d4ff` | Primary accent (cyan) |
| `--gradient-1` | `#00d4ff → #7b61ff` | Gradient text, CTAs |
| `--text-primary` | `#e8e8f0` | Headings, body text |
| `--text-secondary` | `#9898b8` | Descriptions, muted text |

### Typography
- **Headings:** Inter 700-900, tight letter-spacing
- **Body:** Inter 400-500, 1.6 line-height
- **Code:** JetBrains Mono 400-500

### Components
- **Buttons:** Primary (cyan), Ghost (outlined), White (CTA)
- **Cards:** Dark bg, subtle border, hover glow effect
- **Terminal:** Animated typing effect on home page
- **Code blocks:** Syntax-highlighted with copy button
- **Forms:** Dark inputs with focus glow

---

## Features

- **Fully responsive** — mobile, tablet, desktop breakpoints
- **Dark theme** — professional cybersecurity aesthetic
- **Animated counters** — stats animate on scroll into view
- **Scroll reveal** — cards fade in as user scrolls
- **Terminal animation** — typing effect on home hero
- **Sticky docs sidebar** — auto-highlights current section
- **Copy code buttons** — click to copy code snippets
- **Contact form** — client-side validation with success state
- **Gzip compression** — Nginx gzip for CSS/JS/SVG
- **Asset caching** — 30-day cache for static assets
- **Security headers** — X-Frame-Options, X-Content-Type, XSS protection
- **SSL A+ rating** — Let's Encrypt with auto-renewal

---

## DNS Configuration

Managed via Hostinger API:

| Type | Name | Content | TTL |
|------|------|---------|-----|
| A | @ | 187.77.186.252 | 300 |
| CNAME | www | titanxanti.site. | 300 |

---

## Nginx Configuration

Location: `/etc/nginx/sites-available/titanxanti.site`

Key features:
- SSL termination with Let's Encrypt certificates
- HTTP → HTTPS redirect (managed by Certbot)
- Gzip compression for text/CSS/JS/SVG
- Static asset caching (30 days)
- Security headers on all responses
- `try_files` with `.html` extension fallback

---

## SSL Certificate

| Property | Value |
|----------|-------|
| Issuer | Let's Encrypt |
| Certificate | `/etc/letsencrypt/live/titanxanti.site/fullchain.pem` |
| Private Key | `/etc/letsencrypt/live/titanxanti.site/privkey.pem` |
| Expires | 2026-05-28 |
| Auto-renewal | Certbot systemd timer |

---

## Deployment

### Initial Deploy
```bash
# From local machine — upload files and run deploy script
scp -r website/ root@187.77.186.252:/tmp/website
ssh root@187.77.186.252 "bash /tmp/website/deploy.sh"
```

### Update Content
```bash
# Upload updated files
scp -r website/ root@187.77.186.252:/tmp/website

# On VPS — copy to web root and reload
ssh root@187.77.186.252 "cp -r /tmp/website/* /var/www/titanxanti.site/ && nginx -s reload"
```

### Verify
```bash
# Check all pages
for page in "" about.html services.html docs.html contact.html; do
    curl -s -o /dev/null -w "%{http_code} https://titanxanti.site/${page}\n" "https://titanxanti.site/${page}"
done
```

---

## Hostinger API Commands

```powershell
$headers = @{
    "Authorization" = "Bearer YOUR_API_TOKEN"
    "Content-Type" = "application/json"
}

# Check domain
Invoke-RestMethod -Uri "https://developers.hostinger.com/api/domains/v1/portfolio" -Headers $headers

# View DNS records
Invoke-RestMethod -Uri "https://developers.hostinger.com/api/dns/v1/zones/titanxanti.site" -Headers $headers

# Update DNS
$body = '{"overwrite":true,"zone":[{"type":"A","name":"@","ttl":300,"records":[{"content":"187.77.186.252"}]},{"type":"CNAME","name":"www","ttl":300,"records":[{"content":"titanxanti.site."}]}]}'
Invoke-RestMethod -Uri "https://developers.hostinger.com/api/dns/v1/zones/titanxanti.site" -Headers $headers -Method PUT -Body $body
```

---

## Maintenance

### Renew SSL (automatic)
```bash
certbot renew --dry-run    # Test renewal
certbot renew              # Force renewal
```

### Check Nginx Status
```bash
systemctl status nginx
nginx -t                   # Test config
nginx -s reload            # Reload config
```

### View Logs
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## Browser Support

| Browser | Version |
|---------|---------|
| Chrome | 90+ |
| Firefox | 90+ |
| Safari | 14+ |
| Edge | 90+ |
| Mobile Safari | 14+ |
| Chrome Android | 90+ |

---

## Performance

- **No external JS frameworks** — pure vanilla JavaScript (~7KB)
- **Single CSS file** — no build step needed (~32KB)
- **SVG favicon** — resolution-independent, tiny file size
- **Google Fonts** — preconnected for fast loading
- **Nginx gzip** — ~70% compression on text assets
- **30-day cache** — static assets cached aggressively

---

*Last updated: February 27, 2026*
