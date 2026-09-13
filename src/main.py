import os
import math
import random
import platform
import string
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips
)
from faster_whisper import WhisperModel

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
INPUT_DIR = "inputs"
OUTPUT_DIR = "outputs"


def setup_directories():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def resolve_input_path(user_input: str) -> str | None:
    cleaned_input = user_input.strip()
    
    in_inputs_folder = os.path.join(INPUT_DIR, cleaned_input)
    if os.path.exists(in_inputs_folder):
        return in_inputs_folder
    
    if os.path.exists(cleaned_input):
        return cleaned_input
        
    return None


def get_unique_output_path(output_dir: str, base_name: str = "rendered_video", ext: str = ".mp4") -> str:
    filename = f"{base_name}{ext}"
    full_path = os.path.join(output_dir, filename)
    
    if not os.path.exists(full_path):
        return full_path

    counter = 1
    while True:
        filename = f"{base_name} ({counter}){ext}"
        full_path = os.path.join(output_dir, filename)
        if not os.path.exists(full_path):
            return full_path
        counter += 1


def get_system_font_path():
    sys_name = platform.system()
    candidates = []
    
    if sys_name == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Black.ttf",
            "/Library/Fonts/Arial Black.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"
        ]
    elif sys_name == "Windows":
        candidates = [
            "C:\\Windows\\Fonts\\arialblk.ttf",
            "C:\\Windows\\Fonts\\arial.ttf"
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def create_subtitle_clip_pil(text, font_size=80, color='yellow', stroke_color='black', stroke_width=6):
    font_path = get_system_font_path()
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = font.getbbox(text, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = 30
    img_w = text_w + padding * 2
    img_h = text_h + padding * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = padding - bbox[0]
    y = padding - bbox[1]

    draw.text((x, y), text, font=font, fill=color, stroke_width=stroke_width, stroke_fill=stroke_color)

    return ImageClip(np.array(img))


def remove_green_screen(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    r, g, b = cv2.split(frame)
    alpha = cv2.bitwise_not(mask)
    return cv2.merge([r, g, b, alpha])


def make_chromakey_clip(video_path: str):
    banner_clip = VideoFileClip(video_path)
    return banner_clip.transform(lambda get_frame, t: remove_green_screen(get_frame(t)))


def generate_subtitles_whisper(audio_path: str):
    print("Transcribing audio and generating subtitles...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    
    segments, _ = model.transcribe(
        audio_path,
        word_timestamps=True,
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True
    )

    words_data = []
    to_strip = string.punctuation + "«»—… "

    for segment in segments:
        for word in segment.words:
            cleaned_word = word.word.strip(to_strip)
            if cleaned_word:
                words_data.append({
                    'word': cleaned_word.upper(),
                    'start': word.start,
                    'end': word.end
                })
    return words_data


def get_user_inputs():
    print("\n--- Automatic Shorts/Reels Generator ---")
    print(f"Tip: Place your input files inside the '{INPUT_DIR}' directory.\n")

    meme_input = input("1. Enter meme video path/filename (e.g., meme.mp4):\n> ")
    meme_path = resolve_input_path(meme_input)
    if not meme_path:
        print(f"Error: File '{meme_input}' not found.")
        return None

    gameplay_input = input("2. Enter gameplay video path/filename (e.g., gameplay.mp4):\n> ")
    gameplay_path = resolve_input_path(gameplay_input)
    if not gameplay_path:
        print(f"Error: File '{gameplay_input}' not found.")
        return None

    banner_input = input("3. Enter green-screen banner video path/filename (e.g., banner.mp4):\n> ")
    banner_path = resolve_input_path(banner_input)
    if not banner_path:
        print(f"Error: File '{banner_input}' not found.")
        return None

    return {"meme_path": meme_path, "gameplay_path": gameplay_path, "banner_path": banner_path}


def main():
    setup_directories()

    inputs = get_user_inputs()
    if not inputs:
        return

    main_clip = VideoFileClip(inputs["meme_path"])
    gameplay_clip = VideoFileClip(inputs["gameplay_path"])

    # 40% top (meme), 60% bottom (gameplay)
    bottom_height = int(TARGET_HEIGHT * 0.60)
    top_height = TARGET_HEIGHT - bottom_height

    top_clip = main_clip.resized(width=TARGET_WIDTH)
    if top_clip.h > top_height:
        top_clip = top_clip.cropped(
            y1=(top_clip.h - top_height) / 2,
            y2=(top_clip.h + top_height) / 2
        )
    top_clip = top_clip.with_position(("center", "top"))

    if gameplay_clip.duration > main_clip.duration:
        start_time = random.uniform(0, gameplay_clip.duration - main_clip.duration)
        bottom_clip = gameplay_clip.subclipped(start_time, start_time + main_clip.duration)
    else:
        repeats = math.ceil(main_clip.duration / gameplay_clip.duration)
        bottom_clip = concatenate_videoclips([gameplay_clip] * repeats).subclipped(0, main_clip.duration)

    bottom_clip = bottom_clip.resized(height=bottom_height)
    if bottom_clip.w < TARGET_WIDTH:
        bottom_clip = bottom_clip.resized(width=TARGET_WIDTH)
        
    bottom_clip = (bottom_clip
                   .cropped(x1=(bottom_clip.w - TARGET_WIDTH) / 2, width=TARGET_WIDTH)
                   .with_position(("center", "bottom"))
                   .without_audio())

    combined_base = CompositeVideoClip(
        [top_clip, bottom_clip],
        size=(TARGET_WIDTH, TARGET_HEIGHT)
    ).with_audio(main_clip.audio)

    print("Removing green screen from banner...")
    banner_clip_transparent = make_chromakey_clip(inputs["banner_path"])
    banner_duration = banner_clip_transparent.duration

    banner_clip_transparent = (banner_clip_transparent
                               .resized(width=int(TARGET_WIDTH * 0.85))
                               .with_position("center"))

    pause_time = main_clip.duration / 2.0

    part1 = combined_base.subclipped(0, pause_time)
    part2 = combined_base.subclipped(pause_time, combined_base.duration)

    freeze_frame = ImageClip(part1.to_ImageClip(t=part1.duration - 0.05).img).with_duration(banner_duration)

    pause_section = CompositeVideoClip(
        [freeze_frame, banner_clip_transparent],
        size=(TARGET_WIDTH, TARGET_HEIGHT)
    )

    full_clip = concatenate_videoclips([part1, pause_section, part2])

    temp_audio = os.path.join(OUTPUT_DIR, "temp_audio_sub.wav")
    main_clip.audio.write_audiofile(temp_audio, logger=None)
    words_data = generate_subtitles_whisper(temp_audio)

    if os.path.exists(temp_audio):
        os.remove(temp_audio)

    subtitle_clips = []
    subtitle_y = top_height - 50

    for item in words_data:
        word = item['word']
        start = item['start']
        end = item['end']

        if start >= pause_time:
            start += banner_duration
            end += banner_duration
        elif end > pause_time:
            end = pause_time

        sub_img_clip = create_subtitle_clip_pil(
            text=word,
            font_size=80,
            color='yellow',
            stroke_color='black',
            stroke_width=6
        )

        txt_clip = (sub_img_clip
                    .with_position(('center', subtitle_y))
                    .with_start(start)
                    .with_end(end))
        
        subtitle_clips.append(txt_clip)

    output_file_path = get_unique_output_path(OUTPUT_DIR, base_name="rendered_video")

    print(f"Rendering final video ({output_file_path})...")
    final_video = CompositeVideoClip([full_clip] + subtitle_clips)
    final_video.write_videofile(
        output_file_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4
    )
    print(f"\nSuccess! Video saved to: {output_file_path}")


if __name__ == "__main__":
    main()