# Hazard lexicon: English / Hindi / Hinglish (DRAFT FOR REVIEW)

> **Status: DRAFT.** Written by Claude. It has **not** been reviewed by a Hindi speaker or a safety practitioner, and **no code
> uses it yet**. Hindi and Hinglish entries are my best attempt; entries marked ⚠ are ones I am less sure of. After your review I
> will convert the approved entries into the configuration file the extraction rules and the Safety Memory Engine read.
> Anything you do not approve is simply not included.

## 1. How to review

Work through the tables and mark the first column:

- `[x]` keep as written
- `[~]` keep with the change you note
- `[-]` remove
- Add missing terms in the Notes column or at the bottom (section 10).

Suggested order: section 8 (demo-critical terms) first, then section 6 (ambiguous terms), then the rest.
Please say if a term is **natural for site workers** (what people actually say), not just correct. Real site speech often mixes
English nouns with Hindi verbs, and spellings of Hinglish vary a lot.

## 2. What the lexicon is for, and what it will never do

It exists to make three things possible without a language model:

1. **Suggest a category** for a draft report (always labelled "suggested by rules", with the matched words shown). The reporter or officer confirms.
2. **Show shared hazard terms** as one explainable signal when the Safety Memory Engine compares two reports, including across scripts (for example "water" / "pani" / "पानी"), which plain text similarity cannot do.
3. **Flag missing information** (for example no location term found).

It will **never**: decide a match on its own, set severity, infer a cause, assign blame, or write report text for anyone.
For that reason blame words ("careless", "लापरवाही", "galti") are deliberately **not** in the lexicon (section 7).

## 3. Matching conventions (please confirm or change)

| # | Convention | Reason |
|---|---|---|
| C1 | **Explicit spelling variants only.** No automatic spelling normalisation (no collapsing "aa" to "a" or doubled letters). | Automatic rules cause collisions. Example: collapsing doubled letters would merge "gaddha" (pit) with "gadha" (donkey). Listing variants is transparent and reviewable. |
| C2 | Latin text is lower-cased; Devanagari is Unicode-normalised (NFC); both compared as whole words. | Predictable matching. |
| C3 | Multi-word entries (phrases) match as phrases. Single words never match inside longer words. | Avoids false hits. |
| C4 | Ambiguous terms (section 6) match **only** under the handling rule you approve. | Prevents false matches. |
| C5 | Digits 0-9, Devanagari digits ०-९ and number words (section 5.12) are treated as numbers **only** in location expressions such as "Basement 2" / "बेसमेंट दो". | "do" and "ek" are everyday words. |
| C6 | A **concept** is a fine-grained tag (for example `electrical_panel`). A **category** (section 4) is a broader hazard group suggested from concepts. | Keeps the vocabulary reviewable. |

## 4. Proposed hazard categories (a working list, NOT an official standard)

Please adjust to match how your site actually groups hazards.

| Category | Suggested by concepts (examples) |
|---|---|
| Electrical | electrical, electrical_panel, electrical_room, cable_wire, exposed_wire, electric_shock, spark, short_circuit, earthing, socket_plug |
| Water & Drainage | water, water_accumulated, wet_surface, leak, flooding, drainage |
| Working at Height & Falls | fall_from_height, work_at_height, open_edge, floor_opening, lift_shaft, safety_harness, ladder |
| Scaffolding & Formwork | scaffold, scaffold_plank, formwork, props |
| Excavation & Structural | excavation, cave_in, crack, falling_object |
| Lifting & Mobile Plant | crane, lifting_gear, lifting_operation, vehicle, machine_guard, cutting_tool |
| Fire, Hot Work & Gas | fire, smoke, welding_hot_work, fire_extinguisher, gas_cylinder, flammable, gas_leak |
| PPE | helmet, no_ppe, gloves, safety_shoes, eye_protection, respiratory, hi_vis |
| Housekeeping, Slips & Trips | debris, tripping_hazard, slippery, rebar, protruding_nail, material_storage, oil_spill |
| Health & Environment | dust, noise, chemical, heat, confined_space, poor_lighting, poor_ventilation |
| Other / not suggested | used when nothing matches; never guessed |

**Co-occurrence question (important for the demo):** a report such as "water near the electrical panel, cable close to the water"
contains both Water and Electrical concepts. Proposed behaviour: suggest **Electrical** as the primary suggestion and list
**Water & Drainage** as an alternative, showing the matched words for each; the officer chooses. Do you agree, or should
the water-near-electrical combination be its own category?

## 5. Concept tables

Columns: Concept ID · English · Hindi (Devanagari) · Hinglish variants (Latin script) · Notes.
Items in the Notes column starting "see 6" refer to the ambiguity table.

### 5.1 Water and liquids

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `water` | water | पानी | pani, paani | demo-critical |
| [ ] | `water_accumulated` | water collected, accumulated water, standing water, stagnant water, waterlogging, puddle | पानी जमा, जमा हुआ पानी, ठहरा हुआ पानी, जलभराव, पानी भरा हुआ, पानी भर गया | pani jama, jama hua pani, pani ruka hua, pani bhara hua, pani bhar gaya, jalbharav, jal bharav | demo-critical; "जमा"/"भरा" alone: see 6 |
| [ ] | `wet_surface` | wet floor, damp | गीला फर्श, गीला, नमी | geela farsh, gila farsh, geela floor, nami | bare "गीला" is weak |
| [ ] | `leak` | leak, leakage, seepage, dripping | रिसाव, लीकेज, सीपेज, पानी टपक रहा है | risav, leakage, leak, seepage, pani tapak raha hai | |
| [ ] | `oil_spill` | oil spill, oil on floor, diesel spill | तेल गिरा, तेल फैला, डीज़ल गिरा | tel gira, oil gira, oil spill, diesel gira | "गिरा" alone: see 6 |
| [ ] | `flooding` | flood, flooded | बाढ़ | badh, flood, flooded | |
| [ ] | `drainage` | drain, drainage, sump | नाली, ड्रेनेज, सम्प | nali, drainage, sump | "नाला" is in 6 |

### 5.2 Electrical

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `electrical` | electrical, electric | इलेक्ट्रिकल, इलेक्ट्रिक, विद्युत | electrical, electrikal, elektrikal, electric | demo-critical |
| [ ] | `electrical_panel` | electrical panel, panel board, distribution board, DB, DB box, MCB, switchboard | इलेक्ट्रिकल पैनल, पैनल बोर्ड, डीबी, एमसीबी, स्विच बोर्ड | electrical panel, panel board, db, db box, mcb, switch board, switchboard | demo-critical; bare "panel"/"board": see 6 |
| [ ] | `electrical_room` | electrical room, panel room, DB room, switch room, transformer room | इलेक्ट्रिकल रूम, पैनल रूम, डीबी रूम, स्विच रूम | electrical room, panel room, db room, switch room | demo-critical |
| [ ] | `cable_wire` | cable, wire, wiring | केबल, तार, वायर, वायरिंग | cable, kebal, wire, wiring, taar | demo-critical; Latin "tar": see 6 |
| [ ] | `exposed_wire` | exposed wire, bare wire, open wire, hanging wire, live wire | खुला तार, नंगा तार, लटकता तार, खुली केबल, लाइव वायर | khula taar, nanga taar, latakta taar, khuli cable, open wire, live wire, hanging wire | |
| [ ] | `electric_shock` | electric shock, electrocution, got a shock | करंट लगा, बिजली का झटका, शॉक लगा | current laga, current lag gaya, bijli ka jhatka, shock laga, shock lag gaya | bare "current": see 6 |
| [ ] | `spark` | spark, sparking | चिंगारी, स्पार्किंग | chingari, spark, sparking | |
| [ ] | `short_circuit` | short circuit | शॉर्ट सर्किट | short circuit, short-circuit | bare "short": see 6 |
| [ ] | `earthing` | earthing, earth wire | अर्थिंग | earthing, arthing | bare "earth"/"ground": see 6 |
| [ ] | `socket_plug` | socket, plug, extension board, extension cord | सॉकेट, प्लग, एक्सटेंशन बोर्ड | socket, plug, extension board, extension cord | |
| [ ] | `generator` | generator, DG set | जनरेटर, डीजी सेट | generator, dg set | |
| [ ] | `transformer` | transformer | ट्रांसफार्मर | transformer | |

### 5.3 Height, edges, openings

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `fall_from_height` | fall from height, fell from above | ऊँचाई से गिरना, ऊपर से गिर गया | uchai se gira, upar se gir gaya, height se gira | "गिरा" alone: see 6 |
| [ ] | `work_at_height` | work at height, working on the roof | ऊँचाई पर काम | uchai par kaam, height par kaam, height work | |
| [ ] | `roof_terrace` | roof, terrace | छत, टेरेस | chhat, chat, terrace, roof | |
| [ ] | `open_edge` | open edge, unprotected edge, no railing, no guardrail | खुला किनारा, बिना रेलिंग, रेलिंग नहीं | khula kinara, bina railing, railing nahi, no railing | |
| [ ] | `floor_opening` | floor opening, shaft opening, uncovered hole, open manhole | खुला छेद, बिना ढक्कन, ढक्कन नहीं, खुला मैनहोल | khula chhed, bina dhakkan, dhakkan nahi, khula manhole, opening khula | |
| [ ] | `lift_shaft` | lift shaft, lift well | लिफ्ट शाफ्ट | lift shaft, lift well | bare "lift": see 6 |
| [ ] | `safety_harness` | harness, safety belt, lifeline | हार्नेस, सेफ्टी बेल्ट, लाइफलाइन | harness, safety belt, lifeline | |
| [ ] | `ladder` | ladder | (सीढ़ी: see 6) | ladder | Hindi word can mean ladder or stairs |
| [ ] | `stairs` | staircase, stairs, stairwell | सीढ़ियाँ, स्टेयरकेस, ज़ीना ⚠ | seedhiyan, staircase, stairwell, zeena | ⚠ "ज़ीना" may be regional |

### 5.4 Scaffolding and formwork

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `scaffold` | scaffold, scaffolding | स्कैफोल्ड, स्कैफोल्डिंग | scaffold, scaffolding, scafolding | |
| [ ] | `scaffold_plank` | plank, platform board, toe board | तख्ता, पटरा ⚠ | takhta, patra ⚠, plank, toe board | ⚠ please tell me what workers actually say |
| [ ] | `formwork` | formwork, shuttering, centering | शटरिंग, सेंटरिंग | shuttering, shatering, centering, formwork | |
| [ ] | `props` | prop, props, staging | प्रॉप | prop, props, staging | bare "support": see 7 |

### 5.5 Excavation and structure

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `excavation` | excavation, trench, pit | खुदाई, खाई, गड्ढा | khudai, khai, gaddha, gadda, trench, pit | "gadha": see 6 |
| [ ] | `cave_in` | cave-in, soil collapse, collapse | मिट्टी धंस गई, धंस गया, ढह गया | mitti dhans gayi, dhans gaya, dhah gaya, collapse, cave in | |
| [ ] | `crack` | crack | दरार | darar, crack | |
| [ ] | `structure_element` | wall, slab, column, beam | दीवार, स्लैब, कॉलम, बीम | deewar, diwar, slab, column, beam | neutral structure words; not hazards by themselves |
| [ ] | `falling_object` | falling object, dropped object | ऊपर से सामान गिरा, गिरता सामान | upar se saman gira, saman gir gaya, falling object | |

### 5.6 Lifting, plant and machinery

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `crane` | crane, tower crane, mobile crane | क्रेन, टावर क्रेन | crane, tower crane, mobile crane | |
| [ ] | `lifting_gear` | sling, hoist, chain block, wire rope, shackle | स्लिंग, हॉइस्ट, चेन ब्लॉक, वायर रोप | sling, hoist, chain block, wire rope, shackle | "रस्सी"/"chain": see 6 |
| [ ] | `lifting_operation` | lifting operation, hoisting | लिफ्टिंग | lifting, hoisting | |
| [ ] | `vehicle` | truck, dumper, JCB, excavator, forklift, trolley | ट्रक, डंपर, जेसीबी, एक्सकेवेटर, फोर्कलिफ्ट, ट्रॉली | truck, dumper, jcb, excavator, forklift, trolley | |
| [ ] | `machine_guard` | missing guard, no guard | गार्ड नहीं, बिना गार्ड | guard nahi, bina guard, no guard, guard missing | |
| [ ] | `cutting_tool` | grinder, cutter, cutting machine | ग्राइंडर, कटर, कटिंग मशीन | grinder, cutter, cutting machine | bare "cut": see 6 |

### 5.7 Fire, hot work and gas

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `fire` | fire | आग | aag, fire | "आग लगी" is a phrase, see 6 |
| [ ] | `smoke` | smoke | धुआँ, धुआं | dhuan, dhuaan, dhua, smoke | |
| [ ] | `welding_hot_work` | welding, hot work, gas cutting | वेल्डिंग, हॉट वर्क, गैस कटिंग | welding, hot work, gas cutting | |
| [ ] | `fire_extinguisher` | fire extinguisher | फायर एक्सटिंग्विशर, अग्निशामक | fire extinguisher, extinguisher | |
| [ ] | `gas_cylinder` | gas cylinder, LPG cylinder, oxygen cylinder | गैस सिलेंडर, सिलेंडर, ऑक्सीजन सिलेंडर | gas cylinder, cylinder, silinder, lpg, oxygen cylinder | bare "गैस": see 6 |
| [ ] | `flammable` | petrol, diesel, thinner, flammable | पेट्रोल, डीज़ल, थिनर, ज्वलनशील | petrol, diesel, thinner, jwalanshil | |
| [ ] | `gas_leak` | gas leak, smell of gas | गैस रिसाव, गैस लीक, गैस की बदबू | gas leak, gas leakage, gas ki badbu | |

### 5.8 PPE

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `helmet` | helmet, hard hat | हेलमेट | helmet | |
| [ ] | `no_ppe` | not wearing, without helmet / harness / gloves | नहीं पहना, बिना हेलमेट, बिना हार्नेस | nahi pehna, nahin pehna, bina helmet, bina harness, bina gloves, without helmet | records a statement; does not assign blame |
| [ ] | `gloves` | gloves | दस्ताने, ग्लव्स | dastane, gloves | |
| [ ] | `safety_shoes` | safety shoes, safety boots | सेफ्टी शूज़, जूते | safety shoes, safety boots, joote | |
| [ ] | `eye_protection` | goggles, safety glasses, face shield | चश्मा, गॉगल्स, फेस शील्ड | goggles, chashma, face shield | |
| [ ] | `respiratory` | mask, respirator | मास्क | mask, respirator | |
| [ ] | `hi_vis` | hi-vis vest, reflective jacket | रिफ्लेक्टिव जैकेट, वेस्ट | hi vis vest, reflective jacket, vest | |

### 5.9 Housekeeping, slips and trips, materials

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `debris` | debris, scrap, rubble | मलबा, कबाड़ | malba, malbaa, kabad, debris, scrap | |
| [ ] | `tripping_hazard` | tripping hazard, obstruction | ठोकर, रुकावट | thokar, rukawat, tripping hazard | bare "trip": see 6 |
| [ ] | `slippery` | slippery, slip | फिसलन, फिसलना, फिसल गया | fisalan, fislan, fisal gaya, slippery | |
| [ ] | `rebar` | rebar, reinforcement bar, TMT bar, protruding bar | सरिया, सरिया निकला हुआ | saria, sariya, rebar, tmt, tmt bar, saria nikla hua | bare "bar": see 6 |
| [ ] | `protruding_nail` | nail, protruding nail | कील, कील निकली हुई | keel, nail, keel nikli hui | |
| [ ] | `material_storage` | material stack, unstable stack | ढेर, स्टैक | dher, stack, material stack | bare "material": see 7 |

### 5.10 Health and environment

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `dust` | dust | धूल | dhool, dhul, dust | |
| [ ] | `noise` | noise | शोर | shor, noise | |
| [ ] | `chemical` | chemical, acid, solvent | केमिकल, तेज़ाब, एसिड | chemical, kemical, acid, tezab | |
| [ ] | `heat` | heat, heat stress | गर्मी, लू | garmi, heat stress | Latin "loo": see 6 |
| [ ] | `confined_space` | confined space, tank entry | कन्फाइंड स्पेस | confined space, tank entry | bare "tank": see 6 |
| [ ] | `poor_lighting` | poor lighting, dark area | अंधेरा, रोशनी कम | andhera, roshni kam, poor lighting, dark | "light nahi": see 6 |
| [ ] | `poor_ventilation` | poor ventilation | वेंटिलेशन नहीं | ventilation nahi, poor ventilation | |

### 5.11 Locations and structures (used for location signals, not hazard categories)

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `basement` | basement | बेसमेंट, तहखाना ⚠ | basement, bsmt | demo-critical; "तहखाना" is formal ⚠; also patterns like "B2" |
| [ ] | `tower` | tower, wing | टावर, विंग | tower, wing | demo-critical; "Block X": see 6 |
| [ ] | `ground_floor` | ground floor | ग्राउंड फ्लोर, भूतल | ground floor, gf | |
| [ ] | `parking_podium` | parking, podium, stilt | पार्किंग, पोडियम, स्टिल्ट | parking, podium, stilt | |
| [ ] | `stairwell_core` | staircase, stairwell | स्टेयरकेस | staircase, stairwell | |
| [ ] | `pump_room` | pump room | पंप रूम | pump room | |
| [ ] | `dg_room` | DG room, generator room | डीजी रूम, जनरेटर रूम | dg room, generator room | |
| [ ] | `store_room` | store, store room | स्टोर, स्टोर रूम | store, store room | |
| [ ] | `gate_boundary` | gate, boundary wall | गेट, बाउंड्री | gate, boundary, boundary wall | |
| [ ] | `shaft_duct` | shaft, duct | शाफ्ट, डक्ट | shaft, duct | |
| [ ] | `floor_level` | floor, level, storey (**only** with a number: see 5.12 and 6) | फ्लोर, लेवल, मंज़िल | floor, level, manzil | demo-critical; "floor" is also the walking surface: see 6 |

### 5.12 Numbers in location expressions ("Basement 2", "बेसमेंट दो", "Level 4")

Applies only directly after a location word (convention C5). Digits (2) and Devanagari digits (२) also count.

| ✓ | Value | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | 1 | one | एक | ek | "ek" is also the article "a": see 6 |
| [ ] | 2 | two | दो | do | "do" is also an English word and a Hindi verb form: see 6 |
| [ ] | 3 | three | तीन | teen | |
| [ ] | 4 | four | चार | char | |
| [ ] | 5 | five | पाँच, पांच | paanch, panch | |
| [ ] | 6 | six | छह, छः | chhe, chhah, che | ⚠ spelling varies |
| [ ] | 7 | seven | सात | saat, sat | |
| [ ] | 8 | eight | आठ | aath, ath | |
| [ ] | 9 | nine | नौ | nau, nao | |
| [ ] | 10 | ten | दस | das | |

Ordinals ("second basement", "दूसरा तल") are not included yet. Tell me if workers use them for levels and I will add them.

### 5.13 Escalation words (may raise a "review urgently" flag; NEVER set severity)

| ✓ | Concept | English | Hindi | Hinglish variants | Notes |
|---|---|---|---|---|---|
| [ ] | `injury` | injured, injury, hurt | चोट, घायल | chot, ghayal, injured, injury | "चोट लगी" is a phrase, see 6 |
| [ ] | `bleeding` | bleeding | खून | khoon, bleeding | |
| [ ] | `unconscious` | unconscious | बेहोश | behosh, unconscious | |
| [ ] | `trapped` | trapped, stuck under | फँसा, दबा हुआ | phansa, dabba hua ⚠, trapped | ⚠ spelling and wording |
| [ ] | `fracture` | fracture, broken bone | फ्रैक्चर, हड्डी टूटी | fracture, haddi tooti | |
| [ ] | `fatality` | fatal, died | मृत्यु, मौत | mrityu, maut, fatal, died | very sensitive: do you want this word included at all? |

## 6. Ambiguous terms (kept separate on purpose)

These are everyday words with several meanings. Handling options:

- **EXCLUDE** never match.
- **CONTEXT** match only when one of the listed words appears in the same sentence.
- **PHRASE** match only inside the listed phrases.
- **WEAK** counts as a faint hint shown to the officer, never enough alone.

| ✓ | Term | Meanings | Risk | Proposed handling | Your decision |
|---|---|---|---|---|---|
| [ ] | current / करंट | electric current; "current" meaning present; water current | false electrical hit | CONTEXT: an electrical concept or shock verb (laga, lagna, shock) | |
| [ ] | short | short circuit; short in length; "short of" | false electrical hit | PHRASE: "short circuit" / "शॉर्ट सर्किट" only | |
| [ ] | बिजली / bijli | electricity; lightning; power supply ("bijli gayi" = power cut) | an outage is not an electrical hazard | WEAK; PHRASE for outage ("bijli gayi", "bijli gul", "power cut") so it is not read as a hazard | |
| [ ] | tar (Latin) | colloquial for wire; tar / bitumen | wrong concept | EXCLUDE Latin "tar"; accept "taar" and Devanagari "तार" | |
| [ ] | panel / पैनल | electrical panel; shuttering panel; precast panel; solar panel | **demo-critical** false electrical hit | CONTEXT: electrical, DB, MCB, "panel room", "panel board" | |
| [ ] | board / बोर्ड | switchboard; formwork board; signboard | false electrical hit | PHRASE: "switch board", "db board", "panel board" only | |
| [ ] | floor | walking surface ("floor par pani") vs storey ("3rd floor") | **demo-critical**: wrong location level | CONTEXT: with a number or ordinal = storey; after "on / par / pe / पर" = surface; else unresolved | |
| [ ] | do / दो | the number 2; English verb "do"; Hindi "give" ("de do") | invented floor numbers | CONTEXT: number only directly after a location word (C5) | |
| [ ] | ek / एक | the number 1; the article "a" ("ek cable pani ke paas pada hai") | **demo-critical** invented floor number | CONTEXT: number only directly after a location word; otherwise ignore | |
| [ ] | char / चार | the number 4 | rare clash with "charred" | CONTEXT as for "do" | |
| [ ] | teen / तीन | the number 3; "teen" (teenager) | rare | CONTEXT as for "do" | |
| [ ] | fall / gir / गिरा / गिर | person falling; object falling; water spilled ("pani gira"); structure collapsing | wrong hazard | WEAK; map to `fall_from_height` only with a height term (roof, edge, scaffold, ladder, ऊँचाई) | |
| [ ] | जमा / jama | collected (water); deposited (money); set / frozen | **demo-critical** | CONTEXT: a water or liquid term | |
| [ ] | भरा / bhara | filled; full ("godown bhara hai") | **demo-critical** | CONTEXT: a water term | |
| [ ] | खुला / khula | open; generic ("gate khula") | too generic | CONTEXT: wire, cable, edge, hole, shaft, manhole, dhakkan | |
| [ ] | टूटा / toota | broken; generic | too generic | WEAK; only as a modifier of equipment or structure terms | |
| [ ] | लगा / लगी / laga / lagi | attached; struck; caught; started ("chot lagi" injury, "current laga" shock, "aag lagi" fire, "kaam laga hai" work is on) | many unrelated verbs | PHRASE: only the listed phrases | |
| [ ] | सीढ़ी / seedhi | ladder or stairs | wrong concept | WEAK `ladder_or_stairs`, left unresolved for the officer | |
| [ ] | lift | elevator; to lift something ("lift karna") | wrong concept | PHRASE: "lift shaft", "lift well" strong; bare "lift" WEAK | |
| [ ] | load | suspended load; electrical load; to load a truck | wrong concept | CONTEXT: crane, hoist, sling, "overload" | |
| [ ] | ground / earth | ground floor; soil; earthing | wrong concept | PHRASE: "ground floor", "earthing"; EXCLUDE bare | |
| [ ] | slab | concrete slab; paving slab | none (neutral) | treat only as a structure word (5.5), never a hazard | |
| [ ] | cut | cut injury; cutting tool; power cut | wrong concept | EXCLUDE bare; PHRASE: "power cut" = outage | |
| [ ] | jal / jala (Latin) | "jal" = water (formal); "jala" = burnt | **spelling collision** | EXCLUDE both in Latin script; Devanagari जल and जला are distinct and handled separately | |
| [ ] | gas / गैस | LPG; cutting gas; leak; stomach gas | wrong concept | CONTEXT: cylinder, leak, smell, cutting | |
| [ ] | gadha / गधा | "gadha" = donkey; "gaddha" = pit (spelling often merges) | **spelling collision** | CONTEXT for Latin "gadha": excavation or water or "khula" words nearby; accept "gaddha", "gadda" always | |
| [ ] | bar | rebar; crowbar; other | wrong concept | EXCLUDE bare; use saria, rebar, TMT | |
| [ ] | chain | lifting chain; generic | wrong concept | CONTEXT: crane, hoist, sling, "chain block" | |
| [ ] | light / लाइट | lighting; electricity ("light gayi" = power cut); weight | wrong concept | WEAK; "light nahi hai" stays unresolved (poor lighting or outage) | |
| [ ] | trip | circuit tripped (MCB); tripping hazard | wrong concept | CONTEXT: with MCB / DB / panel = electrical event; with thokar / floor / obstruction / "tripped over" = trip hazard | |
| [ ] | pole | electric pole; scaffold pole; flagpole | wrong concept | CONTEXT | |
| [ ] | tank / टैंक | water tank; septic or chemical tank | wrong concept | WEAK; `confined_space` only with "inside / entry / ghusna" | |
| [ ] | motor / मोटर | electric motor; dewatering pump | wrong concept | WEAK | |
| [ ] | block / ब्लॉक | "Block C" (building); concrete block; the verb "block" | wrong location | CONTEXT: followed by a letter or number = location | |
| [ ] | db / डीबी | distribution board; decibel (noise level, e.g. "90 db") | wrong concept on noise reports | CONTEXT: electrical terms, "db box", "db room", "panel" = distribution board; a number before it = decibel (not electrical) | |
| [ ] | slip | slipping on a surface; "slip form" (a formwork technique); a paper slip | wrong concept | CONTEXT: `slippery` only with floor, wet, oil, fisalan words; "slip form" PHRASE = formwork | |
| [ ] | नाला / nala | large drain; stream | too generic | WEAK | |
| [ ] | रस्सी / rassi | rope (any) | not necessarily lifting | WEAK | |
| [ ] | कटिया / katia ⚠ | colloquial illegal power tap; a hook | ⚠ regional, sensitive | CONTEXT: with तार / बिजली; or exclude if you prefer | |
| [ ] | लू / loo | heat wave; (Latin "loo") toilet | wrong concept | CONTEXT for Latin: with garmi / heat | |

## 7. Not included on purpose

- Names of people, contractors, companies and equipment IDs. The system never invents these, and it copies them only as typed.
- **Blame words** ("careless", "negligent", "लापरवाही", "galti", "ghalat"). Matching them would nudge the tool toward blaming a person.
- Generic words with no hazard meaning on their own: "support", "material", "work", "area".
- Medical terms beyond the escalation words in 5.13.

## 8. Demo-critical subset (review these first)

The recurrence demo uses a report about **water near an electrical panel room, with a cable close to the water, in a basement of a tower**.
Review first: `water`, `water_accumulated`, `electrical`, `electrical_panel`, `electrical_room`, `cable_wire`, `basement`, `tower`,
`floor_level`; section 5.12 numbers; and the section 6 rows marked **demo-critical** (panel, floor, ek, do, jama, bhara).

## 9. What happens after your review

1. I convert the approved entries into a versioned configuration file (`backend/app/extraction/lexicon.yaml`) and record the review date and
   reviewer in it, so every suggestion can name the lexicon version it used.
2. The extraction rules and the Safety Memory Engine read only that file.
3. Tests lock in the behaviours above: ambiguous terms do not fire alone, "Ek cable pani ke paas pada hai" does not produce a floor
   number, and Hindi words are never split mid-word.
4. The lexicon will be extended from the **labelled synthetic reports**, not guessed.

## 10. Your additions

Add terms here (any language), with what you want them to mean:

| Term | Language / script | Meaning / concept | Notes |
|---|---|---|---|
| | | | |
