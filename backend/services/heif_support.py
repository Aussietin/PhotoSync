"""
HEIC/HEIF support for Pillow.

iPhones save photos as HEIC by default. Pillow can't open HEIF without a plugin,
so importing this module registers the pillow-heif opener (idempotently). If the
package isn't installed, HEIC files simply won't process — everything else keeps
working — so this never raises at import time.
"""

HEIF_AVAILABLE = False

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_AVAILABLE = True
except Exception:
    HEIF_AVAILABLE = False
