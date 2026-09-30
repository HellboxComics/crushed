"""Names, smells, provenance and inventory notes. The funny part."""

# display names for items; every trait value that names an object comes from here
NAMES = {
    "cassette": "Cassette Tape", "vhs": "VHS Tape", "boombox": "Boom Box", "walkman": "Portable Tape Player",
    "headphones": "Foam Headphones", "portable_cd": "Portable CD Player", "cd": "Burned CD",
    "jewel_case": "Jewel Case", "corded_phone": "Corded Phone", "pager": "Pager", "flip_phone": "Flip Phone",
    "candybar_phone": "Brick Phone", "crt": "CRT Monitor", "keyboard_chunk": "Keyboard (Partial)",
    "mouse": "Ball Mouse", "floppy": "Floppy Disk", "webcam": "Webcam", "digital_camera": "Digital Camera",
    "mp3_player": "MP3 Player", "memory_card": "Memory Card", "usb_stick": "USB Stick",
    "charger_brick": "Laptop Charger", "controller_16bit": "16-Bit Controller",
    "controller_modern": "Game Controller", "joystick": "Joystick", "game_cart": "Game Cartridge",
    "brick_game": "9999-in-1 Handheld", "handheld": "Handheld Console", "virtual_pet": "Virtual Pet",
    "puzzle_cube": "Puzzle Cube", "yoyo": "Yo-Yo", "army_men": "Army Man Squad", "sneaker": "Sneaker",
    "sunglasses": "Cheap Sunglasses", "roller_skate": "Roller Skate", "slap_bracelet": "Slap Bracelet",
    "notebook": "Spiral Notebook", "pencil": "No. 2 Pencil", "binder": "Three-Ring Binder",
    "lunchbox": "Metal Lunchbox", "slime": "Toy Slime", "skateboard": "Skateboard", "skate_wheel": "Skate Wheel",
    "aa_batteries": "AA Batteries", "tv_remote": "TV Remote", "extension_cord": "Power Strip",
    "pizza_crust": "Pizza Crust", "soda_can": "Soda Can", "energy_can": "Energy Drink",
    "film_canister": "Film Canister", "disposable_camera": "Disposable Camera", "glow_stick": "Glow Stick",
    "lighter": "Clear Lighter", "milk_caps": "Milk Caps", "calculator": "Calculator",
    # contaminants
    "broken_rocket": "Broken Rocket", "gold_coin": "Gold Coin", "red_candle": "Tiny Red Candle",
    "green_candle": "Tiny Green Candle", "paper_hand": "Paper Hand", "diamond": "Diamond",
    "hardware_wallet": "Suspicious Rectangle", "crumpled_chart": "Crumpled Chart", "bull": "Bull",
    "bear": "Bear", "ramen_packet": "Emergency Ramen",
    # 2009-2026
    "smartphone": "Smartphone", "tablet": "Tablet", "earbuds_case": "Earbud Case", "smartwatch": "Smartwatch",
    "vr_headset": "VR Headset", "drone": "Drone", "fidget_spinner": "Fidget Spinner", "selfie_stick": "Selfie Stick",
    "ring_light": "Ring Light", "vape": "Disposable Vape", "face_mask": "Face Mask", "hand_sanitizer": "Hand Sanitizer",
    "bluetooth_speaker": "Bluetooth Speaker", "power_bank": "Power Bank",
    # the shelf nobody admits to
    "magazine": "Magazine", "centerfold": "Centerfold", "tissue_box": "Tissue Box", "tissues": "Tissues",
    "foil_packet": "Foil Wrapper", "dice": "Dice", "poker_chip": "Poker Chip", "scratch_ticket": "Scratch Ticket",
    "beer_can": "Beer Can", "shot_glass": "Shot Glass", "matchbook": "Matchbook",
    # one-of-one props
    "hdd": "Hard Drive", "cold_wallet": "Hardware Wallet", "gas_can": "Gas Can", "coffee_mug": "Coffee Mug", "rescue_can": "Rescue Can",
    "whistle": "Lifeguard Whistle", "sunscreen": "Sunscreen", "swimsuit": "Red Swimsuit", "flashlight": "Flashlight",
    "sock": "Tube Sock", "pixel_hoodie": "Pixel Hoodie", "studio_headphones": "Studio Headphones",
    "synth_keys": "Synth Keys", "ribbon_cable": "Ribbon Cable", "neon_tube": "Neon Tube", "highlighter": "Highlighter",
    "tennis_ball": "Tennis Ball", "street_sign": "Street Sign", "newspaper": "Newspaper", "microphone": "Microphone",
    "press_badge": "Press Badge", "play_money": "Play Money", "playing_cards": "Playing Cards",
}

# the parenthetical in the evidence inventory; picked per token
NOTES = {
    "cassette": ["side B only", "recorded off the radio, DJ talks over every intro", "labeled MIX 4 U",
                 "rewound with a pencil", "someone's voicemail greeting"],
    "vhs": ["BE KIND REWIND (they did not)", "taped over a wedding", "label says DO NOT TAPE OVER",
            "late fees now exceed GDP of a small nation"],
    "boombox": ["took 10 D batteries", "shoulder-mounted in its prime", "one speaker still believes"],
    "walkman": ["auto-reverse broke in 1991", "belt clip snapped at a bus stop"],
    "headphones": ["orange foam, allegedly", "one ear works if you hold it"],
    "portable_cd": ["anti-skip lied", "45-second buffer, 2-second attention span"],
    "cd": ["burned at 1x, 4 hours", "track 7 skips", "says ROAD TRIP in marker", "coaster now"],
    "jewel_case": ["hinge broken on arrival", "insert is from a different album"],
    "corded_phone": ["cord stretched to the bathroom", "someone is still on hold",
                     "was on the line when mom picked up"],
    "pager": ["last page: 143", "last page: 911 (it was not)", "clipped to jeans for status only"],
    "flip_phone": ["snapped shut dramatically", "ringtone composed by hand", "12 texts left this month"],
    "candybar_phone": ["unbreakable until today", "snake high score intact", "faceplate swapped 4 times"],
    "crt": ["still warm", "degaussed one last time", "screen burn-in reads LOADING",
            "weighs more than the desk"],
    "keyboard_chunk": ["F, J and the crumbs", "the W key is missing, for obvious reasons"],
    "mouse": ["ball removed as a prank", "rollers caked with 1998", "cord chewed by a dog"],
    "floppy": ["DISK 2 of 7", "says DO NOT FORMAT", "contains one (1) virus", "save icon, but real"],
    "webcam": ["pointed at the ceiling forever", "240p of pure confidence"],
    "digital_camera": ["2 megapixels of truth", "memory full, 14 photos"],
    "mp3_player": ["128MB, 30 songs, 29 skipped", "shuffle picked the same song 6 times"],
    "memory_card": ["corrupted during a birthday", "8MB, full"],
    "usb_stick": ["contains homework_FINAL_final2.doc", "never ejected safely"],
    "charger_brick": ["fits nothing else in the house", "warm to the touch, somehow"],
    "controller_16bit": ["cord pulled the console off the shelf", "the B button is sticky"],
    "controller_modern": ["stick drift since day one", "thrown during a boss fight"],
    "joystick": ["fire button pressed 40 million times", "suction cups gave up"],
    "game_cart": ["blown into 400 times", "save file erased by a sibling"],
    "brick_game": ["9999 games, 4 real ones", "HI SCORE 00000"],
    "handheld": ["screen scratched from a pocket with keys", "battery cover lost immediately"],
    "virtual_pet": ["died during math class", "fed 0 times", "reincarnated 40 times"],
    "puzzle_cube": ["solved once, stickers moved", "two stickers peeled"],
    "yoyo": ["walked the dog one time", "string tied to a finger for 3 years"],
    "army_men": ["the one with the radio survived", "melted with a magnifying glass"],
    "sneaker": ["left only", "light-up heel, dead", "untied since 1989", "was in the dryer"],
    "sunglasses": ["mall kiosk special", "one lens popped out"],
    "roller_skate": ["the rink smell is still in there", "toe stop worn to nothing"],
    "slap_bracelet": ["banned by the school", "cut someone, probably"],
    "notebook": ["doodles in the margins", "note says 'check YES or NO'", "spiral unwound halfway"],
    "pencil": ["chewed", "sharpened to a nub", "never saw a scantron it liked"],
    "binder": ["velcro screams when opened", "covered in band names"],
    "lunchbox": ["thermos missing", "the smell stays"],
    "slime": ["stuck in the carpet", "was in the hair of a sibling"],
    "skateboard": ["one ollie, lifetime", "griptape ate a pair of jeans"],
    "skate_wheel": ["flat spot from a power slide", "rolled into a storm drain once"],
    "aa_batteries": ["probably dead", "licked to test", "taken out of the smoke detector",
                     "mixed old and new, like animals"],
    "tv_remote": ["found in the couch", "the volume button worn smooth", "held together with tape"],
    "extension_cord": ["daisy-chained into three more", "overloaded on purpose"],
    "pizza_crust": ["petrified", "from a sleepover", "still better than most portfolios",
                    "found behind the couch"],
    "soda_can": ["flat", "shaken as a prank", "tab kept for charity"],
    "energy_can": ["third one that night", "tastes like a battery", "exam week casualty"],
    "film_canister": ["undeveloped, forever", "holds one quarter"],
    "disposable_camera": ["27 exposures of a thumb", "never developed"],
    "glow_stick": ["cracked at a school dance", "still glowing a little, somehow"],
    "lighter": ["for incense, obviously", "out of fluid"],
    "milk_caps": ["won in a bet", "the slammer is chipped"],
    "calculator": ["spelled BOOBIES upside down", "solar panel covered by a sticker"],
    # contaminants
    "broken_rocket": ["didn't make it", "was going to the moon"],
    "gold_coin": ["real, probably", "bought the top"],
    "red_candle": ["lit", "one of many"],
    "green_candle": ["rarest thing in here", "genuinely unheard of"],
    "paper_hand": ["folded under light pressure", "sold at the bottom"],
    "diamond": ["hands not included", "held through everything"],
    "hardware_wallet": ["seed phrase written on the back of a receipt", "PIN forgotten"],
    "crumpled_chart": ["printed out for emotional reasons", "it went up, then it went down"],
    "bull": ["dead", "trapped", "flipped"],
    "bear": ["thriving", "doing fine actually"],
    "ramen_packet": ["for emergencies", "the whole strategy"],
    "smartphone": ["screen protector did nothing", "1% battery, forever", "cracked in the first week",
                   "last text: read, no reply"],
    "tablet": ["used once as a cutting board", "bought for the kids, taken back by dad", "one thumbprint of juice"],
    "earbuds_case": ["one bud present", "survived the wash", "both buds gone, case still charges nothing"],
    "smartwatch": ["10,000 steps, never", "says STAND, does not", "still counting steps in the dryer"],
    "vr_headset": ["worn twice", "the walls were real and they were hit", "watched one (1) movie"],
    "drone": ["over the neighbor's fence", "flew once, into a tree", "40 seconds of freedom"],
    "fidget_spinner": ["banned by the school", "spins for four seconds, like the trend", "bearing went missing"],
    "selfie_stick": ["banned at the museum", "mid-trip, mid-ocean", "the person holding it is not in the photo"],
    "ring_light": ["the eyes in every mirror selfie", "one bulb out, one ego intact"],
    "vape": ["5000 puffs, 4999 regrets", "mango, mostly", "zero nicotine, allegedly"],
    "face_mask": ["worn below the nose", "from 2020, still fresh", "one of 400 in a coat pocket"],
    "hand_sanitizer": ["was in every pocket in 2020", "60% alcohol, 40% anxiety", "half empty, half crusty"],
    "bluetooth_speaker": ["paired with the wrong phone", "played one song, too loud", "lost, found, lost"],
    "power_bank": ["at 4%, like all of them", "dead when needed", "10000 mAh of dead weight"],
    "magazine": ["read for the articles", "for the interviews, obviously", "the staples are doing the work",
                 "found in a dad's truck"],
    "centerfold": ["folded out, then folded back in a hurry", "staples removed, an attempt was made",
                   "left open to the wrong page"],
    "tissue_box": ["nearly empty", "one for every mood", "there was a reason it lived on the nightstand"],
    "tissues": ["crusty", "a tragic number of them", "found in a coat pocket"],
    "foil_packet": ["from a wallet, 2003", "expired; hope did not", "XL, optimistic"],
    "dice": ["snake eyes, twice", "blown on for luck", "loaded, rumor says"],
    "poker_chip": ["taken from a casino, small heist", "never cashed out", "a stack of ambition"],
    "scratch_ticket": ["not a winner", "$2 for hope", "scratched with a house key"],
    "beer_can": ["crushed on a forehead", "12 of 12", "warm, sadly", "last one in the fridge"],
    "shot_glass": ["souvenir of a night nobody recalls", "from a trip to Vegas", "chipped rim"],
    "matchbook": ["from a gentlemen's club, reportedly", "matches missing, reasons unclear"],
    "cold_wallet": ["the seed phrase is in the other jacket", "backed up on a napkin", "never plugged in, for safety",
                    "frozen, like the price"],
    "hdd": ["WALLET.DAT inside, allegedly", "backed up nothing", "thrown out in a cleanup, instant regret"],
    "gas_can": ["empty, like the wallet", "the receipt says $9.99 a gallon", "used once, for a mower that did not start"],
    "coffee_mug": ["says GM, like all the others", "chipped handle, favorite", "cold since 6 A.M."],
    "rescue_can": ["never once rescued", "used as a pillow at the beach", "a torpedo with no torpedo"],
    "whistle": ["blown exactly once, at a pool", "around the neck of the loudest person alive", "sounds like authority"],
    "sunscreen": ["SPF 100, the burn did not care", "applied to half a back", "mostly in the sand"],
    "swimsuit": ["red, obviously", "drying since the nineties", "built for running in slow motion"],
    "flashlight": ["for reading under the covers", "batteries gone, guilt remains"],
    "sock": ["one of a pair, no pair", "gym sock, past tense", "found under the bed, do not ask"],
    "pixel_hoodie": ["hood up, lights off", "soft from 400 washes", "drawstring long gone"],
    "studio_headphones": ["one cup loud, one cup soft", "mixed at 3 A.M.", "cable replaced four times"],
    "synth_keys": ["stuck on one (1) preset", "C, D and a lot of reverb", "an 808 lives in here"],
    "ribbon_cable": ["rainbow, the good kind", "pin one is the red stripe", "once inside a real computer"],
    "neon_tube": ["buzzing a little", "the only thing in the cube still awake", "the sign said OPEN, for real"],
    "highlighter": ["highlighted the whole page", "dry, but loud", "yellow, everywhere"],
    "tennis_ball": ["found in a dog", "hit over a fence", "deflated, bouncing on hope"],
    "street_sign": ["taken for a dorm wall", "name faded, sign did not", "bent at the corner"],
    "newspaper": ["EXTRA EXTRA", "yesterday's news", "crossword half done, in pen"],
    "microphone": ["is this thing on", "check one, two, recording", "held too close, for years"],
    "press_badge": ["ALL ACCESS, laminated", "lost at the after party", "hanging by a thread"],
    "play_money": ["worth exactly what it says", "no cash value, ever", "won, then lost, at cards"],
    "playing_cards": ["one short of a deck", "the ace of spades, hidden", "a bluff, in four cards"],
}
# a few extra lines on the old favorites, same voice
NOTES["sneaker"] += ["smells like 1989", "worn to one (1) very bad decision"]
NOTES["sunglasses"] += ["worn indoors at 2 A.M."]
NOTES["cassette"] += ["a mix for someone who never listened"]
NOTES["vhs"] += ["the unmarked one, from the back of the closet"]
NOTES["pager"] += ["last page from a number nobody called back"]
NOTES["lighter"] += ["borrowed in 1997, never returned"]

SMELLS = [
    # (value, weight, conditions it prefers)
    ("New Plastic", 10, ("CLEAN",)),
    ("Hot Dust on a CRT", 9, ()),
    ("Basement", 9, ("SOAKED",)),
    ("Arcade Carpet", 8, ()),
    ("Mall Food Court", 8, ()),
    ("Blue Raspberry", 7, ()),
    ("Wet Cardboard", 7, ("SOAKED",)),
    ("Grandma's Couch", 6, ()),
    ("Fresh Batteries (Licked)", 5, ()),
    ("Body Spray Cloud", 5, ()),
    ("Burnt Popcorn", 5, ("BURNT",)),
    ("Melted Crayon", 4, ("BURNT",)),
    ("Gym Bag, Forgotten", 4, ()),
    ("Scratch-n-Sniff Sticker", 3, ()),
    ("Rink Snack Bar", 3, ()),
    ("Science Lab", 2, ("BIOHAZARD",)),
    ("Don't", 1, ("BIOHAZARD",)),
    ("Cheap Cologne", 5, ()),
    ("Cigarette in a Jacket", 4, ()),
    ("Vegas Carpet", 3, ()),
    ("Hot Tub", 3, ("SOAKED",)),
    ("Victory", 1, ("GOLD",)),
]

RECOVERED = [
    ("Under the Bed", 10, ()),
    ("Back of the Closet", 9, ()),
    ("Dad's Junk Drawer", 8, ()),
    ("Mom's Minivan", 7, ()),
    ("Garage Sale Free Bin", 7, ()),
    ("School Lost & Found", 6, ()),
    ("Grandma's Attic", 6, ()),
    ("Storage Unit (Auctioned)", 5, ()),
    ("Behind the Couch", 5, ()),
    ("A Very Specific Ditch", 3, ()),
    ("The Mall Fountain", 2, ("SOAKED",)),
    ("Flooded Basement", 4, ("SOAKED",)),
    ("House Fire (Everyone's Fine)", 5, ("BURNT",)),
    ("Behind the Science Wing", 4, ("BIOHAZARD",)),
    ("Estate of a Collector", 2, ("CLEAN", "GOLD")),
    ("A Buddy's Basement", 6, ()),
    ("Dad's Truck, Glovebox", 6, ()),
    ("The Bachelor Pad", 5, ()),
    ("Vegas Hotel Room", 4, ()),
    ("Ex's Garage", 4, ()),
    ("Behind the Bar", 3, ()),
    ("Nobody Knows", 1, ()),
]

PRESSURE = [  # by crush intensity, the collection gets progressively more fucked up
    (0.66, "Firm Handshake"),
    (0.78, "Hydraulic"),
    (0.9, "Industrial"),
    (1.01, "Unreasonable"),
]

WIRES = [(3, "A Few"), (5, "Several"), (7, "Concerning"), (99, "Fire Hazard")]
TAPE = {0: "None", 1: "Loose Ends", 2: "Loose Ends", 3: "Wrapped", 4: "Wrapped", 5: "Mummified", 6: "Mummified",
        7: "Mummified", 8: "Fully Mixtaped"}

ONE_OF_ONES = {
    "EMPTY": "We kept the important shit. There wasn't any.",
    "UNCRUSHED": "The pile, as it was, the minute before.",
    "SOLID GOLD": "Every single thing in here is gold. Nobody can explain it.",
    "MIXTAPE": "Forty cassettes and every inch of their tape.",
    "LEFTOVERS": "A block of pizza crust. Only pizza crust. One sleepover's worth.",
    "DOUBLE A": "Every AA battery that ever went missing from a remote.",
    "SCREEN TIME": "Every screen you ever stared at, still on.",
    "BULL TRAP": "They all bought the top.",
    "LANDFILL DRIVE": "Every drive that held something that mattered. All of it is in the dump now.",
    "BLOW ON IT": "Forty-four cartridges, all blown on. It never helped. You did it anyway.",
    "STILL ALIVE": "Thirty-eight virtual pets. One is still alive. Nobody has fed it since 1997.",
    "GAS FEES": "A block of gas cans and receipts. You paid it. You'd pay it again.",
    "SAVE ICON": "Sixty-four floppy disks. The save icon, before it became a joke.",
    "COASTERS": "Every burned CD that ended up under a drink.",
    "GM": "Good morning. Good morning. Good morning. Good morning.",
    "COLD STORAGE": "Every hardware wallet, frozen solid. Do not ask where the seed phrases are.",
    "SLOW MOTION": "Everyone you ever watched run toward the water. Nobody arrived. It was gorgeous.",
    "UNDER THE MATTRESS": "It was under the mattress. Everyone's mother knew. Nobody said a word.",
    "LOW RES": "Made in a hoodie and a pair of headphones at three in the morning. Low res and loud.",
    "CCFF00": "One color. All of it CCFF00. None of it subtle.",
    "STOP THE PRESSES": "Extra. Extra. The street has news, and a street sign to prove it.",
}

SIGNOFFS = [
    "We kept the important shit.",
    "No refunds. No returns. No explanation.",
    "Handle with both hands.",
    "Still heavier than it looks.",
    "Do not attempt to uncrush.",
    "Some assembly was removed.",
    "Contents may have settled.",
    "Crushed it.",
    "Nobody made you keep this.",
]


_SAME = ("s", "Ramen", "Men", "Slime", "Money", "Dice")
_IRREGULAR = {"Boom Box": "Boom Boxes", "Keyboard (Partial)": "Keyboards (Partial)", "Smartwatch": "Smartwatches",
              "9999-in-1 Handheld": "9999-in-1 Handhelds", "Laptop Charger": "Laptop Chargers",
              "Ball Mouse": "Ball Mice"}


def plural(name):
    if name in _IRREGULAR:
        return _IRREGULAR[name]
    if name.endswith(("ss", "x", "ch", "sh")):
        return name + "es"
    if name.endswith(_SAME):
        return name
    return name + "s"


def smells_like(smell):
    if smell == "Don't":
        return "Do not smell it."
    if smell == "Nothing":
        return "Smells like nothing."
    keep = ("Grandma's", "CRT", "Vegas")
    words = [w if any(w.startswith(k) for k in keep) else w.lower() for w in smell.split()]
    return "Smells like " + " ".join(words) + "."
