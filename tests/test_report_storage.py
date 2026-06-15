import os


def test_reports_dir_is_under_app_data_dir(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    import report_storage

    d = report_storage.reports_dir()
    assert d == os.path.join(str(tmp_path), "Rapoarte_Salvate")


def test_save_report_writes_file_and_returns_path(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    import report_storage

    path = report_storage.save_report("demo.pdf", b"%PDF-1.4 test")

    assert os.path.isfile(path)
    assert path == os.path.join(str(tmp_path), "Rapoarte_Salvate", "demo.pdf")
    with open(path, "rb") as f:
        assert f.read() == b"%PDF-1.4 test"
