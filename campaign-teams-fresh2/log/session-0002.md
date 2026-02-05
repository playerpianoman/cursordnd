# session-0002

## Run meta
- started_at: 2026-02-04 19:59:11
- eval_rubric: docs/eval-rubric.md
- chat_model: google/gemini-2.5-flash-lite
- chat_provider: openrouter
- player: llm
- reset: True
- seed_override: None
- utility_model: google/gemini-2.5-flash-lite
- utility_provider: openrouter

## Round 1 (2026-02-04 19:59:25)

### DM lead
> You stand at the edge of a foul-smelling, partially flooded chamber in The Old Drain. The water is a murky brown, and rusted metal grates are visible beneath the surface. Ahead, the passage narrows, and you can hear the chittering sounds of your four goblin<ctrl60>ustos. They have not yet spotted you, but their position is blocking the way forward.

### Group choice
- We prepare for a direct assault. No sense in letting them raise the alarm.

### Party actions
- Hero: Hero will charge directly at the nearest goblin, aiming to engage it in melee combat and disrupt their formation.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 3] highest=3 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"harm_add": ["Hero is wounded."], "stress_delta": 1}, "hostiles": {"count_delta": -1}, "facts_add": ["Hero engaged the nearest goblin in melee combat."]}
  - narration:
  > Your charge is swift, and you manage to engage the nearest goblin, but your momentum carries you past it, leaving you exposed. You take a nasty gash for your trouble, and the goblin alarm clock ticks forward as you press on.
- Fighter: Fighter will advance behind Hero, using their shield to protect themselves and any allies who might be caught in the crossfire.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 4] highest=4 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": 0}, "facts_add": ["Fighter advances behind Hero, shield raised for protection."]}
  - narration:
  > I ducked behind the Fighter's massive shield, feeling the solid thud of their advance against the stone floor. A glancing blow skittered off the metal, but it was enough to make me flinch, the force vibrating up my arm. At least I wasn't directly in the path of whatever that was.
- Rogue: Rogue will attempt to flank the goblins, using the chaos of the direct assault to get into a position to strike at a vulnerable target.
  - classify: {"needs_roll": true, "stat": "finesse", "dice_pool": 2, "approach": "Sneaky"}
  - roll: [3, 1] highest=3 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 1, "supply_delta": -1, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": -1}, "facts_add": ["Rogue's flanking maneuver is spotted.", "Rogue finds a weak point and strikes."]}
  - narration:
  > I darted through the melee, the clang of steel a deafening roar in my ears. My boots barely whispered on the stone as I weaved between bodies, aiming for that sweet spot behind the nearest greenskin. I swear I almost had it, but a stray shield bash sent me stumbling, my blade only grazing its arm before I recovered my balance.
- Mage: Mage will prepare a spell to unleash on the goblins as soon as a good opportunity presents itself, aiming for a group effect.
  - classify: {"needs_roll": true, "stat": "wits", "dice_pool": 2, "approach": "Clever"}
  - roll: [1, 4] highest=4 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": 0}, "hostiles": {}, "facts_add": ["Mage is preparing a spell to unleash on the goblins."]}
  - narration:
  > I started gathering arcane energy, picturing a wave of frost to knock those goblins back. My fingers tingled, but the magic felt… slippery. It didn't quite coalesce into the powerful blast I'd envisioned, just a weak puff of cold air that barely ruffled their fur.

### Round summary (state)
STATE | Goblin alarm: 4/4 | Rats swarm: 0/4 | Torch dwindles: 0/6 | Stress 1/3 | Supply 3/3 | Harm: Hero is wounded. | goblins: 6 | Fighter stress 0/3 | Rogue stress 1/3 | Mage stress 0/3 | Location: The Old Drain | Rogue's clever flanking maneuver is spotted by a goblin, but the rogue finds a weak point and strikes it! It's a good thing the party is prepared to deal with the goblins.

