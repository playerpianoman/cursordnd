# session-0001

## Run meta
- started_at: 2026-02-04 20:01:26
- eval_rubric: docs/eval-rubric.md
- chat_model: google/gemini-2.5-flash-lite
- chat_provider: openrouter
- player: llm
- reset: True
- seed_override: None
- utility_model: google/gemini-2.5-flash-lite
- utility_provider: openrouter

## Round 1 (2026-02-04 20:01:38)

### DM lead
> The air in The Old Drain hangs thick with the smell of stagnant water and something fouler. Ahead, the narrow passage opens into a larger chamber, dimly lit by flickering torchlight. Four hulking goblins, their crude weapons glinting, stand guard near a crude barricade. They haven't noticed you yet.

### Group choice
- We hit them hard and fast before they can raise the alarm.

### Party actions
- Hero: Hero will charge directly at the nearest goblin to initiate the assault.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 3] highest=3 outcome=mixed
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 0, "supply_delta": -1, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": 0}, "facts_add": ["Hero charged the nearest goblin."]}
  - narration:
  > Your charge is met with a mixed reception, as you successfully close the distance but the goblin lets out a yelp, alerting its companions. You’ve managed to get a supply point, but the alarm is now inching closer to being raised. The rest of the group is pressing their attack on the other goblins.
- Fighter: Fighter will follow Hero into the fray, engaging another goblin to draw their attention.
  - classify: {"needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 4] highest=4 outcome=mixed
  - delta: {"clocks": [], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": -1}, "facts_add": ["Fighter engaged a goblin to draw its attention."]}
  - narration:
  > I charged in, shield raised, aiming for that snarling goblin. It dodged my clumsy lunge, scraping my arm, but I managed to put myself between it and the Hero.
- Rogue: Rogue will attempt to flank the closest engaged goblin, aiming for a quick takedown.
  - classify: {"needs_roll": true, "stat": "finesse", "dice_pool": 2, "approach": "Sneaky"}
  - roll: [3, 1] highest=3 outcome=mixed
  - delta: {"clocks": [], "pc": {"stress_delta": 0, "supply_delta": 0}, "hostiles": {"count_delta": -1}, "facts_add": ["Rogue attempted to flank an engaged goblin.", "Goblin alarm is ticking.", "One goblin eliminated."]}
  - narration:
  > I darted around the goblin's side, my dagger glinting, but its clumsy swing caught my arm just as I lunged.  A sting, but I managed to nick its leg.
- Mage: Mage will prepare a ranged spell to target an enemy goblin once the surprise attack begins.
  - classify: {"needs_roll": true, "stat": "spirit", "dice_pool": 2, "approach": "Direct"}
  - roll: [1, 4] highest=4 outcome=mixed
  - delta: {"clocks": [], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {"count_delta": -1}, "facts_add": ["Mage prepares a ranged spell."]}
  - narration:
  > I focused my will, drawing arcane energy into my hands, ready to unleash a searing bolt. The moment the surprise attack began, I launched forward, but the surge of power felt…unstable. It sputtered, a mere spark instead of the inferno I intended, only managing to singe the goblin's ear before dissipating.

### Round summary (state)
STATE | Goblin alarm: 1/4 | Rats swarm: 0/4 | Torch dwindles: 0/6 | Stress 0/3 | Supply 2/3 | Harm: none | goblins: 1 | Fighter stress 0/3 | Rogue stress 0/3 | Mage stress 0/3 | Location: The Old Drain | Hero charges the nearest goblin. Fighter engages a goblin. Rogue attempts to flank an engaged goblin. Mage prepares a ranged spell.

