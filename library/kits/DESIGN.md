# THE ASSET MAKER, REDESIGNED AROUND KITS (2026-10-03)

Cody's direction (2026-10-03, after four days of patches): "be careful of patching vs redesigning ... my AI should
follow the same process as if I gave you something to go create in blender, except my AI should have a more diverse
type of brains ... It should recognize the general category (ie this is a battery, this is pants, this is a cd, this
is a box for a food item, this is a magazine, etc.) and than build more specifically to what I want. The reason being
is all batteries are similar, all magazines are similar, all pants are similar, its the details that change."

## The idea

The center of the asset maker is the KIND OF THING (a kit), not the photo.

A kit is built once, properly, by Claude (setup), and holds what every item of that kind shares:
1. its standard shape at real size, with settings (variants: AA / AAA / C / D; 12 oz / 8.4 oz can; NES / SNES / N64
   cartridge; jewel case / slim case / paper sleeve ...)
2. its PRINT ZONES: where artwork goes, and what kind of zone each is
     wrap  - artwork wrapped all the way around a round thing (battery sleeve, can body, bottle label)
     rect  - a flat printed panel on a face (box panels, cartridge label, VHS spine, card face, magazine cover)
     disc  - a round end (can lid, battery end) - usually bare material, sometimes printed
     fabric- a garment's cloth: color, pattern, stripes, logo patches
     form  - no print: the item's own molded/organic shape and material carry it (figure, toy, food)
3. what the photos must show (which views, per zone) - this drives the photo hunt
4. how to check it (exact size from the kit; each zone compared with its own real photo; printed words read off)

Your AI (Cody's local brains) fills in only what changes: which kit and variant, the era's own version (its name and
marks then), the artwork of each zone (read from real photos, rewritten as clean artwork with the exact words), and
the colors / small settings. Claude never makes an asset; Claude makes kits and the workflow.

Items no kit covers (~1,000 of the 2,668 one-offs) use the GENERAL kit: your AI plans the parts (assembly) or makes the
shape with Hunyuan (soft/organic things), with the same zone logic (front/back/left/right/top/bottom rect zones or a
form zone) and the same checks.

## The flow per item (the same steps a person takes in Blender)

1. KNOW IT      kit + variant from the catalog name and a photo (fast brain); the era's own version: what it was sold
                as in its era and how that version looked (web titles + names read on era photos + memory)
2. FIND IT      a photo hunt directed by the kit's zones and the era words ("90s Duracell PowerCheck AA back")
3. PICK         the item's main photo: picked by itself only when one clearly qualifies (the careful brain says so,
                measured big enough, never a quick-look-only photo, Cody's note met); else the best go to Cody's phone
4. ZONE ART     for each zone: the photos that show it (sorted per zone by the fast brain), turned into its artwork:
                wrap -> unrolled from each photo, the AI writes ONE layout for the whole wrap from every unrolled view
                        with the exact words read by the text reader (Apple Vision), drawn as crisp artwork
                rect -> straightened from the photo, room light taken out, item-specific parts kept exact
                disc / fabric / form -> material + color from the photos (fabric: stripes, logo patches)
5. BUILD        the kit's builder at the variant's real size, zones UV-mapped, each zone's artwork on it, real
                materials per part, the insides from the kit's recipe
6. CHECK        exact (size from the kit, every zone printed, words read off the model, materials in range, mesh,
                insides) + each zone rendered straight-on and compared with its real photo (two looks)
7. FIX          your AI's engineer works on the kit's builder or the item's zone art (never the checks)

## Brains, one per job

  sort    a small fast vision brain: which zone a photo shows, is it the right product, quick ranking
  judge   the big vision brain (thinking on) only where judgment matters: the pick, the zone comparisons
  read    Apple Vision text reader (ocrmac) - exact words, never guessed by a language model
  cutout  the drawing room's cut-out model
  draw    the label drawer (Qwen-Image-Edit) - only to clean glare, never to write words
  shape   Hunyuan3D (organic shapes)
  code    a coding brain for the engineer
Roles are filled from the brains installed on the Mac (brains.json, inventoried at start) and kept by measured
bakeoffs (the best brain per job stays).

## Kits planned (by how many catalog items they cover - counted 2026-10-03 from assets/plan/items.json)

  box_carton (food/product boxes, big-box software)   card_flat (cards, tickets, flyers, money, posters)
  device_shell (small electronics)                     disc_media (CD, DVD, CD-R, floppy, MiniDisc) + cases
  audio_cassette                                       vhs (tape, clamshell, slipcase)
  cell_battery (AA, AAA, C, D, 9V)                     can (12 oz, 8.4 oz, 16 oz)
  bottle_jar                                           cartridge (NES, SNES, N64, Game Boy, Genesis)
  controller                                           booklet (magazine, comic, manual, book)
  wrapper_bag (candy wrappers, chip bags, pouches)     garment_pants / garment_top / footwear / hat
  figure_toy (form + Hunyuan)                          food_item (form + Hunyuan)
  general (assembly / Hunyuan)

## Soft and molded things (plush toys, figures, food) - planned 2026-10-03 after the Furby

What went wrong with the old one-photo way (Furby, 2026-10-03, measured): Hunyuan got ONE photo, so it guessed the
back (plain white), made the top of the head a flat lid and the ears mush; the hang tag in the photo was built as part
of the toy; the paint is the photo's own colors with the photo's light still in them (texture median 182 vs the
photo's 188), so lit again in the viewer the light gray and pale pink read as white; the texture is stitched from many
small photo pieces (the patchy look).

The kit way, as a person would build it in Blender:
1. KIND        plush_toy / figure / food_item, with the parts every such thing has (plush toy: body, eyes, nose or
               beak, ears, feet, tags) and which of them are hard plastic, fabric or fur
2. FIND        real photos from the front, both sides and the back (the dossier's hunt, zone words per kit)
3. CLEAN       anything that is not the item is erased from each photo before it is used: hang tags, price
               stickers, hands, stands, other things, watermarks - found by the sorting brain with a box, erased by
               the drawing room, and checked: nothing outside those boxes may change
4. BUILD       the body's shape from every cleaned view (several views, never one); hard parts (eyes, beak, feet)
               as their own solid parts with their own materials (glossy plastic, felt); fur as a fur material with
               the photo's colors taken DOWN to true color (the photo's light taken out), not a photo pasted on
5. CHECK       each side rendered and compared with its own real photo; the colors measured against the photos

## After an asset is perfect: the marketplace lane (Cody, 2026-10-03)

One of the two lanes for finished assets. It starts only AFTER an asset passes every check and Cody keeps it - the
asset is perfected first, then it conforms to these steps. One master catalog, the same clean package sent to several
stores (no exclusivity anywhere):
  stores, in order   CGTrader and Fab first (same first ~10-25 excellent assets), then his own site (canonical
                     product pages, direct checkout), TurboSquid Basic (never SquidGuild - it needs exclusivity),
                     Superhive (the full Blender source), Sketchfab (showcase only), Unity (themed packs of 25-100)
  every package      the .blend master with named parts and collections (CLEAN, CUTAWAY, EXPLODED, CRUSH,
                     GAME_READY), FBX / GLB, 4K and 2K PBR maps, LOD0-LOD3, a collision mesh, variants where they
                     exist (closed, peeled wrapper, cutaway, exploded, crushed)
  every listing      interactive preview, turntable, wireframe, cutaway, exploded and crushed pictures; title and
                     keywords by object and era ("1998 Alkaline AA Battery - Full Interior / Cutaway / PBR")
  three levels       single objects; themed packs from the catalog's own themes (Sleepover, Road Trip, Arcade
                     Birthday, 90s School...); big era libraries ("The 1990s", the complete library)
  learning           which kinds, prices, thumbnails and keywords sell decides what gets built next
Already made for every kept asset: .blend, .glb, .fbx, .usdc, .obj/.mtl, .3ds, .ma, the phone-size .glb, the cutaway
picture. Still to build for this lane: LODs, collision mesh, 2K maps, named collections, turntable / wireframe /
exploded / crushed pictures, listing text, one folder per store. No store accounts are opened by the asset maker -
that is Cody's to do.
  brand              BUILTINSIDE - "3D objects modeled all the way through" (handles in order: BuiltInside,
                     BuiltInside3D, BuiltInsideAssets); kept separate from Harrow and CRUSHED on every store
  the standard       every listing: EXTERIOR, INTERIOR, MATERIALS, PHYSICS (density, hardness, deformation), BREAK,
                     STATES (clean / opened / damaged / crushed), GAME (optimized mesh, collision, LODs), PBR;
                     thumbnail badges FULL INTERIOR, PHYSICS READY, DESTRUCTIBLE, PBR, GAME READY

## Build order

  1. kit system + cell_battery, can, box_carton - proven end to end on the Duracell, a soda can, the Pop-Tarts box
  2. media: audio_cassette, vhs, disc_media + cases, cartridge, card_flat, booklet
  3. garments, figure_toy / food_item (Hunyuan), wrapper_bag, device_shell, general
  4. brains: inventory, per-job bakeoffs, speed target ~15 minutes per item

## Status

  2026-10-03
  - kits.py + family_library.json: kits carry variants (with sources), a template, zones with what each zone
    normally carries (typical, in words) and what a rebuilt zone draws from facts (elements).
  - The variant is trusted only when the catalog name says it or the catalog size agrees (15%) - a soup can is not
    forced into a soda can, an N cell not into an AA (kits.pick_variant).
  - cylindrical_cell: AA / AAA / C / D from the measured AA master (template "cell"); Blender builds all four at
    their exact standard sizes (selftest builds the AAA on the Mac every start).
  - beverage_can: 12 fl oz standard size (CMI 202); the outline is traced from the photo AT that size until a
    measured can master exists.
  - folding_carton: six zones; the dossier's must-show list and eraprint's rebuilt sides both read the kit
    (one list, not three copies).
  - Round labels: the label layout is told what a label like this normally carries (zone typical) and to fill the
    parts no photo saw only with confirmed words that belong there.
  - The lathe builder orients every face by the direction the outline walks (an AAA's pressed end was turned inside
    out by the old face-by-face guess, and its steel threw 100 mm spikes when given thickness).
  - Brains: the photo exam picks the judge and sorter from every installed vision brain (brainjobs.py).
  Next: dossier hunt words from the kit's zones; prove can + carton end to end; media kits.
