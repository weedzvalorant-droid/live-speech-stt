# Overrides pyinstaller-hooks-contrib's built-in hook for "webrtcvad".
#
# That contrib hook expects a companion module ("__PyInstaller_hooks_0_webrtcvad")
# supplied by the official `webrtcvad` PyPI package. We install `webrtcvad-wheels`
# instead (same import name, prebuilt wheels incl. Windows, see requirements.txt) which
# doesn't ship that companion module, so the contrib hook crashes with
# ImportErrorWhenRunningHook during analysis.
#
# webrtcvad is a single small C extension with no bundled data files, so it needs no
# special hook at all -- PyInstaller's normal import analysis collects it on its own.
# Pointing --additional-hooks-dir at this folder makes PyInstaller use this no-op hook
# instead of the broken contrib one.
hiddenimports = ["webrtcvad"]
