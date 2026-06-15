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


def test_list_saved_reports_empty_when_no_folder(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path / "nope"))
    import report_storage
    assert report_storage.list_saved_reports() == []


def test_list_saved_reports_newest_first(monkeypatch, tmp_path):
    import os, time
    import config
    monkeypatch.setattr(config, "app_data_dir", lambda: str(tmp_path))
    import report_storage

    report_storage.save_report("old.pdf", b"%PDF-old")
    time.sleep(0.01)
    report_storage.save_report("new.csv", b"new")
    # asigură mtime distinct/ordonat
    folder = report_storage.reports_dir()
    os.utime(os.path.join(folder, "old.pdf"), (1000, 1000))
    os.utime(os.path.join(folder, "new.csv"), (2000, 2000))

    out = report_storage.list_saved_reports()
    assert [e["filename"] for e in out] == ["new.csv", "old.pdf"]
    assert all(e["generated"] for e in out)        # string nevid
    assert all("_mtime" not in e for e in out)      # câmp intern eliminat
