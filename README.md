# Auto Shorts & Reels Generator

An automated Python-based CLI processing pipeline designed to generate vertical video content (Shorts/Reels/TikTok) by compositing streamer memes, gameplay footage, animated chroma-key overlay banners, and synchronized AI-generated subtitles.

## Product Specification

### Core Mechanics

- **Layout & Ratio Engine:** Standardized 9:16 vertical output canvas (`1080x1920`). Composites top video content (Meme/Streamer clip at 40% height) and bottom footage (Gameplay at 60% height).
- **Chroma Key Processing:** Utilizes OpenCV HSV color masking (`cv2`) to dynamically remove green-screen backgrounds from banner assets and render transparent overlays.
- **Mid-Roll Banner Segment:** Calculates the exact midpoint duration of the primary meme clip, splits the timeline, inserts a freeze-frame pause section, and overlays the transparent chroma-key banner.
- **AI Word-Level Subtitling:** Extracts audio to generate precise word-level timestamps using `faster-whisper` (`small` model, int8 quantization).
- **PIL Subtitle Renderer:** Draws yellow text with thick black borders via Pillow (`PIL`) on transparent RGBA canvases, avoiding vector clipping, bounding-box distortion, or font stroke artifacts across MoviePy updates.
- **Automated Output Collision Handling:** Generates incremental unique filenames (e.g., `rendered_video (1).mp4`) in the output directory to prevent overwriting existing renders.

### Cross-Platform Architecture

- **Font Resolution Module:** Auto-detects native bold system typography depending on the host OS:
  - **macOS:** `/System/Library/Fonts/Supplemental/Arial Black.ttf`
  - **Windows:** `C:\Windows\Fonts\arialblk.ttf`
  - **Linux:** `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`

---

## File Architecture

```text
.
├── .venv/            # Local Python virtual environment
├── inputs/           # Workspace folder for raw media assets
├── outputs/          # Target folder for generated MP4 video outputs
├── src/
│   └── main.py       # Core CLI processing pipeline & composition engine
├── .gitignore        # Git exclusion configurations
└── requirements.txt   # Third-party dependency registry
```
# Auto-Shorts-Generator
