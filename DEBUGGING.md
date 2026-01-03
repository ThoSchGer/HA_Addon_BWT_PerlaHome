# Debugging Guide für BWT Perla Smartmeter Add-on

## Problem: OCR liest Bereiche nicht korrekt aus

### Schritt 1: Debug-Screenshots aktivieren

In der Add-on-Konfiguration:
```yaml
debug_screenshots: true
```

### Schritt 2: Logs überprüfen

**Home Assistant → Add-ons → BWT Perla Smartmeter → Logs**

Achte auf diese Debug-Ausgaben:
```
[DEBUG] Capturing region: x=60, y=70, w=80, h=25 -> /data/debug/throughput_xxxxx.png
[DEBUG] Screenshot saved to: ... (exists=True, size=xxxx bytes)
[DEBUG] Running OCR on: ...
[DEBUG] Image size: (80, 25), mode: RGB
[DEBUG] OCR raw result length: xx chars
[DEBUG] throughput raw='...' parsed='...'
```

### Schritt 3: Screenshots analysieren

Die Screenshots werden in `/data/debug/` gespeichert:

1. **fullscreen_after_login.png** - Vollbild nach VNC-Login
2. **throughput_[timestamp].png** - Ausschnitt Durchfluss
3. **volume_[timestamp].png** - Ausschnitt Volumen

**Zugriff auf Screenshots:**
- Via SSH: `ls -lh /data/debug/`
- Via Add-on File Editor
- Via Backup-Export

### Schritt 4: Koordinaten anpassen

Falls die Screenshots den falschen Bereich zeigen:

#### Fullscreen analysieren
1. Öffne `fullscreen_after_login.png`
2. Messe die Pixel-Koordinaten der Werte mit einem Bildbearbeitungsprogramm
3. Format: `x,y,breite,höhe` (x/y = linke obere Ecke)

#### Config anpassen
```yaml
throughput_region: "60,70,80,25"  # Beispiel: x=60, y=70, w=80, h=25
volume_region: "70,150,60,24"
```

### Schritt 5: OCR-Pattern testen

Falls OCR den Text erkennt, aber das Pattern nicht matcht:

**Durchfluss-Pattern:**
```yaml
throughput_pattern: "(.*)|*./h"
```
- Matcht: `123|/h`, `45.5/h`, `0/h`
- Regex: Alles vor `/h` (mit optionalen Pipes)

**Volumen-Pattern:**
```yaml
volume_pattern: "(.*)|*."
```
- Matcht: `12345|.`, `67890.`
- Regex: Alles vor dem letzten Zeichen

### Häufige Probleme

#### Problem: Screenshots sind schwarz/leer
**Lösung:** 
- VNC-Verbindung prüfen: `ping <bwt_ipaddress>`
- VNC-Timeout erhöhen: `vnc_timeout_seconds: 120`
- VNC manuell testen: `vncviewer <bwt_ipaddress>`

#### Problem: OCR erkennt nichts (leerer String)
**Lösung:**
- Screenshot manuell prüfen: Ist Text lesbar?
- Tesseract-Config anpassen: `tesseract_config: "--psm 7"`
- Helligkeit/Kontrast des Displays prüfen

#### Problem: OCR erkennt falsche Zeichen (z.B. `|` statt `1`)
**Lösung:**
- Normal! Die `parse_ocr_value` Funktion bereinigt das
- Falls `O` als `0` erkannt werden soll, ist das bereits implementiert

#### Problem: Pattern matcht nicht
**Lösung:**
- Log zeigt: `parsed=None` → Pattern passt nicht
- Beispiel Raw-Output: `"123|4 /h"`
- Teste Pattern online: https://regex101.com/
- Original-Pattern aus funktionierendem Script: `'(.*)\|*./h'`

### Test-Kommandos (SSH/Terminal)

```bash
# Logs live verfolgen
docker logs -f addon_xxxxxxxx_bwt_perla_smartmeter

# Debug-Verzeichnis ansehen
ls -lh /data/debug/

# Screenshots ansehen (wenn X11 verfügbar)
display /data/debug/fullscreen_after_login.png

# Letztes Screenshot
ls -lt /data/debug/ | head -5
```

### Manuelle OCR-Tests

Falls du die Screenshots hast, kannst du OCR manuell testen:

```python
from PIL import Image
import pytesseract

img = Image.open("throughput_xxxxx.png")
print(pytesseract.image_to_string(img, lang='eng', config='-c page_separator=""'))
```

### Support

Falls nichts hilft:
1. Screenshots aus `/data/debug/` exportieren
2. Logs kopieren
3. Issue auf GitHub öffnen: https://github.com/ThoSchGer/HA_Addon_BWT_PerlaHome/issues
