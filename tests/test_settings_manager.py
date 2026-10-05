from livestt.config.settings_manager import SettingsManager


def test_defaults_loaded_when_no_file_exists(tmp_path):
    sm = SettingsManager(config_dir=tmp_path)
    assert sm.get("language") == "auto"
    assert sm.get("theme") == "dark"


def test_set_persists_across_instances(tmp_path):
    sm = SettingsManager(config_dir=tmp_path)
    sm.set("language", "ru")
    sm.set("font_size", 18)

    sm2 = SettingsManager(config_dir=tmp_path)
    assert sm2.get("language") == "ru"
    assert sm2.get("font_size") == 18


def test_update_multiple_keys(tmp_path):
    sm = SettingsManager(config_dir=tmp_path)
    sm.update({"theme": "light", "autoscroll": False})
    sm2 = SettingsManager(config_dir=tmp_path)
    assert sm2.get("theme") == "light"
    assert sm2.get("autoscroll") is False


def test_corrupted_json_falls_back_to_defaults(tmp_path):
    (tmp_path / "settings.json").write_text("{not valid json", encoding="utf-8")
    sm = SettingsManager(config_dir=tmp_path)
    assert sm.get("language") == "auto"


def test_unknown_keys_on_disk_are_ignored(tmp_path):
    (tmp_path / "settings.json").write_text('{"made_up_key": 123, "theme": "light"}', encoding="utf-8")
    sm = SettingsManager(config_dir=tmp_path)
    assert sm.get("theme") == "light"
    assert sm.get("made_up_key") is None


def test_api_key_not_written_to_settings_json(tmp_path):
    sm = SettingsManager(config_dir=tmp_path)
    sm.set("theme", "dark")  # ensure settings.json exists regardless of keyring outcome
    sm.set_api_key("openai", "sk-super-secret-value")
    raw = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "sk-super-secret-value" not in raw


def test_api_key_roundtrips_through_keyring_backend(tmp_path):
    sm = SettingsManager(config_dir=tmp_path)
    stored = sm.set_api_key("openai", "sk-another-secret")
    if not stored:
        import pytest

        pytest.skip("no keyring backend available on this system")
    assert sm.get_api_key("openai") == "sk-another-secret"
    sm.clear_api_key("openai")
    assert sm.get_api_key("openai") is None
