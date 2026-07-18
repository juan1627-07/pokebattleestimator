# POKÉMON BATTLE SYSTEM MODIFICATION SPECIFICATION

## CRITICAL EXECUTION RULES
1. ONLY modify the requested code blocks, modules, and components specified below.
2. DO NOT alter, rewrite, or delete any fully working core mechanics (turn logic, connection states, sprite loaders) unless explicitly instructed.
3. Ensure all visual and layout modifications are responsive, completely conflict-free, and dynamically adapt to both Desktop and Mobile views without text overlapping.

---

## 1. BATTLE LOGS & TOP HUD ALIGNMENT (Random 6v6 & PVP Modes)
- **Context Analysis:** Analyze the `image.txt` layout in the static folder. The 1v1 mode's battle attack log alignment is the ground truth target layout. In 6v6 and PVP modes, the top Party HUD (6 Pokeballs) causes structural shifting, creating overlapping issues in the bottom right layout.
- **Modification Task:**
  - Adjust the top HUD container housing the 6 Pokeball/Sprite icons. Scale down, reposition, or apply CSS Flexbox/Grid constraints to this top bar so it occupies a fixed, non-disruptive footprint.
  - Apply the exact bottom-right alignment properties used in the 1v1 mode battle log system to the Random 6v6 and PVP modes.
  - Ensure that the 6-Pokémon indicator UI (HUD sub-component) scales down fluidly: illuminated icons/sprites represent available Pokémon, and greyed-out icons represent fainted Pokémon. Prevent any wrapping or overlapping on screens down to 360px wide.

## 2. MAIN BATTLE INTERACTION INTERFACE
- **Modification Task:** Locate the structural zone next to the baseline prompt container `> What will [pokemon_name] do?`. Remodify the layout to place 3 primary interactive controls side-by-side or grouped clean across mobile/desktop:
  1. **SWITCH Button:** Triggers a modal popup displaying the user's 6 party Pokémon with their current status, preserving your legacy switch selection logic.
  2. **ITEMS Button:** Triggers a toggleable popup interface displaying all categorized inventory items (Potions, PP Antidotes, etc.). *Note: Wire up the UI structure and list rendering only; execution mechanics will be hooked up later.*
  3. **GIVE UP Button:** Triggers a 10-second countdown routine overlay. Display a ticking countdown with a visible "Cancel" mechanism. If the countdown reaches 0 without a cancel intervention, terminate the match execution loop and fire the respective Win/Loss resolution events.

## 3. WEATHER & FIELD HAZARD MANAGEMENT
- **Modification Task:** Locate the Hazard/Weather tick logic inside the state machine.
  - Implement a persistent tick-counter (`duration = 5`) for active environmental conditions (e.g., Stream, Snow, etc.). 
  - Decrement this counter at the conclusion of each turn loop. At 0, purge the hazard effect from the field state.
  - Ensure the field hazard accurately applies its modifier payload (damage, speed halves, type changes) to the active Pokémon on the field during the active turns.

## 4. DYNAMIC 2030 BATTLEFIELD GENERATION
- **Modification Task:** Implement a procedurally generated background system that dynamically changes the battlefield environment at the initialization of each match.
  - **Procedural Assets:** Build a pool of modern 2030 visual field themes (e.g., Cyber Arena, Neo-Forest, Volcanic Fissure, Fractured Glacier, Desert Wasteland). 
  - **Random Selection Layer:** On battle initialization, run a randomizer function to pick a field theme layout from the asset pool. The chosen environment assets must render smoothly beneath all active UI elements and sprite layering without causing displacement.
  - **Environmental Aesthetics:** Ensure each randomly selected field style applies corresponding lighting shifts and particle overlays (e.g., floating digital embers for volcanic fields, neon grid pulses for the cyber arena) to match the 2030 vertical UI look.

## 5. BATTLE LOGIC ENGINE BUG FIXES
- **Task A: Struggle & Switch Softlock Resolution**
  - Fix the state lock where a Pokémon forced to use "Struggle" (out of PP across all primary moves) completely disables the "SWITCH" action option. 
  - Fix the bug where switching to an ally inadvertently flags the incoming Pokémon's moves as disabled. Ensure switching clear-states any move-disable flags unless explicitly caused by a lingering field hazard or status condition (like Choice items or Torment).
- **Task B: Boss/Special Type Move Pools**
  - Inspect the Move Allocation assignment arrays for Legendary and Dynamax entities. 
  - Fix the fallback condition that defaults their move layout exclusively to "Struggle". Ensure their proper, specified boss move data arrays map correctly upon instantiating the battle phase.
- **Task C: Type Effectiveness Evaluation**
  - Debug the Weakness/Strength badge calculation function. Fix the element logic evaluating Type 1 and Type 2 multi-target arrays so it visually renders the correct multiplier badge asset (e.g., Super Effective, Resistant) matching standard chart logic.

## 6. PVP MATCHMAKING SELECTION PHASE
- **Modification Task:** Open the PVP setup loop and synchronization layer.
  - While waiting for the remote peer connection to finalize their roster data, display a blinking string indicator: `"Opponent is choosing....."`.
  - Append a visual indicator tag or label marked `"OK"` directly alongside or inside the opponent's team status view/search bar as soon as the opponent submits or locks in their selection array.

## 7. DAMAGE FORMULA VARIANCE ENTROPY
- **Modification Task:** Locate the damage calculation function inside the core battle logic.
  - Remove highly deterministic or static damage results by integrating a standard random damage variance multiplier variable.
  - Apply a random float generator factor scaled between `0.85` and `1.00` to the total calculated output of every standard attack transaction block:
    $$\text{Final Damage} = \text{Calculated Damage} \times \text{Random}(0.85, 1.00)$$