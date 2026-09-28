"""Results frozen before the replay was made fast, and held ever since.

The replay of a big library protocol used to take minutes: every tip and well on a deck of 384
samples ends up carrying all 384, and every action copied all of them. The rewrite had to change
no result. It was checked against digests of real library traces, which may not be committed
(DECISIONS.md D-05); these are the same check on traces built here. The digests below were
computed with the replay as it was before the rewrite. If one changes, a result changed: that is
either a bug, or a decision to record in DECISIONS.md before the digest is updated.
"""

from __future__ import annotations

import random

import pytest

from provette.model import Trace
from provette.state import replay
from tests.state.builder import ABOVE, NAMES_96, TraceBuilder, plate, tip, trough, tube
from tests.state.digest import digest
from tests.state.test_properties import build


def random_stream(seed: int) -> Trace:
    rng = random.Random(seed)
    codes = [tuple(rng.randrange(12) for _ in range(4)) for _ in range(150)]
    return build((seed % 2 == 0, codes))  # type: ignore[arg-type]


def saturated_plate(declares: bool) -> Trace:
    """The shape that was slow: eight tips work through a whole plate that arrives full, column
    by column, several times over, so everything ends up carrying everything."""
    reagent = trough("A1")
    b = TraceBuilder({reagent: ("reagent", 14000.0)} if declares else {})
    tips = [tip(f"{row}1") for row in "ABCDEFGH"]
    b.pick_up(tips)
    for round_ in range(3):
        for col in range(1, 13):
            column = [plate(f"{row}{col}") for row in "ABCDEFGH"]
            b.aspirate(tips, [reagent] * 8, 10)
            if round_ == 1:
                b.aspirate(tips, [reagent] * 8, 5, height=ABOVE, parent="air_gap")
            b.dispense(
                tips, column, 15 if round_ == 1 else 10, height=ABOVE if col % 5 == 0 else 1.0
            )
            for _ in range(2):
                b.aspirate(tips, column, 30, parent="mix")
                b.dispense(tips, column, 30, parent="mix")
        b.blow_out(tips, [trough("A12")] * 8)
    b.drop(tips, returned=True)
    b.pick_up(tips)  # parked and picked up again: still carrying everything
    b.aspirate(tips, [plate(name) for name in NAMES_96[:8]], 20)
    b.dispense(tips, [tube("A1")] * 8, 20)
    b.drop(tips)
    return b.trace()


FROZEN = {
    "full plate, silent": "6dbf702b70b7ead5f8323c07b9fcc6235db4604b2b8033ac7b4ceeedad0dac5b",
    "full plate, declared": "447e5f52d53c727365add01306a7be6a5010d47d9c49d10f65667159adfeadf8",
    "random stream 0": "fa9124b267751ddf58e99d5fd3fb3c34974f34b3abbb27393642424294792814",
    "random stream 1": "9f6242d012d3a0941eb06d47fa4951807c9fc534192d42238743e7d61a35adfe",
    "random stream 2": "a7bbab2ccd85f25b36792ae28afdbef35c60e5811de3f5cfd957325b102f51b2",
    "random stream 3": "165016af70e29cfbcc3b96d343c8a48dfa7379502576690b0eb352970c72ae9a",
    "random stream 4": "6fc2b995093d2296e0ea380e7e9f9869150696cf9df7dd6f59b9e00f1282d64d",
    "random stream 5": "4673a875050a02181742adb3f9eea8b260d3cd0264388a07d56170fa7cbe7c32",
    "random stream 6": "ff2b8dd302e2ad4faf5201ffa4d48697b1775bb509d816d418652e16480501ea",
    "random stream 7": "c99a6572080e7f1db9d744b93db0a6241093c640b2905f9a4812e0ecc1fa7e72",
    "random stream 8": "7c6065ae8d65e2e8b55faa40518371e098f1880b2713d1f5199e11a8bdc72b55",
    "random stream 9": "4a52d1692146deeaf32ccaa792185726ae07ef3e04403fdfeb863e59fd5e533f",
    "random stream 10": "6033dd62310305469fc78b39051569580c0c6388122c25d9c7e0c8c36b7f14a4",
    "random stream 11": "9e0f7d50b5ce921199eaf5f95553fd6a1133ff136f2325fd0fdb02ed6ad8ec20",
    "random stream 12": "8febe1f553e4e135679fbdea4c9713fe785f08a85db9f44beff5c2b2b7d71dcf",
    "random stream 13": "48b7df2b32ed014a6c81edcfe3062a3c0fbd1cac670b321729e2fbee59637ba1",
    "random stream 14": "3c6ff080e6228da2645cb5ef6c2f0460ae9556074f33db39f39600e8347ad811",
    "random stream 15": "f10dbc4cc637c243ff5b66ff4e0dc3d6ce92185f690ea71e5f462fc93f52fc78",
    "random stream 16": "338ab3f5e6e0757c5d171383d8cd7a10591e1779dff956868071ddae955dfea1",
    "random stream 17": "8b8fea93d1d42b3ba5aea89ae6d2bf0fa77393da3fbc17f30fcf8904d527d212",
    "random stream 18": "dbf6ecc8c02a64d78e2dc6f1708630ed69024f18528eacfa92e293a156c748d9",
    "random stream 19": "a8c0010183f3ce167db163dfee029d97317c0bea685deecd42965403fbae57b9",
    "random stream 20": "1108020ea4e08761d9b3bd323fa4d970bf86f83458fa9483ee8fa081156fe65c",
    "random stream 21": "e37030c579809a5249a63e5bbf7d881fa8118fbe21cce79d77eed5999a0ffc14",
    "random stream 22": "118e54224c7f6d369fb1bec9514886d7136bc888e91620085e16ab7e533ce5cf",
    "random stream 23": "afee402db21a6893c33ec77d91861bc821e25de4a1f9e2a62a76f6f49f651f05",
}

TRACES = {
    "full plate, silent": lambda: saturated_plate(False),
    "full plate, declared": lambda: saturated_plate(True),
    **{f"random stream {seed}": (lambda seed=seed: random_stream(seed)) for seed in range(24)},
}


@pytest.mark.parametrize("name", TRACES)
def test_the_replay_gives_the_frozen_result(name: str) -> None:
    trace = TRACES[name]()
    assert digest(replay(trace), trace) == FROZEN[name]
