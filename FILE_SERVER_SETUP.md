# Titan-7 Public File Server Setup Guide

## Quick Start

### Windows
1. Double-click `scripts\start_file_server.bat`
2. Enter port number (default: 8000)
3. Server will start and display access URLs

### Manual Start
```bash
# From titan-7 root directory
python scripts/titan_file_server.py --port 8000
```

## Access URLs

Once running, the server will display:
- **Local**: `http://localhost:8000`
- **Network**: `http://YOUR_LOCAL_IP:8000` (e.g., 192.168.1.100:8000)
- **Public**: `http://YOUR_PUBLIC_IP:8000`

## Getting Your Public IP

### Windows PowerShell
```powershell
(Invoke-WebRequest -Uri "https://api.ipify.org").Content
```

### Command Line
```bash
curl https://api.ipify.org
```

## Firewall Configuration

### Windows Firewall

**Option 1: Automatic (Run as Administrator)**
```powershell
New-NetFirewallRule -DisplayName "Titan File Server" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

**Option 2: Manual**
1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP" and enter port number (e.g., 8000)
6. Select "Allow the connection"
7. Apply to all profiles (Domain, Private, Public)
8. Name it "Titan File Server"

### Router Port Forwarding (For Public Internet Access)

1. Access your router admin panel (usually 192.168.1.1 or 192.168.0.1)
2. Find "Port Forwarding" or "Virtual Server" section
3. Add new rule:
   - **External Port**: 8000
   - **Internal Port**: 8000
   - **Internal IP**: Your computer's local IP (e.g., 192.168.1.100)
   - **Protocol**: TCP
4. Save and apply

## Command Line Options

```bash
# Custom port
python scripts/titan_file_server.py --port 9000

# Serve specific directory
python scripts/titan_file_server.py --dir /path/to/folder

# Bind to specific IP
python scripts/titan_file_server.py --host 192.168.1.100 --port 8080

# Help
python scripts/titan_file_server.py --help
```

## Features

- **Directory Browsing**: Navigate through folders in web browser
- **File Download**: Click download button or add `?download` to URL
- **File Preview**: Click file name to view in browser (if supported)
- **Responsive UI**: Dark theme with file icons and sizes
- **Cross-Platform**: Works on Windows, Linux, macOS

## Security Warnings

⚠️ **CRITICAL**: This server allows ANYONE with network access to download ALL files in the Titan-7 folder!

### Recommendations:
1. **Only run when needed** - Stop server when not in use
2. **Use strong firewall rules** - Limit access to trusted IPs if possible
3. **Monitor access** - Server logs all requests to console
4. **Consider VPN** - Use VPN for remote access instead of public internet
5. **Temporary use** - This is meant for quick file sharing, not permanent hosting

## Example Access Scenarios

### Scenario 1: Local Network Access
- Your PC: 192.168.1.100
- Friend's PC: 192.168.1.50 (same network)
- Friend accesses: `http://192.168.1.100:8000`

### Scenario 2: Public Internet Access
- Your Public IP: 203.0.113.45 (from ipify.org)
- Port forwarding enabled on router
- Remote user accesses: `http://203.0.113.45:8000`

### Scenario 3: VPS/Remote Server
- VPS IP: 72.62.72.48
- Run server on VPS
- Access from anywhere: `http://72.62.72.48:8000`

## Stopping the Server

Press `Ctrl+C` in the terminal/command prompt window

## Troubleshooting

### "Address already in use"
Port is already taken. Try different port:
```bash
python scripts/titan_file_server.py --port 8001
```

### Can't access from other devices
1. Check firewall allows the port
2. Verify you're using correct IP address
3. Make sure devices are on same network (for local access)
4. Check router port forwarding (for public access)

### Slow downloads
- Large files may take time depending on network speed
- Check network bandwidth
- Consider compressing folder first for faster transfer

## Alternative: Create Downloadable Archive

If you want a single downloadable file instead of browsing:

### Windows
```powershell
# Create ZIP archive
Compress-Archive -Path "C:\Users\Administrator\Downloads\titan-7\titan-7\titan-7\*" -DestinationPath "C:\Users\Administrator\Downloads\titan-7-complete.zip"
```

Then serve just the ZIP file or upload to file sharing service.

## Production Hosting Alternatives

For permanent/production hosting, consider:
- **GitHub**: Free for public repos (up to 100GB)
- **Cloud Storage**: Google Drive, Dropbox, OneDrive
- **File Hosting**: WeTransfer, Mega.nz, MediaFire
- **VPS with Nginx**: More secure and performant
- **FTP Server**: FileZilla Server for Windows

## Support

For issues or questions, check server console output for error messages.
