"""
Shortcuts Generator: Creates a binary Shortcuts file mapping single letters to high-authority domains.
"""
import struct
from pathlib import Path

def generate_shortcuts(shortcuts_path, domain_map=None):
    # domain_map: dict like {'y': 'https://www.youtube.com', 'g': 'https://www.google.com'}
    domain_map = domain_map or {
        'y': 'https://www.youtube.com',
        'g': 'https://www.google.com',
        'r': 'https://www.reddit.com',
        'n': 'https://www.netflix.com',
        'a': 'https://www.amazon.com',
        's': 'https://stackoverflow.com',
        'w': 'https://en.wikipedia.org/wiki/Main_Page',
        'l': 'https://www.linkedin.com',
        't': 'https://www.twitch.tv',
        'e': 'https://www.espn.com',
    }
    # This is a placeholder: real Shortcuts is a protobuf, but we fake a binary blob for now
    with open(shortcuts_path, 'wb') as f:
        for key, url in domain_map.items():
            # Write: key (1 byte), url length (1 byte), url (utf-8)
            f.write(key.encode('utf-8'))
            url_bytes = url.encode('utf-8')
            f.write(struct.pack('B', len(url_bytes)))
            f.write(url_bytes)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: shortcuts_gen.py <shortcuts_path>")
        exit(1)
    generate_shortcuts(sys.argv[1])
