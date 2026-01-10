# -*- coding: utf-8 -*-
"""Text-to-Speech - Make the computer speak your message using Edge TTS"""
import os
import asyncio
import tempfile
import subprocess
import shutil
from pathlib import Path

try:
    import edge_tts
    import pygame
except ImportError as e:
    print(f"[!] Required library not installed: {e}")
    print("[!] Please install: edge-tts and pygame")
    raise

# Get message and voice from environment variables (injected by server)
message = os.environ.get("SPEAK_MESSAGE", "Hello! I am your computer speaking. This is a test message.")
VOICE = os.environ.get("TTS_VOICE", "en-US-GuyNeural")  # Default voice

# Debug: Print all environment variables related to TTS
print("=" * 60)
print("   TEXT TO SPEECH (EDGE TTS)")
print("=" * 60)
print(f"[*] Voice   : {VOICE}")
print(f"[*] Message : {message}")
print(f"[DEBUG] TTS_VOICE env var: {os.environ.get('TTS_VOICE', 'NOT SET')}")
print(f"[DEBUG] SPEAK_MESSAGE env var: {os.environ.get('SPEAK_MESSAGE', 'NOT SET')}")
print("[*] Generating speech...")


async def TextToAudioFile(text, voice, file_path):
    """Asynchronous function to convert text to an audio file using Python API."""
    # Validate input
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Create directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing file if it exists
    if file_path.exists():
        file_path.unlink()
    
    # Try the selected voice first, then fallbacks
    voices_to_try = [voice] + get_fallback_voices(voice)
    
    for attempt_voice in voices_to_try:
        # Try without pitch/rate first (most reliable), then with
        attempts = [
            (attempt_voice, None, None),       # Try without pitch/rate first
            (attempt_voice, '+5Hz', '+13%'),  # Try with pitch/rate
        ]
        
        last_error = None
        for v, pitch, rate in attempts:
            try:
                # Create the communicate object
                if pitch and rate:
                    communicate = edge_tts.Communicate(text, v, pitch=pitch, rate=rate)
                else:
                    communicate = edge_tts.Communicate(text, v)
                
                await communicate.save(str(file_path))
                
                # Verify file was created
                if file_path.exists() and file_path.stat().st_size > 0:
                    if v != voice:
                        print(f"[!] Used fallback voice '{v}' instead of '{voice}'")
                    return v  # Return the voice that worked
                else:
                    raise Exception("Audio file was not created or is empty")
                    
            except Exception as e:
                last_error = e
                # Only print error for the first voice attempt
                if attempt_voice == voice and v == voice and pitch is None:
                    print(f"[!] Voice '{voice}' failed: {e}")
                continue
        
        # If we tried all pitch/rate combinations for this voice and it failed, try next voice
        if attempt_voice == voice:
            print(f"[!] Voice '{voice}' not available, trying fallback voices...")
    
    # If we get here, all voices failed
    raise Exception(f"Failed to generate audio. Tried voices: {voices_to_try}. Last error: {last_error}")


def play_audio(file_path):
    """Play audio file using pygame."""
    try:
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Load the generated speech file into pygame mixer
        pygame.mixer.music.load(str(file_path))
        pygame.mixer.music.play()  # Play the audio
        
        # Loop until the audio is done playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)  # Limit the loop to 10 ticks per second
        
        return True
        
    except Exception as e:
        print(f"[!] Error playing audio: {e}")
        return False
    finally:
        try:
            pygame.mixer.music.stop()  # Stop the audio playback
            pygame.mixer.quit()  # Quit the pygame mixer
        except Exception:
            pass


def get_fallback_voices(voice):
    """Get fallback voices based on the selected voice."""
    # Common fallback voices that are known to work
    fallbacks = {
        'en-IN-PrabhatNeural': ['en-IN-RaviNeural', 'en-US-GuyNeural', 'en-US-AriaNeural'],
        'en-IN-NeerjaNeural': ['en-IN-PriyaNeural', 'en-US-AriaNeural', 'en-US-JennyNeural'],
        'en-US-GuyNeural': ['en-US-AriaNeural', 'en-GB-RyanNeural'],
        'en-US-AriaNeural': ['en-US-JennyNeural', 'en-US-GuyNeural'],
        'hi-IN-MadhurNeural': ['hi-IN-SwaraNeural', 'en-IN-PrabhatNeural', 'en-US-GuyNeural'],
        'hi-IN-SwaraNeural': ['hi-IN-MadhurNeural', 'en-IN-NeerjaNeural', 'en-US-AriaNeural'],
    }
    
    # If we have a specific fallback list, use it
    if voice in fallbacks:
        return fallbacks[voice]
    
    # Generic fallbacks based on language prefix
    if voice.startswith('en-AU-'):
        return ['en-US-GuyNeural', 'en-US-AriaNeural', 'en-GB-RyanNeural']
    elif voice.startswith('en-IN-'):
        return ['en-US-AriaNeural', 'en-US-GuyNeural', 'en-GB-RyanNeural']
    elif voice.startswith('en-US-'):
        return ['en-US-AriaNeural', 'en-GB-RyanNeural']
    elif voice.startswith('en-GB-'):
        return ['en-US-GuyNeural', 'en-US-AriaNeural']
    elif voice.startswith('hi-IN-'):
        # Hindi voices fallback to other Hindi voices, then English Indian voices
        return ['hi-IN-SwaraNeural', 'hi-IN-MadhurNeural', 'en-IN-PrabhatNeural', 'en-IN-NeerjaNeural']
    else:
        # Generic English fallbacks
        return ['en-US-AriaNeural', 'en-US-GuyNeural', 'en-GB-RyanNeural']


def generate_with_cli(text, voice, file_path):
    """Use edge-tts CLI command (primary method - most reliable)."""
    # Try the selected voice first
    voices_to_try = [voice] + get_fallback_voices(voice)
    
    for attempt_voice in voices_to_try:
        try:
            # Check if edge-tts CLI is available
            if not shutil.which("edge-tts"):
                print("[!] edge-tts CLI not found in PATH")
                return False, None
            
            # Remove existing file if it exists
            if file_path.exists():
                file_path.unlink()
            
            # Use CLI command - don't escape, let subprocess handle it
            cmd = [
                "edge-tts",
                "--text", text,
                "--voice", attempt_voice,
                "--write-media", str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and file_path.exists() and file_path.stat().st_size > 0:
                return True, attempt_voice
            
            # If this was the first attempt (selected voice), log the error
            if attempt_voice == voice:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                if "No audio was received" in error_msg or "NoAudioReceived" in error_msg:
                    print(f"[!] Voice '{voice}' not available, trying fallback voices...")
                else:
                    print(f"[!] CLI error with '{voice}': {error_msg}")
            
        except subprocess.TimeoutExpired:
            if attempt_voice == voice:
                print("[!] CLI command timed out")
            continue
        except Exception as e:
            if attempt_voice == voice:
                print(f"[!] CLI error: {e}")
            continue
    
    return False, None


def main():
    """Main function to generate and play TTS."""
    # Create temp file for mp3
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_path = Path(tmp.name)
    
    audio_generated = False
    actual_voice_used = VOICE
    try:
        # Use CLI as primary method (most reliable, works with all voices)
        print(f"[*] Using CLI to generate audio with voice: {VOICE}")
        success, used_voice = generate_with_cli(message, VOICE, tmp_path)
        if success:
            if used_voice != VOICE:
                print(f"[!] Note: Used voice '{used_voice}' instead of '{VOICE}'")
                actual_voice_used = used_voice
            print(f"[*] Audio generated (CLI): {tmp_path}")
            audio_generated = True
        else:
            print("[!] CLI failed, trying Python API...")
            # Fallback to Python API
            # Note: Cannot use asyncio.run() in script context (event loop already running)
            # Use event loop pattern per SERVER_SCRIPT_DEVELOPMENT_GUIDE.md
            try:
                # Create a new event loop for this script (per development guide)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    used_voice = loop.run_until_complete(TextToAudioFile(message, VOICE, tmp_path))
                    if used_voice != VOICE:
                        actual_voice_used = used_voice
                    print(f"[*] Audio generated (Python API): {tmp_path}")
                    audio_generated = True
                finally:
                    loop.close()
            except Exception as e:
                print(f"[!] Python API also failed: {e}")
                raise Exception(f"Both CLI and Python API failed. Last error: {e}")
        
        if not audio_generated:
            raise Exception("Failed to generate audio")
        
        # Play the audio
        print("[*] Playing audio...")
        if play_audio(tmp_path):
            print("[OK] Message spoken successfully!")
        else:
            print("[!] Failed to play audio")
            
    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Clean up temp file
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
