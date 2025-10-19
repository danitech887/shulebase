import subprocess
import os

# === 1️⃣ Path to your FFprobe executable ===
FFPROBE_PATH = r"C:\Users\danie\Desktop\ffmpeg-master-latest-win64-gpl-shared\bin\ffprobe.exe"

# === 2️⃣ Folder containing your episode files ===
folder_path = r"C:\Users\danie\Videos\raised by wolves" # <- change to your folder

# === 3️⃣ Official episode durations (in minutes) for Raised by Wolves Season 1 ===
official_episodes = {
    "S01E01 - Raised by Wolves": 53,
    "S01E02 - Pentagram": 42,
    "S01E03 - Victory": 48,
    "S01E04 - Aurore": 50,
    "S01E05 - Mother": 50,
    "S01E06 - Campion": 50,
    "S01E07 - Awakening": 50,
    "S01E08 - Revelation": 50,
    "S01E09 - Infected": 50,
    "S01E10 - Revelation": 50,
}

# === Function to get video duration in minutes ===
def get_duration(file_path):
    result = subprocess.run(
        [FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    duration_sec = float(result.stdout)
    return round(duration_sec / 60)

# === Loop through files and match with closest episode ===
for file in os.listdir(folder_path):
    file_path = os.path.join(folder_path, file)
    if os.path.isfile(file_path):
        try:
            dur = get_duration(file_path)
            closest_episode = min(official_episodes, key=lambda k: abs(official_episodes[k]-dur))
            print(f"{file} -> approx {dur} min -> {closest_episode}")
        except Exception as e:
            print(f"Could not read {file} ({e})")
