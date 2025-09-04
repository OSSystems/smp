"""Tests for the ForwardTree protocol (header flag, payload, round-trip)."""

import cbor2

from smp import header as smphdr
from smp.os_management import EchoWriteRequest

# Firmware wire-format reference (freedom-zephyr docs/forward_tree/protocol.md):
# route [2, 1, 1] -> hop count 2 in the MSB nibble, port for hop h at bit (h-1)*4.
FT_211 = [2, 1, 1]
FT_211_WIRE = bytes.fromhex("2000000000000011")


def _cbor_len(**kwargs: object) -> int:
    return len(cbor2.dumps(kwargs, canonical=True))


def test_forward_tree_wire_format_matches_firmware() -> None:
    """The encoded payload must match the firmware spec's worked example."""
    assert bytes(smphdr.ForwardTree(FT_211)) == FT_211_WIRE


def test_constructor_sets_flag_length_and_bytes() -> None:
    req = EchoWriteRequest(d="x", forward_tree=smphdr.ForwardTree(FT_211))

    assert req.header.flags & smphdr.Flag.FORWARD_TREE
    assert req.header.length == _cbor_len(d="x") + smphdr.ForwardTree.SIZE
    assert req.BYTES[-smphdr.ForwardTree.SIZE :] == FT_211_WIRE


def test_non_forward_tree_message_is_unchanged() -> None:
    """Control: a message without a forward tree keeps the legacy wire format."""
    req = EchoWriteRequest(d="x")

    assert req.header.flags == smphdr.Flag(0)
    assert req.header.length == _cbor_len(d="x")
    assert req.forward_tree is None
    assert len(req.BYTES) == smphdr.Header.SIZE + _cbor_len(d="x")


def test_set_forward_rebuilds_bytes() -> None:
    req = EchoWriteRequest(d="x")
    req2 = req.set_forward(smphdr.ForwardTree(FT_211))

    assert req2 is not req
    assert not (req.header.flags & smphdr.Flag.FORWARD_TREE)  # original untouched
    assert req2.header.flags & smphdr.Flag.FORWARD_TREE
    assert req2.header.length == req.header.length + smphdr.ForwardTree.SIZE
    assert req2.BYTES[-smphdr.ForwardTree.SIZE :] == FT_211_WIRE


def test_loads_round_trip_forward_tree() -> None:
    wire = EchoWriteRequest(d="x", forward_tree=smphdr.ForwardTree(FT_211)).BYTES

    back = EchoWriteRequest.loads(wire)

    assert back.header.flags & smphdr.Flag.FORWARD_TREE
    assert back.BYTES == wire
    assert back.forward_tree is not None
    assert bytes(back.forward_tree) == FT_211_WIRE
    assert back.forward_tree.ft == FT_211


def test_loads_non_forward_tree_leaves_field_none() -> None:
    req = EchoWriteRequest(d="x")

    back = EchoWriteRequest.loads(req.BYTES)

    assert back.forward_tree is None
    assert back == req


def test_forward_tree_codec_round_trip() -> None:
    """Encode then decode recovers the logical [hops, *ports] list."""
    for ft in ([1, 5], [3, 1, 2, 3], [0]):
        recovered = smphdr.ForwardTree.loads(bytes(smphdr.ForwardTree(ft))).ft
        assert recovered == ft
