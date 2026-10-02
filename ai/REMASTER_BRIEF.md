# BRIEF: CRUSHED.BUZZ REMASTER -- every object, label and name made real, on this Mac, hands off

From Harrow (2026-10-01): "go back through everything ... make all assets look even more realistic ... turns the
parody's back into the actual thing it was referencing ... I am going for epic, and in art canonical creates epic."
The goal: every object in the 888 is the REAL product as it actually looked, with the real brand, from real photos.
Project: ~/crushed-render/repo (branch claude/epic-galileo-iubypk). The collection stays ON HOLD (collection/HOLD)
until Harrow says the remaster is done. Never remove HOLD yourself.

Harrow watches everything on his phone: https://crushed-remaster.pages.dev (every object, its real photos, its
reference sheet, the four-side review, and a spin-in-3D view of every model). Keep it publishing.

## What runs by itself (the clock: `crushed remaster`, crushed_remaster.sh)
    .venv/bin/python ai/remaster.py --limit 20      the next objects, one after another
    .venv/bin/python ai/remaster/labels.py          the real packaging labels
For each object: real photos (ai/remaster/refs.py: Wikimedia Commons, then Openverse; free, reuse-licensed) ->
the drawing room paints a 2x2 reference sheet OVER those photos (so it copies the real thing) -> the sculptor makes
the shape -> the inside is painted -> Blender sizes it, paints it on, adds the inside layer -> review on the page.
An object is made once its prompts exist: prompts/<name>.txt (outside) and prompts/<name>.inside.txt (inside).

## Your jobs, in this order (models are always made whole and new; the renderer crushes them). After every change: `.venv/bin/python ai/plan_check.py` must say ALL GOOD, then
## `git add -A assets/plan assets/real ai/remaster && git commit -m "<what>" && git pull --rebase -q`.

### 1. Photo searches (fast, do first)
For EVERY object (see ai/remaster/expected.txt) write prompts/<name>.query: the exact real product a photo search
would find, brand + model + year. "Nintendo 64 console 1996", "Surge soda can 1997", "Tamagotchi 1997 egg".
Without one, the search uses the first words of the prompt, which finds worse photos.

### 2. Make every prompt the REAL thing
Read every prompts/<name>.txt. Where it describes a parody or a vague "generic" item, rewrite it as the real
product it was referencing: real brand, real model, real year, real colors, logo and label placement, materials,
wear. One paragraph, ends "single object, plain background, product photo". Same for <name>.inside.txt (what you'd
see split open: a cartridge's green board and gold contacts, a chocolate's filling, a plush's stuffing).
After rewriting an object that already has a remaster waiting, run `ai/remaster.py --only <name> --redo`.

### 3. Real names everywhere (assets/real/)
The code's names and notes are parodies ("Blockbusted", "Surj", "Nintendont", "WALKMAYBE"). Write the real ones:
- assets/real/names.json  {"object_name": "Real Display Name"}  for every object whose display name is a parody
  or generic ("Nintendo 64", "Surge", "Blockbuster Video Case")
- assets/real/notes.json  {"object_name": ["note", "note"]}  every note that contains a parody brand, rewritten
  with the real brand, same dry voice, short
- assets/real/ones.json   {"ONE-OF-ONE TITLE": "lore line"}  every one-of-one lore line with a parody brand
To read the current names/notes/lore: `python3 -c "import bpy,sys;sys.path.insert(0,'blender');from crushed.objects
import load;load();from crushed import lore;import json;print(json.dumps([lore.NAMES,lore.NOTES,lore.ONE_OF_ONES]))"`

### 4. Every one-of-one: at least 15 things to discover, the more the better
Harrow (2026-10-01): "every 1 of 1 ... at minimum 15 unique traits to be discovered, the more the better ... I am
looking for people to be absolutely infatuated with each and every one." plan_check prints a TO DO line with every
one-of-one under 15 distinct objects. Take them one at a time: add real, specific, surprising objects that belong
in that world (the deep cut a real fan would scream at, not filler), as planned objects (job 5 format) added with
{"TITLE": {"extra": [["object", count]]}} in assets/plan/ones.json. Aim for 20+.
Also audit each for missing brands:
For every one-of-one (recipe.ONE_OF_ONES), ask: what are the brands/products everyone remembers from that thing,
and are they in it? (CONSOLE WARS needs the real consoles of both sides; RETIREMENT PLAN needs the real Beanie
Babies everyone hoarded; DIAL-UP needs the AOL disc.) For each missing one: add it as a planned object (job 5
format) and add it to that one-of-one's mix in assets/plan/ones.json ("extra" list, see below). Write what you
added and why to ai/remaster/audit_ones.md, one line each. Never remove anything Harrow put in.

### 5. Design the 40 planned one-of-ones (assets/plan/)
Each new object goes in assets/plan/items.json:
    "dreidel": {"display": "Dreidel", "size": [0.04, 0.04, 0.055], "eras": [0,1,2,3,4], "group": "special",
                "mass": 0.02, "hero": [0,-1,0], "notes": ["spun for gelt, lost to a cousin", "the shin side, again"]}
  size = real width, depth, height in METERS. group "era" (+ "weight": 0.12) = also shows up rarely in regular
  cubes (snacks, sodas, toys a kid in that country knew); "special" = one-of-ones only. Aim ~40% "era".
  Reuse an existing object instead of a new one when it is the same thing (check expected.txt and the code).
Plus its prompts: prompts/<name>.txt, .inside.txt, .query (jobs 1-2 rules).
Each one-of-one goes in assets/plan/ones.json:
    "EIGHT NIGHTS": {"mix": [["dreidel", 8], ["gelt_bag", 6], ...], "lore": "one dry sentence",
                     "flavor": ["Smell", "Recovered From", "Headliner Display Name"], "era": [1,2],
                     "fillers": ["gelt_coin", "crumpled_paper"], "soft": 0.5, "no_wires": true}
  mix: at least 15 distinct objects (20+ is better), counts summing to 50-70. era: the eras its stuff was current (0 1985-90,
  1 1991-96, 2 1997-02, 3 2003-08, 4 2009-26). To ADD to an existing one-of-one (job 4), use
  {"TITLE": {"extra": [["object", count]]}} -- plan_check will tell you if the format is wrong.
Respect: for religious holidays only the food, lights, gifts, decorations, toys and clothes. Never holy books,
scripture, deity or saint images, or prayer objects. WINDOW SHOPPING is adult but not explicit: no nudity.
Real brands are wanted everywhere (that is Harrow's call). Real PEOPLE are not: no celebrity faces or likenesses.

The 40 (title, theme, the item ideas Harrow approved; design each item properly):
- RED ENVELOPE (Lunar New Year): red envelope, firecracker string, mandarin oranges, red paper lantern, new year cake, Chinese knot, candy tray box, White Rabbit candy, zodiac figurine, door couplet
- KRAMPUSNACHT (Krampus night): birch switch, chains, horned devil mask, Advent calendar, Lebkuchen, Stollen, boot with orange and nuts, cowbell, nutcracker
- KWANZAA (Kwanzaa): straw mat, ears of corn, fruit basket, kente cloth, unity cup, handmade gifts, red/green/black candles, sweet potato pie, greeting card
- OFRENDA (Day of the Dead): sugar skull, marigolds, papel picado, pan de muerto, tall candles, framed photo, copal, clay jarrito, alebrije, hot chocolate tablets
- DIYA (Diwali): clay diyas, rangoli powder, ladoo, kaju katli, sparkler box, flowerpot firework, paper lantern, marigold garland, sweet box
- GULAL (Holi): color powder packets, pichkari water gun, gujiya, thandai glass, water balloons, color-stained white kurta
- EIDI (Eid): money envelopes, dates, maamoul, sheer khurma bowl, henna cone, glass bangles, new-clothes box, sweet box, toy cap gun, lantern
- EIGHT NIGHTS (Hanukkah): dreidel, chocolate gelt, latkes, jelly donut, candle box, blue-and-silver wrapping paper, applesauce jar, gift socks
- PROST (Oktoberfest): glass stein, giant pretzel, gingerbread heart, beer mat, feathered hat, weisswurst, mustard tube, lederhosen suspender
- CARNAVAL (Rio Carnival): feather headdress, sequins, tamborim drum, confetti, caipirinha cup, Havaianas, Guaraná can, brigadeiros, glitter, mask
- MOONCAKE (Mid-Autumn): mooncake, mooncake tin, paper lanterns, pomelo, tea tin, glow-stick lantern
- SONGKRAN (Thai water war): pump water gun, silver water bowl, talcum powder, jasmine garland, Thai tea bag, elephant pants, goggles, waterproof phone pouch
- BOXING DAY (UK Christmas): Quality Street tin, Terry's Chocolate Orange, selection box, cracker with paper crown, Christmas pudding, TV guide, Argos catalogue, torn toy box
- LA TOMATINA (Spain's tomato fight): squashed tomatoes, swim goggles, soaked T-shirt, flip-flop, ham on a greased pole, sangria cup, water pistol
- GOTCHA (April Fools): whoopee cushion, joy buzzer, fake vomit, snake-in-a-can, rubber chicken, X-ray specs, fake dog poop, chattering teeth, squirting flower, rubber pencil, fake ice cube with fly
- PROBED (Aliens and UFOs): Area 51 souvenir, foil hat, glow alien plush, blurry UFO photo, UFO toy, alien autopsy tape, crop-circle pamphlet, chrome probe gag gift, green slime, alien candy
- WINDOW SHOPPING (Red light district): red neon window frame, red lightbulb, lace lingerie, fishnet stocking, condom wrappers, feather boa, stroopwafel, tulip, bike bell, clog keychain, beer can, coffeeshop menu
- BOARDWALK (Atlantic City): casino chips, slot coin cup, saltwater taffy box, boardwalk fries cup, Boardwalk deed card, dice, buffet ticket, keno card, seagull feather, pageant sash
- MISSING PIECES (Board games): Monopoly money, top hat token, Mouse Trap parts, Operation board, Hungry Hippos marbles, Connect Four discs, Battleship pegs, Guess Who board, Twister spinner, Trouble dome, Clue cards, box lid
- INSERT DISK 2 (DOS games): 5¼ and 3½ floppies, big-box PC game, shareware mailer, Sound Blaster card, joystick, hint book, code wheel, manual, locking disk box
- BLACKLIGHT (Bedroom wall): the 13 bedroom pieces above, plus incense box, black light bulb, sticky tack
- BUT WAIT THERE'S MORE (Infomercials): Snuggie, ShamWow, Chia Pet, ThighMaster, Ginsu knife box, Ab Roller, OxiClean tub, Magic Bullet, Pocket Fisherman, rotisserie box, Bedazzler
- SEWING KIT (Grandma's house): blue butter-cookie tin full of thread, hard candy dish, doilies, TV Guide, plastic sofa cover, Werther's, pill organizer, toilet roll doll, rotary phone
- PRIZE COUNTER (Arcade birthday): tokens, ticket strips, finger trap, spider ring, sticky hand, mini slinky, army men, bouncy ball, Pixy Stix, birthday crown, skee-ball, pizza slice
- MALL RAT (The mall): food court tray, Orange Julius cup, Claire's earring card, Sam Goody bag, pretzel wrapper, chain wallet, Spencer's gag gift, Abercrombie bag, Sbarro plate
- SLEEPOVER (Sleepover): sleeping bag, nail polish, talking board, prank-call phone, Bop It, popcorn bag, face mask packet, truth-or-dare cards, Mad Libs, flashlight
- LOST AND FOUND (School bin): single mittens, retainer in a napkin, one sneaker, hoodie, Walkman, water bottle, lunchbox, lone sock, glasses, gym shorts
- GARAGE SALE (Garage sale): 25-cent price stickers, fondue set, cassette rack, ceramic cat, Tupperware lid, workout tape, waffle iron, lamp shade, cash box, sign
- TIME CAPSULE (Buried in 1999): shoebox, letter to future self, CD single, Tamagotchi, Y2K newspaper, Polaroids, pog, trading card, school photo, friendship bracelet
- CRYPTID (Bigfoot and friends): blurry photos, plaster footprint cast, night-vision camcorder, trail cam, Bigfoot crossing sign, Nessie plush, beef jerky, tape recorder, foil sandwich
- SUMMER CAMP (Summer camp): friendship bracelets, bug juice cup, care package, mess kit, bug spray, camp T-shirt, lanyard, flashlight, s'mores, canteen, letter home
- ROAD TRIP (Road trip): road map, gas station snacks, car bingo, fuzzy dice, tape adapter, pine-tree air freshener, souvenir spoon, motel key, toll ticket, travel game
- PROM NIGHT (Prom): wrist corsage, disposable camera, limo receipt, bow tie, one high heel, prom ticket, cummerbund, glitter hair spray, boutonniere, tiara
- WITH A TOY (Kids' meal): meal box, toy in its bag, a toy set, fry box, soda cup, straw wrapper, ketchup packets, playground sock, paper crown
- SICK DAY (Home sick): cough syrup with cup, saltines, ginger ale, soup can, thermometer, kid vitamins, tissue box, handheld game, heating pad, bucket, popsicle
- MIDNIGHT SHOWING (Movie theater): popcorn bucket, souvenir cup, 3D glasses, ticket stubs, boxed candy, nacho tray, poster standee scrap, glow sticks, cupholder
- KICKFLIP (Skate park): snapped deck, finger skateboards, scooter wheel, light-up skate shoes, rollerblade, BMX peg, grip tape, skate video, energy drink, wax block
- DRESS CODE (Banned outfits): slap bracelets, color-change shirt, scrunchies, wide-leg jeans, light-up sneakers, tattoo choker, butterfly clips, trucker hat, charity band, foam clog
- EXTINCT (Dinosaurs): bag of plastic dinosaurs, fossil dig kit, dino nuggets, glow skeleton, dino lunchbox, roaring toy, amber keychain, dino egg
- DUCK AND COVER (Fallout shelter): gas mask, Geiger counter, canned goods, hand-crank radio, fallout shelter sign, canteen, pamphlet, powdered milk, pill box, crate

### 5b. How every object crushes (assets/plan/behavior.json)
Every model is made WHOLE and NEW, the way it looked on the shelf. The renderer does the crushing, all the objects
pressed together in the bale, and each one gives way the way its material really does. For EVERY object (code-built
and planned) set {"how": ..., "hard": 0..1} in assets/plan/behavior.json. A first guess from the names is already
there; check every line and fix what's wrong.
  crumple  thin metal, foil, wrappers, chip bags, soda cans: wrinkles everywhere, presses very flat
  fold     card, paper, boxes, magazines, posters, tickets: sharp creases, flattens in layers
  squish   plush, foam, rubber, fabric, fruit, gummy candy, sneakers: squashes and bulges, no creases
  dent     solid metal, die-cast cars, tins, tools, coins, keys: dents, keeps its shape
  snap     hard plastic, ceramic, glass, cartridges, consoles, CD cases, VHS: breaks into a few big pieces
  crumble  cookies, crackers, chalk, cake, chocolate, pretzels, mooncakes: breaks into many chunks
  hard     how much force it takes: a chip bag 0.1, a Game Boy 0.7, a die-cast car 0.95
Write the inside prompt to match: a snapped cartridge shows its board, a crumbled mooncake its yolk.

### 5c. Real size and real material for EVERY object (assets/plan/behavior.json "size" and "mat")
Everything in a bale is life size next to everything else: a ring is ring-sized beside a console. "size" is the
real [width, depth, height] in meters of the actual product (a 1996 Nintendo 64: [0.26, 0.19, 0.073]; a Tamagotchi:
[0.04, 0.015, 0.05]). The current values are the code's guesses: check every one against the real product.
"mat" is what it is MADE of, so it looks like it under the lights: clay things are clay, metal is metal, plastic is
plastic, paper is paper. One of: plastic, soft_plastic, metal, foil, paper, card, glossy_print, fabric, rubber,
clay, ceramic, glass, wood, food, chocolate, candy, foam, wax. Check every line.

### 6. The real labels (ai/remaster/labels/<era>.txt)
The crushed cans, cartons, chip bags and wrappers packed behind the objects in every bale wear parody labels.
Write 40 real ones per era file 0.txt..4.txt, one per line: `slug | what the label looks like | photo search`.
Sodas, beers, energy drinks, chips, candy bars, gum, cereal, fast-food cups and bags, batteries, cleaning products,
juice boxes, of that era and the international markets (Kinder, Haribo, Pocky, Tazos-era chips, Vimto, Parle-G).
No tobacco. The clock makes them; Harrow approves them (`ai/remaster/labels.py --approve`).

### 7. Look and judge (only if you can see images)
If you have an image model: for every review.png write `<name> PASS` or `<name> REDO <why>` to
ai/remaster/verdicts.txt; a REDO gets a better prompt and `--only <name> --redo`; three tries then `KEEP CODE`.
If you can't see images, skip this: Harrow judges on the phone page.

## Rules (his, standing)
- You never approve models or labels and never remove collection/HOLD. Harrow does.
- American spelling. Never delete a file: anything replaced goes to ~/Desktop/_to delete/ with a note.
- Never spend money. Free sources only. Nothing private leaves this machine.
- Slop is a bug. Epic is the bar.
- If the drawing room or the sculptor is off, `note` it in plain words and stop that cycle; don't open them yourself.
- The sculptor's license (Hunyuan3D-2) asks that AI-made work be labeled as AI-made when published.
- `note` progress once a day in plain words: objects made, approved, waiting; labels; what's next.
