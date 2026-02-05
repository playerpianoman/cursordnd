# session-0001

## Run meta
- started_at: 2026-02-04 20:05:05
- eval_rubric: docs/eval-rubric.md
- chat_model: google/gemini-2.5-flash-lite
- chat_provider: openrouter
- player: llm
- reset: True
- seed_override: None
- utility_model: google/gemini-2.5-flash-lite
- utility_provider: openrouter

## Round 1 (2026-02-04 20:05:19)

### DM lead
> You stand at a junction in the Old Drain. The air is thick with the smell of stagnant water and decay. Ahead, the tunnel opens into a larger chamber where the flickering torchlight reveals four hunched figures—goblins! They haven't spotted you yet, their attention focused on rummaging through a pile of refuse.

### Group choice
- We use the shadows to sneak up on them and take them down before they can raise the alarm.

### Party actions
- Hero: Hero will attempt to move stealthily towards the goblins to get into a flanking position.
  - classify: {"category": "combat", "combat_effect": {"kills_on_hit": 1, "kills_on_crit": 2}, "needs_roll": true, "stat": "finesse", "dice_pool": 1, "approach": "Sneaky"}
  - roll: [1] highest=1 outcome=crit_fail
  - delta: {"clocks": [{"name": "Goblin alarm", "delta": 1}], "pc": {"stress_delta": 1, "supply_delta": -1, "harm_add": [], "harm_remove": []}, "hostiles": {}, "facts_add": ["Hero stumbled and made noise, alerting the goblins."]}
  - narration:
  > Your attempt at stealth was a complete disaster, as you stumbled and crashed through some loose debris. The goblins immediately heard the commotion and are now fully aware of your presence, their alarm bells clanging furiously. Worse still, you've lost a bit of your grip on your supplies, scattering some of them into the dark, damp muck.
- Fighter: Fighter will creep forward, ready to engage the nearest goblin to prevent it from alerting the others.
  - classify: {"category": "combat", "combat_effect": {"kills_on_hit": 1, "kills_on_crit": 2}, "needs_roll": true, "stat": "might", "dice_pool": 2, "approach": "Sneaky"}
  - roll: [3, 1] highest=3 outcome=mixed
  - delta: {"clocks": [], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {}, "facts_add": ["Fighter moved to engage the nearest goblin."]}
  - narration:
  > I crept forward, my shield held high, feeling the grit of the dungeon floor beneath my boots. My heart pounded as I reached for the nearest goblin, but my grip slipped on its slimy hide. It twisted away, letting out a yelp, and I felt a surge of frustration as I only managed to graze its arm.
- Rogue: Rogue will attempt to silently close the distance and eliminate the most dangerous-looking goblin with a swift strike.
  - classify: {"category": "combat", "combat_effect": {"kills_on_hit": 1, "kills_on_crit": 2}, "needs_roll": true, "stat": "finesse", "dice_pool": 2, "approach": "Sneaky"}
  - roll: [4, 3] highest=4 outcome=mixed
  - delta: {"clocks": [], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {}, "facts_add": ["Rogue's stealth is compromised, but they managed to take down one goblin before anyone else reacted.", "The remaining goblins are now fully aware of the party's presence and preparing to fight."]}
  - narration:
  > I crept forward, the shadows a welcome cloak, and lunged. My dagger found its mark, a shallow wound on the brute, but my foot slipped on a loose stone. It wasn't the clean kill I'd hoped for, just a sting.
- Mage: Mage will ready a spell, waiting to cast it on an unsuspecting goblin once the ambush begins.
  - classify: {"category": "combat", "combat_effect": {"kills_on_hit": 1, "kills_on_crit": 2}, "needs_roll": true, "stat": "wits", "dice_pool": 2, "approach": "Sneaky"}
  - roll: [1, 1] highest=1 outcome=crit_fail
  - delta: {"clocks": [], "pc": {"stress_delta": 0, "supply_delta": 0, "harm_add": [], "harm_remove": []}, "hostiles": {}, "facts_add": ["Mage readied a spell, intending to cast it when the ambush began.", "Due to a critical failure, the Mage's spell fizzled harmlessly."]}
  - narration:
  > I tried to gather the arcane energies, to weave a powerful spell for when the moment was right. But my focus slipped, the magic fizzled, and I felt a sickening lurch as the power I'd summoned turned inward. It was a complete disaster.

### Round summary (state)
STATE | Goblin alarm: 1/4 | Rats swarm: 0/4 | Torch dwindles: 0/6 | Stress 1/3 | Supply 2/3 | Harm: none | goblins: 4 | Fighter stress 0/3 | Rogue stress 0/3 | Mage stress 0/3 | Location: The Old Drain | The Mage's spell fizzled, leaving the party exactly where they were before the attempt, with the goblins still alerted and preparing to fight.

