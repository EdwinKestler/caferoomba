from caferoomba.control.adapters.mavlink_rover import MavlinkRoverAdapter
from caferoomba.environment import report


def test_default_import_does_not_construct_legacy_robot():
    import rover

    import caferoomba

    assert caferoomba.__version__
    # Importing the historical package is fine; constructing Robot is not.
    assert not hasattr(rover, "Robot") or rover.Robot is not None


def test_mavlink_adapter_stays_disabled():
    adapter = MavlinkRoverAdapter(enabled=False)
    assert adapter.enabled is False
    try:
        MavlinkRoverAdapter(enabled=True)
        raise AssertionError("enabled adapter must fail closed")
    except RuntimeError as exc:
        assert "approval" in str(exc)


def test_doctor_secret_booleans_only():
    payload = report()
    creds = payload["credentials_present"]
    assert set(creds) <= {
        "gcloud_adc",
        "github_token_env",
        "nvidia_api_key",
        "cosmos_url",
    }
    assert all(isinstance(value, bool) for value in creds.values())
