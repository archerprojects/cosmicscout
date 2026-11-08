Cosmic Scout — hicolor icon tree (v1.1.0 — Monday 9 November 2026)

Source: source/org.cosmicscout.app-master.png (1024x1024 RGBA, Overwatch's
cs_logo artwork). The eight sizes (16, 24, 32, 48, 64, 128, 256, 512) are
smooth-scaled from it; the Flatpak manifest installs them into
/app/share/icons/hicolor/<size>/apps/org.cosmicscout.app.png. When run from
source, chs/main.py uses the 256x256 file as the window icon.

To regenerate after replacing the master (from flatpak/icons/):
  python3 -c "from PyQt6.QtGui import QImage; from PyQt6.QtCore import Qt; \
src=QImage('source/org.cosmicscout.app-master.png'); \
[src.scaled(s,s,Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation).save(f'{s}x{s}/apps/org.cosmicscout.app.png') \
 for s in (16,24,32,48,64,128,256,512)]"
