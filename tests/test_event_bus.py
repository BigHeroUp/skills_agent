from core.kernel.events import Event, EventBus


def test_event_bus_publish_subscribe_and_filter():
    bus = EventBus()
    received = []

    bus.subscribe("capability.execution.started", lambda event: received.append(event.id))
    bus.publish(
        Event(
            type="capability.execution.started",
            payload={"capability_name": "health_check"},
            metadata={"source": "test"},
        )
    )
    bus.publish(Event(type="custom.event", payload={"value": 1}))

    assert len(received) == 1
    assert bus.event_count == 2
    assert len(bus.get_events()) == 2
    assert len(bus.get_events(event_type="capability.execution.started")) == 1
    assert bus.get_events(limit=1)[0].type == "custom.event"


def test_event_bus_handler_failure_does_not_break_publish():
    bus = EventBus()
    observed = []

    def _broken_handler(event):
        raise RuntimeError("boom")

    bus.subscribe("test.event", _broken_handler)
    bus.subscribe("test.event", lambda event: observed.append(event.type))

    published = bus.publish(Event(type="test.event"))

    assert published.type == "test.event"
    assert observed == ["test.event"]
