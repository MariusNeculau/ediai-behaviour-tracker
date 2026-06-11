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
