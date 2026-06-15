def test_open_browser_calls_webbrowser_with_local_url(monkeypatch):
    import app as app_module

    opened = {}
    monkeypatch.setattr(app_module.webbrowser, "open", lambda url: opened.setdefault("url", url))

    app_module._open_browser()

    assert opened["url"] == "http://127.0.0.1:5000/"


def test_url_is_loopback_only():
    import app as app_module

    assert app_module.URL == "http://127.0.0.1:5000/"
