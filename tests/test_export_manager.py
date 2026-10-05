from livestt.export.export_manager import ExportManager


def test_to_txt_writes_exact_text(tmp_path):
    path = tmp_path / "out.txt"
    ExportManager.to_txt("Привет, мир.", path)
    assert path.read_text(encoding="utf-8") == "Привет, мир."


def test_to_markdown_contains_title_and_body(tmp_path):
    path = tmp_path / "out.md"
    ExportManager.to_markdown("Первая строка.\nВторая строка.", path, title="Моя расшифровка")
    content = path.read_text(encoding="utf-8")
    assert content.startswith("# Моя расшифровка\n")
    assert "Первая строка." in content
    assert "Вторая строка." in content
