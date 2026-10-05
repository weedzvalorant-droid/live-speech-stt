"""Default application settings. Persisted as JSON (minus secrets) by SettingsManager."""

DEFAULT_SETTINGS = {
    # Audio
    "audio_device_index": None,  # None = resolve default system output loopback at start time
    "chunk_ms": 500,  # size of audio chunks pulled from the capture stream
    # Language / STT
    "language": "auto",  # "auto" | "ru" | "en"
    "stt_provider": "faster_whisper",  # "faster_whisper" | "cloud_openai"
    "whisper_model": "small",  # tiny | base | small | medium | large-v3
    "use_gpu": True,
    "compute_type": "auto",  # auto | int8 | float16 | float32
    "partial_interval_ms": 900,  # minimum time between partial re-decodes
    # VAD
    "vad_sensitivity": 0.5,  # 0..1, higher = more sensitive to speech
    "vad_min_silence_ms": 500,  # silence needed to end an utterance
    "vad_min_speech_ms": 200,  # speech needed to start an utterance
    # UI
    "theme": "dark",  # dark | light
    "font_size": 14,
    "autoscroll": True,
    "always_on_top": False,
    # Subtitle mode
    "subtitle_opacity": 0.85,
    "subtitle_font_size": 22,
    "subtitle_background": True,
    "subtitle_always_on_top": True,
    "subtitle_geometry": None,  # [x, y, w, h], saved on close
    # Misc
    "autostart": False,
    "cloud_api_key_configured": False,
}
