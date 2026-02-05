# session-0006

## Run meta
- started_at: 2026-02-04 19:37:07
- eval_rubric: docs/eval-rubric.md
- chat_model: google/gemini-2.5-flash-lite
- chat_provider: openrouter
- player: llm
- reset: True
- seed_override: None
- utility_model: google/gemini-2.5-flash-lite
- utility_provider: openrouter

## Round 1 (2026-02-04 19:37:26)

### DM lead
> You stand in the damp, echoing confines of the Old Drain, the stench of mildew and stagnant water thick in the air. A moment ago, the Mage unleashed a blast of arcane energy, staggering one of the four goblins ahead. The creature stumbles, momentarily vulnerable amidst its kin.

### Group choice
- The party launches a coordinated assault to overwhelm the staggered goblin.

### Party actions
- Hero: Hero will charge the staggered goblin and strike with all their might.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 3] highest=3 outcome=miss
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 1, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": 0}, "facts_add": ["Hero overextends when charging the staggered goblin."]}
  - narration:
  > Blast! I lunged forward, aiming to put this miserable creature down for good, but my foot skidded on the damp stone. My sword whipped through the air, yet the goblin, for all its staggered state, managed to roll just out of reach. Utterly frustrating.
- Fighter: Fighter will move to engage another goblin, creating a barrier with their shield.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 4] highest=4 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": -1}, "facts_add": ["Fighter moves to engage another goblin, creating a barrier with their shield.", "Fighter draws enemy attention."]}
  - narration:
  > Alright, I charged in, shield up, aiming to draw that little green menace away from the others. Got a good stance, felt solid, but the little bugger just weaved under my swing. Managed to keep him from getting at the mages though, so not a total loss.
- Hero: Hero will charge the staggered goblin and strike with all their might.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [3, 1] highest=3 outcome=miss
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 1, "supply_delta": -1, "harm_add": ["Overextends and leaves them open"]}, "hostiles": {"count_delta": -1}, "facts_add": ["Hero misses their strike against the staggered goblin."]}
  - narration:
  > I lunged forward, adrenaline coursing through me, but my feet slipped on the slick stone. My blade swung wide, a desperate arc that missed its mark entirely. A wave of frustration washed over me as the goblin skittered away.
- Rogue: Rogue will attempt to flank the goblins from the side and strike a vulnerable point.
  - classify: {"needs_roll": true, "stat": "finesse", "dice_pool": 2, "approach": "Sneaky"}
  - roll: [1, 4] highest=4 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": 0}, "facts_add": ["Rogue attempts to flank the goblins.", "Rogue strikes a vulnerable point."]}
  - narration:
  > I tried to get around the side of those grimy little goblins, looking for a gap in their defense. Managed to get a decent stab in, but it wasn't as clean as I'd hoped. They're still standing, the little pests.
- Hero: Hero will charge the staggered goblin and strike with all their might.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [5, 5] highest=5 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": ["Overextends and leaves them open"], "harm_remove": []}, "hostiles": {}, "facts_add": ["Hero overextends when charging the staggered goblin."]}
  - narration:
  > Right, my turn! I charged the goblin, putting everything I had into that swing. It felt pretty good, but I guess it wasn't quite enough to really put him down.
- Mage: Mage will ready a spell to unleash on the next goblin that advances on the party.
  - classify: {"needs_roll": false, "stat": "wits", "dice_pool": 2, "approach": "Clever"}
  - roll: (no roll)
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 1, "supply_delta": 0, "harm_add": [], "harm_remove": ["Overextends and leaves them open"]}, "hostiles": {"count_delta": 0}, "facts_add": ["Mage readies a spell to unleash on the next goblin that advances on the party."]}
  - narration:
  > I focused my will, weaving arcane energies, ready to unleash them. The air crackled with anticipation as I waited for the goblin to step closer, my muscles tensed for the release. It felt like holding back a storm, the power thrumming just beneath my skin.
- Hero: Hero will charge the staggered goblin and strike with all their might.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [3, 3] highest=3 outcome=miss
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": ["Overextends and leaves them open"], "harm_remove": []}, "hostiles": {"count_delta": 0}, "facts_add": ["Hero charges the staggered goblin and misses their strike."]}
  - narration:
  > I lunged forward, adrenaline coursing through me, ready to deliver a finishing blow. But my foot slipped on some loose rubble, and my sword just whizzed past the goblin's ear. Damn it. All that energy wasted.

### Round summary (state)
STATE | Goblin alarm: 4/4 | Rats swarm: 0/4 | Torch dwindles: 0/6 | Stress 2/3 | Supply 2/3 | Harm: Overextends and leaves them open | goblins: 2 | Fighter stress 0/3 | Rogue stress 0/3 | Mage stress 1/3 | Location: The Old Drain | The Warrior stands firm, shield held high, their armor dented but unbroken. They managed to hold their ground against the goblin's onslaught, buying the party precious moments. The Rogue, true to form, darts through the chaos, attempting to outmaneuver the remaining goblin. The Mage, eyes burning with arcane power, begins to chant, a powerful spell taking shape in their hands. The Hero, recovering from their missed attack, readies themselves for another attempt, determined to end this encounter swiftly.

