import importlib.util
import os


def load_handler():
    path = os.path.join(os.path.dirname(__file__), "../lambdas/health/handler.py")
    spec = importlib.util.spec_from_file_location("health_handler", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_health_error_does_not_expose_internal_exception(monkeypatch):
    handler = load_handler()

    monkeypatch.setattr(handler, "_check_dynamodb", lambda: {"estado": "error"})
    monkeypatch.setattr(handler, "_check_redis", lambda: {"estado": "ok"})

    result = handler.main({}, None)

    assert result["statusCode"] == 503
    assert "detalle" not in result["body"]
