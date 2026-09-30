# CRUSHED

Not characters. Not PFPs. Not lore.

888 perfect 12-inch cubes of crushed nostalgic shit, generated procedurally in Blender.
Same camera, same floor, same lights, same cube. Completely different guts.

```
CRUSHED #0044
```

---

## What's in here

| Path | What it is |
|---|---|
| `blender/` | The generator. Pure Blender Python, runs in Blender or with the `bpy` wheel |
| `blender/crushed/objects/` | The item library: 55 era objects, 11 contaminants, 19 kinds of filler debris |
| `collection/` | `manifest.json` (every block, frozen), `provenance.txt` (its sha256), `RARITY.md`, per-token `metadata/`, `sealed.json` + `contract.json` templates |
| `contracts/` | `Crushed.sol` (ERC-721, 888 max), Foundry tests, deploy script for Robinhood Chain |
| `site/` | Black page, one rotating cube, `WE KEPT THE IMPORTANT SHIT.`, `VIEW THE PILE` |
| `docs/` | Item catalog sheets and sample renders |

## How a block is made

Each token id seeds a recipe (`blender/crushed/recipe.py`). The recipe is then built as layers, back to front:

1. **Core** – a dark, dense mass, so every gap reads as more compressed stuff.
2. **Big items** – CRTs, boom boxes, skateboards, pressed hardest; they become the back layer.
3. **Headliner** – the first thing you see, placed front and centre, dented but recognisable.
4. **Heroes** – 26–46 era objects spread across the five visible faces, oriented so their best side faces out.
5. **Contaminant** – in 88 of 888 blocks, one crypto item buried near the surface.
6. **Filler** – 60–110 flattened housings, packaging, film, paper, PCB chunks, glass and wire.
7. **Dressing** – loose wires, cassette tape ribbon wrapped around the whole thing, goo or water.
8. **Straps** – two rusty steel bands with a crimp seal stamped with the token number.

Every object is bent, folded, crumpled and dented, then pressed into the cube with a soft clamp: whatever
sticks out is flattened against the crusher plates, layered so overlapping surfaces stack instead of
z-fighting, and wrinkled in proportion to how hard it was squeezed. Textures follow the geometry (they read
a stored rest position), so a notebook's ruled lines bend with the page.

Nothing is AI-generated and nothing copies a real product: every object is original, generic geometry
built from primitives in code. Era is carried by shape, colour and material.

## Traits and rarity

All counts are exact: conditions, one-of-ones and contaminants are dealt from fixed decks, not rolled.
Full tables: [`collection/RARITY.md`](collection/RARITY.md).

| Trait | Values |
|---|---|
| Era | 1985-1990 · 1991-1996 · 1997-2002 · 2003-2008 (222 each, in token order) |
| Condition | JUNK 751 · SOAKED 36 · BURNT 36 · CLEAN 27 · BIOHAZARD 19 · GOLD 11 |
| One of One | EMPTY · UNCRUSHED · SOLID GOLD · MIXTAPE · LEFTOVERS · DOUBLE A · SCREEN TIME · BULL TRAP |
| Headliner | the front-and-centre object (Sneaker, CRT Monitor, Corded Phone, Pager, ...) |
| Contaminant | None 800 · Tiny Red Candle 16 · Paper Hand 12 · Emergency Ramen 11 · Crumpled Chart 10 · Broken Rocket 9 · Dead Bull 8 · Bear (Thriving) 7 · Gold Coin 6 · Suspicious Rectangle 5 · Diamond 3 · **Tiny Green Candle 1** |
| Pressure | Firm Handshake → Hydraulic → Industrial → Unreasonable (the collection gets progressively more fucked up) |
| Smell | Hot Dust on a CRT, New Plastic, Arcade Carpet, Blue Raspberry, ... Burnt Popcorn, Science Lab, Don't |
| Recovered From | Under the Bed, Dad's Junk Drawer, Mom's Minivan, ... House Fire (Everyone's Fine) |
| Tape | None · Loose Ends · Wrapped · Mummified · Fully Mixtaped |
| Loose Wires | A Few · Several · Concerning |
| Finish | CLEAN only: BONE, OBSIDIAN, CHROME, GRAPE, SAFETY ORANGE, ICE |
| Gilded | GOLD only: which object turned gold |
| Weight (lb) | computed from what's inside |
| Item Count | how many recognisable things went in |

**Conditions**

- **JUNK** – most of them.
- **CLEAN** – almost entirely one material and colour.
- **BURNT** – charred, blistered, embers still glowing in the cracks, soot on the floor.
- **SOAKED** – wet, oxidised, moldy, sitting in its own puddle.
- **BIOHAZARD** – something deeply questionable leaked into it. It glows.
- **GOLD** – one totally inappropriate gold object buried inside.

**One of ones**

- **EMPTY** – the steel straps holding absolutely nothing. Same cube dimensions.
- **UNCRUSHED** – the original chaotic pile, sitting where the block should be.
- **SOLID GOLD** – every single thing in it is gold.
- **MIXTAPE** – forty cassettes and every inch of their tape.
- **LEFTOVERS** – pizza crust. Only pizza crust.
- **DOUBLE A** – every AA battery that ever went missing from a remote.
- **SCREEN TIME** – every screen you ever stared at, still on.
- **BULL TRAP** – twenty-two dead bulls, twelve red candles, one bear doing fine.

## Metadata

Every token generates its own metadata from its recipe, so the traits always match what's in the render.
The description is an evidence log:

```json
{
 "name": "CRUSHED #0044",
 "description": "Recovered from Dad's Junk Drawer. Smells like arcade carpet. Contents (partial): 1 Yo-Yo (string tied to a finger for 3 years); 1 Cassette Tape (recorded off the radio, DJ talks over every intro); 2 Calculators (solar panel covered by a sticker); ... Contents may have settled.",
 "attributes": [{"trait_type": "Era", "value": "1985-1990"}, {"trait_type": "Condition", "value": "JUNK"}, ...]
}
```

## Running the generator

Blender 4.2+ or the `bpy` wheel (Python 3.11):

```sh
pip install bpy pillow            # or use Blender's own python

# one block (PNG in renders/)
python3 blender/generate.py --token 44
python3 blender/generate.py --token 44 --res 2048 --samples 160     # final quality
blender -b -P blender/generate.py -- --token 44                     # inside Blender

# a range, the site's 100-block showcase, a turntable, the pre-reveal image, the .blend
python3 blender/generate.py --range 1 888 --res 2048 --skip-existing
python3 blender/generate.py --showcase
python3 blender/generate.py --token 44 --turntable 96
python3 blender/generate.py --sealed
python3 blender/generate.py --token 44 --blend

# item catalog sheets
python3 blender/catalog.py --group era --era 2 --out docs/catalog_era2.png

# manifest, provenance hash, rarity report, and metadata for all 888
python3 blender/generate.py --manifest --metadata ipfs://<images-cid>

# site assets
python3 blender/export_site.py --pile
python3 blender/export_site.py --turntable renders/0044_frames
```

Preview the site locally with `python3 -m http.server -d site 8000` (it fetches JSON, so `file://` won't work).
It's fully static: host `site/` anywhere.

Rendering is Cycles on CPU or GPU. A 1024px block takes ~1–2 minutes on a 4-core CPU; set
`sc.cycles.device = "GPU"` in `blender/crushed/stage.py` if you have one.

## Fair mint

1. Freeze the collection: `python3 blender/generate.py --manifest`. `collection/provenance.txt` is the sha256
   of `manifest.json`.
2. Pick a secret, commit `keccak256(secret)`, deploy with the provenance hash. Both are immutable.
3. Mint. Everyone gets a sealed block.
4. Close mint, call `reveal(secret)`. The contract derives an `offset` from the secret and a recent block
   hash; token `t` is recipe `((t - 1 + offset) % 888) + 1` (`recipeOf(t)` on-chain).
5. Render and publish with that offset: `generate.py --range 1 888 --offset <offset>` and
   `--metadata <cid> --offset <offset>`. Stamps, names and files all use the token number.
6. `setBaseURI`, then `freezeMetadata()` when you're sure.

## Contract

`contracts/src/Crushed.sol`: OpenZeppelin v5 ERC-721, 888 max supply, public mint with per-wallet cap,
owner mint, immutable provenance + reveal commit, sealed URI until reveal, one-way metadata freeze,
ERC-2981 royalties, ERC-4906 metadata update events.

```sh
cd contracts
git submodule update --init --recursive
forge test
cp .env.example .env && source .env
forge script script/Deploy.s.sol --rpc-url robinhood_testnet --broadcast --verify
```

Robinhood Chain is an Arbitrum Orbit chain: mainnet chain id 4663, testnet 46630 (Blockscout explorers are
configured in `foundry.toml`). Confirm the RPC URLs against the official docs before deploying.

Being an ERC-721, every block can own things through an ERC-6551 token-bound account. That's the later,
unannounced mechanic: owners crush things into their block, the block re-renders with them inside,
and ERC-4906 tells marketplaces to refresh. Don't lead with it.

## Brand note

Keep Robinhood's marks out of the artwork, metadata and contract attributes. Robinhood Chain's brand
guidelines prohibit incorporating them into NFTs or digital collectibles. Nothing in this repo does, and
nothing reproduces any other real brand either.
