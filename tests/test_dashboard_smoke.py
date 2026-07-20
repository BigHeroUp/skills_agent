def test_dashboard_application_builds_without_starting_server():
    from app_dash import app, runtime_state

    assert app.layout is not None
    assert app.callback_map
    assert runtime_state.processing_status
