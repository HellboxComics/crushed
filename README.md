# CRUSHED IT

Not characters. Not PFPs. Not lore.

888 perfect 12-inch cubes of crushed nostalgic shit, generated procedurally in Blender.
Same camera, same floor, same lights, same cube. Completely different guts.

```
CRUSHED IT #0044
CRUSHED IT #0718: CCFF00
```

---

## What's in here

| Path | What it is |
|---|---|
| `blender/` | The generator. Pure Blender Python, runs with the `bpy` wheel or inside Blender 5.0 |
| `blender/crushed/objects/` | The item library: 78 era objects, 11 contaminants, 20 kinds of filler debris, 44 one-of-one props |
| `assets/` | Drop-in art slots: a PNG named for a printed surface replaces the procedural print everywhere |
| `ai/` | The local AI's side of the work: the asset list, one prompt per print slot, the drawing-room runner, the Blender build guide |
| `collection/` | `manifest.json` (every block, frozen), `provenance.txt` (its sha256), `sealed.json` (the on-chain seal tree), `RARITY.md`, per-token `metadata/`, `DECISIONS.md` |
| `contracts/` | `CrushedIt.sol` on OpenSea's SeaDrop, Foundry tests, deploy script for Robinhood Chain |
| `scripts/` | One-paste Mac scripts (setup, time one block, render all 888) and the seal tree builder |
| `site/` | Black page, one rotating cube, `WE KEPT THE IMPORTANT SHIT.`, `VIEW THE PILE` |

## How a block is made

Each token id seeds a recipe (`blender/crushed/recipe.py`). The recipe is built as layers, back to front:

1. **Core** – a dark, dense mass, so every gap reads as more compressed stuff.
2. **Big items** – CRTs, boom boxes, skateboards, pressed hardest; they become the back layer.
3. **Headliner** – the first thing you see, placed front and center, dented but recognizable.
4. **Heroes** – 26–46 era objects spread across the five visible faces, oriented so their best side faces out.
5. **Contaminant** – in 88 of 888 blocks, one crypto item buried near the surface.
6. **Filler** – 60–110 flattened housings, packaging, film, paper, PCB chunks, glass and wire.
7. **Dressing** – loose wires, cassette tape ribbon wrapped around the whole thing, goo or water.
8. **Straps** – two steel bands with a crimp seal stamped with the token number. The straps are always the top
   layer: nothing pokes through them.

Every object is bent, folded, crumpled and dented, then pressed into the cube with a soft clamp: whatever
sticks out is flattened against the crusher plates, layered so overlapping surfaces stack instead of
z-fighting, and wrinkled in proportion to how hard it was squeezed. Textures follow the geometry (they read
a stored rest position), so a notebook's ruled lines bend with the page.

Every object is original, generic geometry built from primitives in code, with invented brands and
mastheads. Era is carried by shape, color and material. Printed surfaces can be swapped for drop-in art
(`assets/README.md`); the local AI draws those from the prompts in `ai/prompts/`.

## Traits and rarity

All counts are exact: conditions, one-of-ones and contaminants are dealt from fixed decks, not rolled.
Full tables: [`collection/RARITY.md`](collection/RARITY.md).

| Trait | Values |
|---|---|
| Era | 1985-1990 (178) · 1991-1996 (178) · 1997-2002 (177) · 2003-2008 (178) · 2009-2026 (177), in token order |
| Condition | JUNK 737 · SOAKED 36 · BURNT 36 · CLEAN 27 · BIOHAZARD 19 · GOLD 11 · 22 one-of-ones |
| Headliner | the front-and-center object (Sneaker, CRT Monitor, Corded Phone, Smartphone, Magazine, ...) |
| Contaminant | None 800 · Tiny Red Candle 16 · Paper Hand 12 · Emergency Ramen 11 · Crumpled Chart 10 · Broken Rocket 9 · Dead Bull 8 · Bear (Thriving) 7 · Gold Coin 6 · Suspicious Rectangle 5 · Diamond 3 · **Tiny Green Candle 1** |
| Pressure | Firm Handshake → Hydraulic → Industrial → Unreasonable (the collection gets progressively more fucked up) |
| Smell | Hot Dust on a CRT, New Plastic, Arcade Carpet, Blue Raspberry, ... Burnt Popcorn, Science Lab, Don't |
| Recovered From | Under the Bed, Dad's Junk Drawer, Mom's Minivan, ... House Fire (Everyone's Fine) |
| Tape | None · Loose Ends · Wrapped · Mummified · Fully Mixtaped |
| Loose Wires | None · A Few · Several · Concerning · Fire Hazard |
| Finish | CLEAN only: BONE, OBSIDIAN, CHROME, GRAPE, SAFETY ORANGE, ICE |
| Gilded | GOLD only: which object turned gold |
| One of One | the 22 below |
| Weight (lb) | computed from what's inside |
| Item Count | how many recognizable things went in |

**Conditions**

- **JUNK** – most of them.
- **CLEAN** – almost entirely one material and color.
- **BURNT** – charred, blistered, embers still glowing in the cracks, soot on the floor.
- **SOAKED** – wet, oxidized, moldy, sitting in its own puddle.
- **BIOHAZARD** – something deeply questionable leaked into it. It glows.
- **GOLD** – one totally inappropriate gold object buried inside.

**The 22 one-of-ones**

| | | |
|---|---|---|
| **EMPTY** – the straps holding nothing | **UNCRUSHED** – the pile, the minute before | **SOLID GOLD** – everything in it is gold |
| **MIXTAPE** – forty cassettes and all their tape | **LEFTOVERS** – pizza crust, only pizza crust | **DOUBLE A** – every battery that went missing from a remote |
| **SCREEN TIME** – every screen you stared at, still on | **BULL TRAP** – they all bought the top | **LANDFILL DRIVE** – every drive that held something that mattered |
| **BLOW ON IT** – forty-four cartridges, all blown on | **STILL ALIVE** – thirty-eight virtual pets, one still alive | **GAS FEES** – gas cans and receipts |
| **SAVE ICON** – sixty-four floppies | **COASTERS** – every burned CD that ended up under a drink | **GM** – good morning, thirty-two times |
| **COLD STORAGE** – hardware wallets, frozen solid | **SLOW MOTION** – the beach, in slow motion | **UNDER THE MATTRESS** – everyone's mother knew |
| **LOW RES** – a bedroom studio at 3 A.M. (gift) | **CCFF00** – one color, three shapes (gift) | **STOP THE PRESSES** – bulls, bears and pigs (gift) |
| **CLAY DAY** – clay bulls, bears, pigs and frogs (gift) | | |

The four gift blocks are part of the team's 44 and are minted to the people they were made for.

## Metadata

Every token generates its own metadata from its recipe, so the traits always match the render.
The description is an evidence log:

```json
{
 "name": "CRUSHED IT #0044",
 "description": "Recovered from Dad's Junk Drawer. Smells like arcade carpet. Contents (partial): 1 Yo-Yo (string tied to a finger for 3 years); 1 Cassette Tape (recorded off the radio, DJ talks over every intro); 2 Calculators (solar panel covered by a sticker); ... Contents may have settled.",
 "attributes": [{"trait_type": "Era", "value": "1985-1990"}, {"trait_type": "Condition", "value": "JUNK"}, ...]
}
```

## Running the generator

Blender 5.0, or Python 3.11 with the `bpy==5.0.1` wheel and `numpy==1.26.4`. `--device auto` uses a GPU when
there is one (Metal on a Mac). On a Mac, `scripts/mac_time_one.sh` sets everything up and times one block;
`scripts/mac_render_all.sh` renders all 888 overnight.

```sh
pip install bpy==5.0.1 numpy==1.26.4 pillow

python3 blender/generate.py --token 44                               # one block (PNG in renders/)
python3 blender/generate.py --range 1 888 --res 1024 --samples 96 --skip-existing
python3 blender/generate.py --showcase                               # the site's 100-block pile
python3 blender/generate.py --token 44 --turntable 96                # frames for the homepage cube
python3 blender/generate.py --sealed                                 # the pre-reveal image
python3 blender/generate.py --verify                                 # does this machine rebuild the frozen collection?

python3 blender/catalog.py --group special --out docs/catalog_special.png     # item sheets
python3 blender/generate.py --manifest --metadata ipfs://<images-cid>         # freeze + metadata for all 888
python3 blender/export_site.py --pile
python3 blender/export_site.py --turntable renders/0044_frames
python3 blender/slots.py                                             # templates for every art slot
```

Preview the site with `python3 -m http.server -d site 8000`. It's fully static.

## Fair mint

1. Freeze the collection: `python3 blender/generate.py --manifest`. `collection/provenance.txt` is the sha256 of
   `manifest.json`, which also covers every drop-in art file.
2. Render all 888, then `python3 scripts/seal_tree.py build`: the Merkle root over every final JPEG and its
   metadata goes into the deploy as `IMAGE_ROOT`.
3. Pick a secret, commit `keccak256(secret)`, deploy with the provenance hash and the image root. All immutable.
4. `mintTeam`: 40 random blocks to the team, the 4 gifts to their people as tokens 1–4. Then SeaDrop opens the
   free public mint.
5. Sold out (or the deadline passes): anyone calls `reveal(secret)`. The offset mixes the secret with a block
   hash; `recipeOf(t)` is the on-chain mapping. Gifts are pinned, the other 884 are shuffled.
6. Publish renders and metadata by recipe id. Any holder can then **seal** their block: upload the full 1024px
   JPEG and metadata in 24 KB chunks with the Merkle proof (`scripts/seal_tree.py proof <recipe>`), and
   `tokenURI` serves it from the chain forever.

## Contract

`contracts/src/CrushedIt.sol` extends OpenSea's `ERC721SeaDrop` (audited, unchanged, pinned at commit 757590f):
SeaDrop free mint with per-wallet limits set on SeaDrop, the team's 44 with pinned gift ids, commit-reveal
shuffle with no chain randomness needed, holder-paid on-chain seal (SSTORE2 chunks, Merkle-verified image and
metadata, data-URI `tokenURI`), 5.99% ERC-2981 royalties, ERC-4906 refresh events. Works with ERC-6551
token-bound accounts as-is.

```sh
cd contracts
git submodule update --init --recursive
forge test
forge script script/Deploy.s.sol --rpc-url robinhood_testnet --broadcast --verify
```

Robinhood Chain is an Arbitrum Orbit chain: mainnet 4663, testnet 46630 (Blockscout explorers are in
`foundry.toml`). SeaDrop lives at `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5` there.

## Brand note

Keep Robinhood's marks out of the artwork, metadata and contract attributes. Robinhood Chain's brand
guidelines prohibit incorporating them into NFTs or digital collectibles. Nothing in this repo does, and
nothing reproduces any other real brand: every masthead, label and logo in the cubes is invented.
