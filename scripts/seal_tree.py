#!/usr/bin/env python3
"""
THE SEAL TREE -- the Merkle root the contract checks when a holder puts a block on-chain.

    python3 scripts/seal_tree.py build            renders/*.png + collection/metadata -> collection/sealed.json
    python3 scripts/seal_tree.py proof 718        the calldata for sealing recipe 718: chunks, meta, proof
    python3 scripts/seal_tree.py check            every leaf recomputes from the files on disk

Leaf = keccak256(abi.encodePacked(uint256 recipeId, sha256(jpeg), keccak256(meta), keccak256(subtitle))).
The JPEG is the final 1024px image at quality 90 (progressive, 4:4:4). `meta` is the metadata JSON with the
braces, the name and the image removed: it starts with `,"description":` and ends after the attributes,
because the contract writes the name itself from the token number (CRUSHED IT #0044) and adds the image.
`subtitle` is the one-of-one's name ("CCFF00") or empty. Pairs are hashed sorted, odd nodes paired with
zero: the same scheme as the murky library the tests use.

This freezes the art. Run it once, after the final render, and put the root in the deploy.
"""
import glob
import hashlib
import io
import json
import os
import sys

from Crypto.Hash import keccak

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERS = os.path.join(ROOT, "renders")
META = os.path.join(ROOT, "collection", "metadata")
OUT = os.path.join(ROOT, "collection", "sealed.json")
JPEG_DIR = os.path.join(ROOT, "collection", "jpeg")
CHUNK = 24_000
SUPPLY = 888


def k(b):
    return keccak.new(digest_bits=256, data=b).digest()


def pair(a, b):
    return k(a + b) if a < b else k(b + a)


def jpeg_bytes(recipe):
    """The on-chain image: q90 progressive 4:4:4 JPEG of the 1024px render, cached in collection/jpeg."""
    os.makedirs(JPEG_DIR, exist_ok=True)
    out = os.path.join(JPEG_DIR, f"{recipe:04d}.jpg")
    if os.path.exists(out):
        return open(out, "rb").read()
    from PIL import Image
    src = os.path.join(RENDERS, f"{recipe:04d}.png")
    with Image.open(src) as im:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=90, progressive=True, subsampling=0, optimize=True)
    data = buf.getvalue()
    open(out, "wb").write(data)
    return data


def meta_bytes(recipe):
    """(meta fragment, subtitle) as the contract expects them: no braces, no name, no image."""
    m = json.load(open(os.path.join(META, str(recipe))))
    name = m.pop("name")
    subtitle = name.split(": ", 1)[1] if ": " in name else ""
    m.pop("image", None)
    m.pop("animation_url", None)
    s = json.dumps(m, separators=(",", ":"), ensure_ascii=False)
    assert s.startswith("{") and s.endswith("}")
    return ("," + s[1:-1]).encode(), subtitle


def leaf(recipe, img, meta, subtitle):
    return k(recipe.to_bytes(32, "big") + hashlib.sha256(img).digest() + k(meta) + k(subtitle.encode()))


def tree(leaves):
    levels = [leaves]
    while len(levels[-1]) > 1:
        lv = levels[-1]
        nxt = [pair(lv[i], lv[i + 1]) for i in range(0, len(lv) - 1, 2)]
        if len(lv) % 2:
            nxt.append(pair(lv[-1], b"\0" * 32))
        levels.append(nxt)
    return levels


def proof(levels, i):
    out = []
    for lv in levels[:-1]:
        sib = i ^ 1
        out.append(lv[sib] if sib < len(lv) else b"\0" * 32)
        i //= 2
    return out


def build():
    missing = [r for r in range(1, SUPPLY + 1) if not os.path.exists(os.path.join(RENDERS, f"{r:04d}.png"))]
    if missing:
        sys.exit(f"{len(missing)} renders missing (first: {missing[0]:04d}); render everything first")
    leaves, sizes = [], {}
    for r in range(1, SUPPLY + 1):
        img, (meta, sub) = jpeg_bytes(r), meta_bytes(r)
        leaves.append(leaf(r, img, meta, sub))
        sizes[r] = len(img)
        if r % 100 == 0:
            print(f"[{r}/{SUPPLY}] {int(100 * r / SUPPLY)}%", flush=True)
    levels = tree(leaves)
    root = levels[-1][0]
    doc = {"root": "0x" + root.hex(), "leaves": ["0x" + x.hex() for x in leaves], "jpeg_bytes": sizes,
           "jpeg": "quality 90, progressive, 4:4:4, 1024px", "chunk": CHUNK,
           "total_bytes": sum(sizes.values())}
    json.dump(doc, open(OUT, "w"), indent=1)
    print(f"root {doc['root']}\n{SUPPLY} leaves, {doc['total_bytes'] / 1e6:.1f} MB of JPEG in all -> {os.path.relpath(OUT, ROOT)}")


def show_proof(recipe):
    doc = json.load(open(OUT))
    leaves = [bytes.fromhex(x[2:]) for x in doc["leaves"]]
    levels = tree(leaves)
    img, (meta, sub) = jpeg_bytes(recipe), meta_bytes(recipe)
    assert leaf(recipe, img, meta, sub) == leaves[recipe - 1], "the files on disk no longer match the frozen tree"
    chunks = [img[i:i + CHUNK] for i in range(0, len(img), CHUNK)]
    print(json.dumps({"recipe": recipe, "chunks": ["0x" + c.hex() for c in chunks], "meta": meta.decode(),
                      "subtitle": sub, "proof": ["0x" + p.hex() for p in proof(levels, recipe - 1)],
                      "root": doc["root"]}, indent=1))


def check():
    doc = json.load(open(OUT))
    bad = 0
    for r in range(1, SUPPLY + 1):
        meta, sub = meta_bytes(r)
        if "0x" + leaf(r, jpeg_bytes(r), meta, sub).hex() != doc["leaves"][r - 1]:
            bad += 1
            print(f"recipe {r}: leaf changed")
    root = "0x" + tree([bytes.fromhex(x[2:]) for x in doc["leaves"]])[-1][0].hex()
    print(f"{SUPPLY - bad}/{SUPPLY} leaves match; root {'matches' if root == doc['root'] else 'DOES NOT MATCH'}")
    sys.exit(1 if bad or root != doc["root"] else 0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build()
    elif cmd == "proof":
        show_proof(int(sys.argv[2]))
    elif cmd == "check":
        check()
    else:
        print(__doc__)
