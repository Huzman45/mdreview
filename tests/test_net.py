"""Address selection is pure, so every rule is tested without real interfaces."""

from __future__ import annotations

import pytest

from mdreview import net
from mdreview.net import NoLanAddress


def test_a_private_address_is_chosen() -> None:
    assert net.choose([("en0", "192.168.0.111")]) == "192.168.0.111"


def test_the_preferred_range_wins() -> None:
    addresses = [("en0", "192.168.0.111"), ("en7", "10.31.41.9")]
    assert net.choose(addresses, prefer="10.") == "10.31.41.9"


def test_order_does_not_defeat_the_preference() -> None:
    addresses = [("en7", "10.31.41.9"), ("en0", "192.168.0.111")]
    assert net.choose(addresses, prefer="192.168.") == "192.168.0.111"


def test_falls_back_when_the_preference_is_absent() -> None:
    assert net.choose([("en0", "192.168.0.111")], prefer="10.") == "192.168.0.111"


def test_loopback_is_never_chosen() -> None:
    """Binding loopback would leave the service unreachable, defeating the point."""
    with pytest.raises(NoLanAddress):
        net.choose([("lo0", "127.0.0.1")])


def test_loopback_is_skipped_in_favour_of_a_real_address() -> None:
    addresses = [("lo0", "127.0.0.1"), ("en7", "10.31.41.9")]
    assert net.choose(addresses) == "10.31.41.9"


def test_public_addresses_are_never_chosen() -> None:
    with pytest.raises(NoLanAddress):
        net.choose([("en0", "8.8.8.8")])


def test_link_local_is_never_chosen() -> None:
    """A self-assigned address means the interface has no working network."""
    with pytest.raises(NoLanAddress):
        net.choose([("en0", "169.254.10.1")])


def test_nothing_suitable_reports_clearly() -> None:
    with pytest.raises(NoLanAddress, match="no private network address"):
        net.choose([])


def test_garbage_addresses_are_ignored() -> None:
    addresses = [("en0", "not-an-ip"), ("en7", "10.31.41.9")]
    assert net.choose(addresses) == "10.31.41.9"


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("10.31.41.9", True),
        ("192.168.0.1", True),
        ("172.16.0.1", True),
        ("127.0.0.1", False),
        ("169.254.1.1", False),
        ("8.8.8.8", False),
        ("0.0.0.0", False),
        ("garbage", False),
    ],
)
def test_candidate_rules(address: str, expected: bool) -> None:
    assert net.is_candidate(address) is expected


def test_preference_is_configurable_by_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MDREVIEW_LAN_PREFIX", "192.168.")
    addresses = [("en7", "10.31.41.9"), ("en0", "192.168.0.111")]
    assert net.choose(addresses) == "192.168.0.111"


# -- auto resolution --------------------------------------------------------


def test_auto_is_substituted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(net, "interface_addresses", lambda: [("en7", "10.31.41.9")])
    assert net.resolve_host("auto") == "10.31.41.9"


def test_auto_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(net, "interface_addresses", lambda: [("en7", "10.31.41.9")])
    assert net.resolve_host("AUTO") == "10.31.41.9"


def test_a_concrete_host_passes_through() -> None:
    assert net.resolve_host("127.0.0.1") == "127.0.0.1"


def test_none_passes_through() -> None:
    assert net.resolve_host(None) is None


def test_auto_raises_when_nothing_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(net, "interface_addresses", lambda: [])
    with pytest.raises(NoLanAddress):
        net.resolve_host("auto")


def test_enumeration_returns_pairs() -> None:
    """The one platform-specific part; assert only its shape."""
    for entry in net.interface_addresses():
        assert isinstance(entry, tuple)
        assert len(entry) == 2
