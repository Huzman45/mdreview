"""Finding this machine's own private LAN address.

Split deliberately in two. Enumerating interfaces is platform-specific and cannot
be exercised in a unit test, so it is one small function that shells out.
Choosing among the results is pure, and that is where every rule lives — which
means preference order, refusing loopback, and failing when nothing is suitable
are all tested directly rather than depending on whatever interfaces the test
machine happens to have.
"""

from __future__ import annotations

import ipaddress
import os
import shutil
import subprocess
from pathlib import Path

#: Address range preferred when the machine has more than one private address.
#: Defaults to the range the operator confirmed their tablet can reach, directly
#: and over VPN. An interface name would be a worse default: `en7` here is a USB
#: adapter, and there are eight `utun` tunnels.
ENV_PREFER = "MDREVIEW_LAN_PREFIX"
DEFAULT_PREFER = "10."

AUTO = "auto"


class NoLanAddress(RuntimeError):
    """No private address belongs to this machine."""


def preferred_prefix() -> str:
    return os.environ.get(ENV_PREFER, DEFAULT_PREFER)


def is_candidate(address: str) -> bool:
    """Whether an address could be bound for LAN access.

    Loopback is excluded because binding it leaves the service unreachable from
    another device, which is the whole point. Anything non-private is excluded
    because the tool refuses to serve on a public address.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified:
        return False
    return parsed.is_private


def choose(addresses: list[tuple[str, str]], *, prefer: str | None = None) -> str:
    """Pick the best private address from ``(interface, address)`` pairs.

    Pure, so every rule below is directly testable.
    """
    prefer = preferred_prefix() if prefer is None else prefer
    candidates = [addr for _, addr in addresses if is_candidate(addr)]
    if not candidates:
        raise NoLanAddress(
            "no private network address found on this machine; connect to a "
            "network or pass an explicit --host"
        )
    for address in candidates:
        if address.startswith(prefer):
            return address
    return candidates[0]


def _tool(name: str, *fallbacks: str) -> str | None:
    """Locate a system tool by absolute path.

    Bare names are not enough: `ifconfig` lives in /sbin, which is absent from a
    trimmed PATH and from the minimal environment launchd hands a service. Both
    would make discovery silently report no addresses at all.
    """
    found = shutil.which(name)
    if found:
        return found
    for candidate in fallbacks:
        if Path(candidate).exists():
            return candidate
    return None


def interface_addresses() -> list[tuple[str, str]]:
    """Enumerate this machine's interfaces and their IPv4 addresses (macOS)."""
    ifconfig = _tool("ifconfig", "/sbin/ifconfig", "/usr/sbin/ifconfig")
    ipconfig = _tool("ipconfig", "/usr/sbin/ipconfig", "/sbin/ipconfig")
    if not ifconfig or not ipconfig:
        return []

    try:
        names = subprocess.run(
            [ifconfig, "-l"], capture_output=True, text=True, timeout=5, check=True
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return []

    found: list[tuple[str, str]] = []
    for name in names:
        try:
            result = subprocess.run(
                [ipconfig, "getifaddr", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        address = result.stdout.strip()
        if address:
            found.append((name, address))
    return found


def detect(*, prefer: str | None = None) -> str:
    """This machine's best private LAN address."""
    return choose(interface_addresses(), prefer=prefer)


def resolve_host(host: str | None) -> str | None:
    """Substitute a concrete address for ``auto``.

    Called before the bind safety check, never after, so discovery cannot widen
    what may be bound: whatever this returns is validated by the same rule as an
    address typed by hand.
    """
    if host is not None and host.strip().lower() == AUTO:
        return detect()
    return host
