def assert_serialized_event(klass, data):
    actual = data.get("$type", None)
    assert (
        klass.__name__ == actual
    ), "Serialized event $type is '%s', but should be '%s'" % (actual, klass.__name__)
    _ = klass.from_json(data)
