# CRUSHED IT: the asset list

Two kinds of asset go into the cubes. Both are made on this machine by the local AI. Nobody writes prompts
by hand; the prompts are in `ai/prompts/` and the build steps are in `ai/BUILD_GUIDE.md`.

## 1. Flat art: the 34 print slots

Every printed surface in the collection is a slot. A slot is one PNG at a fixed size. The compositor
(`blender/`) wraps it onto the object, crushes it, lights it, and hashes it into the manifest. Three variants
per slot is the target; one variant is dealt per object, so three covers the whole collection without repeats
looking obvious.

Draw them: `python3 ai/draw_slots.py` (prompts in `ai/prompts/<slot>.txt`). See what's filled:
`python3 ai/draw_slots.py --check`.

| slot | size | where it shows up | what goes on it |
|---|---|---|---|
| sticker | 256x128 | laptops, lunchboxes, skateboards, cases | a trashy sticker, invented brand |
| keypad | 192x256 | corded phones, brick phones, calculators | a worn 12-key keypad |
| notebook | 256x320 | spiral notebooks, crumpled paper | a doodled page |
| chart | 320x240 | the crumpled chart contaminant | a top-then-cliff price chart |
| pcb | 256x256 | PCB chunks, broken electronics | a circuit board top |
| can_print | 512x256 | soda cans, energy cans (wrap) | an energy drink label, invented brand |
| ramen | 320x256 | the emergency ramen packet | a noodle packet front |
| screen | 256x192 | CRTs, handhelds, flip phones | an error screen |
| griptape_art | 128x512 | skateboards | tall griptape graphic |
| battery | 256x128 | AA batteries (wrap) | a battery wrapper |
| cd_marker | 256x256 | burned CDs | a marker-scrawled disc label |
| app_grid | 160x344 | smartphones, tablets | a home screen of invented apps |
| lockscreen | 160x344 | smartphones | a lock screen |
| vape_print | 256x96 | disposable vapes (wrap) | a candy vape wrapper, invented flavor |
| mag_cover | 192x256 | magazines (UNDER THE MATTRESS and the regular deal) | a men's magazine cover, invented masthead, pin-up illustration |
| poster | 384x256 | centerfolds | a pin-up poster, invented caption |
| tissue_print | 128x128 | tissue boxes | a tissue box panel, invented brand |
| foil_print | 64x64 | foil packets | a square foil wrapper, invented brand |
| scratch_print | 96x224 | scratch tickets | a scratch ticket |
| beer_print | 256x192 | beer cans (wrap) | a cheap lager label, invented brand |
| matchbook_print | 96x128 | matchbooks | a club matchbook, invented club |
| mug_print | 256x128 | coffee mugs (GM) | the GM mug wrap |
| sun_label | 256x96 | sunscreen (SLOW MOTION) | a sunscreen label |
| hdd_label | 192x128 | hard drives (LANDFILL DRIVE) | a drive label that says WALLET.DAT |
| street_sign | 512x128 | the HOOD ST sign | a green street sign |
| newspaper | 256x320 | newspapers | THE LEDGER front page |
| play_money | 256x120 | play money | a play bill |
| card_print | 96x128 | playing cards | one card face |
| badge_print | 96x128 | press badges | a PRESS laminate |
| spectrum_print | 512x64 | ribbon cables (LOW RES) | a rainbow ribbon |
| sock_print | 64x128 | tube socks | a sock, flat |
| watch_face | 128x128 | smartwatches | a watch face |
| sanitizer_label | 256x96 | hand sanitizer | a sanitizer label |
| gas_label | 128x96 | gas cans (GAS FEES) | a GAS FEES warning label |

House rules for every slot: fills the frame, bold, readable at thumbnail size, American spelling, invented
brand names and mastheads only. Humor-adult, degen, never explicit.

## 2. Objects: 3D props built in Blender

The compositor is a Blender library of generic objects (about 150). Each is a short Python function that
builds geometry from boxes, cylinders, spheres, lathes, tubes, extrusions and lofts, and returns its
materials. `ai/BUILD_GUIDE.md` has the whole recipe plus a worked example, and
`python3 blender/catalog.py --names <object>` renders what you built so you can look at it.

Wanted next (each one is a function in `blender/crushed/objects/`): see the OPEN list at the end of
`ai/BUILD_GUIDE.md`. When you add an object, add its display name and three inventory notes to
`blender/crushed/lore.py` and, if it belongs in a one-of-one, add it to `MONOCULTURES` in
`blender/crushed/recipe.py`.
