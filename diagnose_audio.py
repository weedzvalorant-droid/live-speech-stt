"""Standalone WASAPI loopback diagnostic, independent of the rest of the app.
Run with the venv's Python: venv\\Scripts\\python.exe diagnose_audio.py
Paste the full output back for debugging.
"""
import sys
import traceback

try:
    import pyaudiowpatch as pyaudio
except Exception as exc:
    print("FAILED to import pyaudiowpatch:", exc)
    sys.exit(1)

try:
    import importlib.metadata as _im
    print("pyaudiowpatch package version:", _im.version("PyAudioWPatch"))
except Exception as exc:
    print("Could not determine pyaudiowpatch package version:", exc)

print("pyaudiowpatch version info OK")
print("PyAudio/PortAudio version:", pyaudio.get_portaudio_version_text())
print()

p = pyaudio.PyAudio()
print("Host API count:", p.get_host_api_count())
print("Device count:", p.get_device_count())
print()

try:
    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    print("WASAPI host api info:", wasapi_info)
except Exception:
    print("FAILED to get WASAPI host api info:")
    traceback.print_exc()
    wasapi_info = None

print()
print("--- ALL devices (index, name, maxInputChannels, maxOutputChannels, hostApi, isLoopback) ---")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(
        i,
        repr(info.get("name")),
        "in=", info.get("maxInputChannels"),
        "out=", info.get("maxOutputChannels"),
        "hostApi=", info.get("hostApi"),
        "isLoopbackDevice=", info.get("isLoopbackDevice"),
        "defaultSampleRate=", info.get("defaultSampleRate"),
    )

print()
print("--- LOOPBACK devices via get_loopback_device_info_generator() ---")
loopback_devices = []
try:
    for info in p.get_loopback_device_info_generator():
        loopback_devices.append(info)
        print(info)
except Exception:
    print("FAILED to enumerate loopback devices:")
    traceback.print_exc()

print()
if wasapi_info:
    try:
        default_out = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        print("Default WASAPI output device:", default_out)
    except Exception:
        print("FAILED to get default output device:")
        traceback.print_exc()
        default_out = None
else:
    default_out = None

target = None
if default_out:
    if default_out.get("isLoopbackDevice"):
        target = default_out
    else:
        for d in loopback_devices:
            if default_out["name"] in d["name"]:
                target = d
                break
if target is None and loopback_devices:
    target = loopback_devices[0]

print()
print("=== Chosen target device for open() test ===")
print(target)

if target is None:
    print("No loopback device could be chosen. Stopping here.")
    p.terminate()
    sys.exit(1)

FORMATS = {
    "paInt16": pyaudio.paInt16,
    "paInt24": pyaudio.paInt24,
    "paFloat32": pyaudio.paFloat32,
}


def try_open(dev, format_name, format_const):
    print()
    print(f"=== index {dev['index']} ({dev['name']!r}), format={format_name} ===")
    try:
        stream = p.open(
            format=format_const,
            channels=int(dev["maxInputChannels"]),
            rate=int(dev["defaultSampleRate"]),
            frames_per_buffer=8000,
            input=True,
            input_device_index=dev["index"],
        )
        print("OPEN SUCCEEDED. Reading one buffer...")
        data = stream.read(8000, exception_on_overflow=False)
        print("READ SUCCEEDED, got", len(data), "bytes")
        stream.stop_stream()
        stream.close()
        print(f"ALL GOOD: {dev['name']} works with {format_name}")
        return True
    except Exception as exc:
        print(f"FAILED ({format_name}):", exc)
        return False


print()
print("################ Trying EVERY loopback device x EVERY format ################")
results = {}
for dev in loopback_devices:
    for format_name, format_const in FORMATS.items():
        results[(dev["name"], format_name)] = try_open(dev, format_name, format_const)

print()
print("################ Control test: does WASAPI work AT ALL on this machine? ################")
print("(This only tests whether the WASAPI host API itself can open ANY input device --")
print(" the app never captures the microphone, this is purely diagnostic.)")
all_devices = [p.get_device_info_by_index(i) for i in range(p.get_device_count())]
input_capable = [d for d in all_devices if d["maxInputChannels"] > 0]
for dev in input_capable:
    api_name = p.get_host_api_info_by_index(dev["hostApi"])["name"]
    key = f"{dev['name']} [hostApi={api_name}, loopback={dev.get('isLoopbackDevice')}]"
    results[(key, "paInt16")] = try_open(dev, "paInt16", pyaudio.paInt16)

print()
print("################ Summary ################")
for (name, format_name), ok in results.items():
    print(("OK  " if ok else "FAIL"), name, "/", format_name)

p.terminate()
