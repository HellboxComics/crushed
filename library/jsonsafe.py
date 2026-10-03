"""NUMBERS FROM THE IMAGE MATH ARE SAVED AS PLAIN NUMBERS: the picture math (numpy) hands back its own number types
(float32, int64, arrays), and Python's JSON writer refuses them - one such number anywhere in a file being saved
stopped a whole build (2026-10-03, the Pop-Tarts: "Object of type float32 is not JSON serializable" while saving
the texture's sources list). Importing this module once in a program teaches every JSON save in that program to
write them as ordinary numbers and lists, so no save anywhere can fail this way again.

    import jsonsafe  # noqa: F401   (at the top of a program; nothing else to do)
"""
import json

_plain = json.JSONEncoder.default


def _default(self, o):
    shape = getattr(o, "shape", None)
    if shape == () and hasattr(o, "item"):           # one numpy number: float32, int64, bool_ ...
        return o.item()
    if hasattr(o, "tolist"):                         # a numpy array
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=str)
    return _plain(self, o)


if getattr(json.JSONEncoder.default, "__name__", "") != "_default":
    json.JSONEncoder.default = _default
