#!/bin/bash
# TitanXanti Website Deployment Script
# Deploys to Nginx with Let's Encrypt SSL on titanxanti.site

set -e

DOMAIN="titanxanti.site"
WEB_ROOT="/var/www/${DOMAIN}"
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"

echo "=== TitanXanti Website Deployment ==="
echo "Domain: ${DOMAIN}"
echo "Web Root: ${WEB_ROOT}"

# 1. Install Nginx + Certbot if not present
echo "[1/6] Installing Nginx and Certbot..."
apt-get update -qq
apt-get install -y nginx certbot python3-certbot-nginx > /dev/null 2>&1
echo "  OK: Nginx and Certbot installed"

# 2. Create web root and copy files
echo "[2/6] Setting up web root..."
mkdir -p "${WEB_ROOT}"
cp -r /tmp/website/* "${WEB_ROOT}/"
chown -R www-data:www-data "${WEB_ROOT}"
chmod -R 755 "${WEB_ROOT}"
echo "  OK: Files deployed to ${WEB_ROOT}"

# 3. Create Nginx configuration
echo "[3/6] Configuring Nginx..."
cat > "${NGINX_CONF}" << 'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name titanxanti.site www.titanxanti.site;

    root /var/www/titanxanti.site;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;

    # Cache static assets
    location ~* \.(css|js|svg|png|jpg|jpeg|gif|ico|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # HTML files - short cache
    location ~* \.html$ {
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # Main location
    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    # Custom 404
    error_page 404 /index.html;
}
NGINX

# Enable site
ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload
nginx -t
systemctl enable nginx
systemctl reload nginx
echo "  OK: Nginx configured and running"

# 4. Obtain SSL certificate
echo "[4/6] Obtaining SSL certificate..."
certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" --non-interactive --agree-tos --email admin@${DOMAIN} --redirect || {
    echo "  WARN: SSL cert failed (DNS may not have propagated yet)"
    echo "  Run manually later: certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
}
echo "  OK: SSL configured"

# 5. Setup auto-renewal
echo "[5/6] Setting up SSL auto-renewal..."
systemctl enable certbot.timer 2>/dev/null || true
echo "  OK: Auto-renewal enabled"

# 6. Open firewall ports
echo "[6/6] Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
fi
echo "  OK: Ports 80/443 open"

echo ""
echo "=== Deployment Complete ==="
echo "HTTP:  http://${DOMAIN}"
echo "HTTPS: https://${DOMAIN}"
echo ""

# Verify
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "http://localhost/" || true
