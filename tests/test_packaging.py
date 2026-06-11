import os
import sys


def test_app_data_dir_dev(monkeypatch):
    import config
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert config.app_data_dir() == config.BASE_DIR


def test_app_data_dir_frozen(monkeypatch, tmp_path):
    import config
    exe = tmp_path / "EDIAIBehaviourTracker.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)
    assert config.app_data_dir() == str(tmp_path)


def test_resource_base_dev(monkeypatch):
    import app
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert app._resource_base() == os.path.dirname(os.path.abspath(app.__file__))


def test_resource_base_frozen(monkeypatch, tmp_path):
    import app
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert app._resource_base() == str(tmp_path)
