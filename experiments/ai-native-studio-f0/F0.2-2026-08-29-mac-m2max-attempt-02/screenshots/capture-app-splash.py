import bpy

SCREENSHOT_PATH = "/Users/mengyingli/Documents/ChatGPT/MyBlenderFilmStudio/experiments/ai-native-studio-f0/F0.2-2026-08-29-mac-m2max-attempt-02/screenshots/app-splash.png"

def capture_and_exit():
    try:
        result = bpy.ops.screen.screenshot(filepath=SCREENSHOT_PATH)
        print(f"F0_SCREENSHOT_RESULT={sorted(result)}", flush=True)
    finally:
        bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(capture_and_exit, first_interval=4.0)
