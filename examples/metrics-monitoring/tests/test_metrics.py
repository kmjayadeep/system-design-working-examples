from app.metrics import metric_key


def test_metric_key_namespaces_metric():
    assert metric_key("cpu") == "metric:cpu"
