# Clothing Equipment Override Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Move all clothing contrib behavior currently inherited from `evennia.contrib.game_systems.clothing.clothing.py` into the local `typeclasses/characters.py`, backed by the local `typeclasses/equipment.py` equipment model.

**Architecture:** Treat `Equipment` as the only wearable/equippable item typeclass. Replace contrib clothing inheritance/imports with local helper functions, local player commands, and local character hooks that read/write `db.equipment`, `db.inventory`, `db.worn`, `db.covered_by`, `db.wear_style`, and `db.clothing_type` compatibility fields. Keep behavior compatible with current equipment slots and combat stat calculation.

**Tech Stack:** Evennia typeclasses, command cmdsets, Django/Evennia tests inside Docker.

---

## Current baseline

Source files read:

- `typeclasses/characters.py`
- `typeclasses/equipment.py`
- `commands/player_commands.py`
- `commands/default_cmdsets.py`
- `world/equipment_tools.py`
- upstream `evennia/contrib/game_systems/clothing/clothing.py`
- `tests/test_equipment_system.py`

Important findings:

- `Character` currently inherits `ClothedCharacter`, but `ClothedCharacterCmdSet` is imported and commented out in `commands/default_cmdsets.py`.
- Existing game inventory is `caller.db.inventory`, not just `caller.contents`.
- Existing equipment state is `caller.db.equipment`, keyed by slots.
- Current equip flow only sets `item.db.worn = True`, not contrib-compatible `item.db.covered_by` or style-aware `db.worn` semantics.
- Upstream clothing helper functions inspect `character.contents`, so copying them directly would miss items stored in `db.inventory` or `db.equipment`.
- `Equipment` has `wear_style` but not `clothing_type`, `covered_by`, or `worn` defaults.
- `CmdInventory` and `CmdEquipment` already exist locally and should stay authoritative instead of re-enabling contrib `CmdInventory`.

## Design decisions

1. Do not keep inheriting from `ClothedCharacter`.
   - Local `Character` should own the appearance logic.
   - This prevents hidden upstream behavior from fighting `db.equipment`.

2. Do not re-enable `ClothedCharacterCmdSet`.
   - Build local commands or extend current `commands/player_commands.py`.
   - Contrib inventory command is incompatible with local `db.inventory`.

3. Use `Equipment` as the single wearable object type.
   - Add clothing compatibility fields to `Equipment.at_object_creation()`.
   - Keep existing durability, stats, slots, magic buffs.

4. Use slot-based equipment as the source of truth for worn items.
   - `db.equipment` decides what is worn.
   - `db.worn`, `db.covered_by`, and `db.wear_style` are derived compatibility/display metadata.

5. Keep `top` and `bottom` non-auto-replace unless Hina later changes the design.
   - This matches current `EQUIPMENT_SLOTS` behavior.

6. Translate all player-facing strings into Traditional Chinese.

## Behavior mapping from upstream clothing.py

| Upstream feature | Local target |
|---|---|
| `order_clothes_list` | Local helper ordering by `EQUIPMENT_SLOTS` plus optional clothing type order aliases |
| `get_worn_clothes(character, exclude_covered=False)` | Local helper reading `character.get_all_equipped().values()` |
| `clothing_type_count` | Local helper for slot/type limits |
| `single_type_count` | Local helper for slot/type limits |
| `ContribClothing.wear` | `Character.equip_item(item, slot, wear_style=None, quiet=False)` plus optional `Equipment.wear()` wrapper |
| `ContribClothing.remove` | `Character.unequip_item(slot_or_item)` plus optional `Equipment.remove()` wrapper |
| `ContribClothing.at_get` | `Equipment.at_get()` clears worn/covered/equipped metadata |
| `ContribClothing.at_pre_move` | `Equipment.at_pre_move()` blocks moving covered items |
| `ClothedCharacter.get_display_desc` | `Character.get_display_desc()` local override |
| `ClothedCharacter.get_display_things` | `Character.get_display_things()` local override hiding worn equipment from carried list |
| `CmdWear` | Local `CmdWearEquipment` in `commands/player_commands.py` |
| `CmdRemove` | Local `CmdRemoveEquipment` in `commands/player_commands.py` |
| `CmdCover` | Local `CmdCoverEquipment` in `commands/player_commands.py` |
| `CmdUncover` | Local `CmdUncoverEquipment` in `commands/player_commands.py` |
| `CmdInventory` | Keep existing local `CmdInventory`, update it to respect covered/worn metadata if needed |
| `ClothedCharacterCmdSet` | Do not use; add local commands to existing `CharacterCmdSet` |

## Compatibility field contract

On every `Equipment` object:

- `db.equip_slot`: canonical slot name.
- `db.clothing_type`: compatibility alias, default same as `equip_slot` when wearable.
- `db.worn`: falsey when not equipped; truthy or style string when equipped.
- `db.wear_style`: display style text, empty string when none.
- `db.covered_by`: object reference or falsey.
- `db.is_equipment`: always `True`.
- `db.two_handed`: existing weapon compatibility.
- `db.stats`, `db.durability`, `db.magic_buffs`: unchanged.

On every `Character` object:

- `db.equipment`: canonical slot map.
- `db.inventory`: canonical inventory list.

## Implementation tasks

### Task 1: Add local clothing constants and helpers to `typeclasses/characters.py`

**Objective:** Remove dependency on upstream helper behavior and make helpers use local equipment slots.

**Files:**

- Modify: `typeclasses/characters.py`
- Test: `tests/test_equipment_system.py` or new focused test module

**Steps:**

1. Remove `from evennia.contrib.game_systems.clothing import ClothedCharacter`.
2. Add constants:
   - `WEARSTYLE_MAXLENGTH = 50`
   - `CLOTHING_OVERALL_LIMIT = 20`
   - `CLOTHING_TYPE_LIMIT = {"hat": 1, "gloves": 1, "shoes": 1, ...}` aligned with `EQUIPMENT_SLOTS`
   - `CLOTHING_TYPE_AUTOCOVER = {"top": [], "bottom": [], ...}` or an explicit map if layering is desired.
   - `CLOTHING_TYPE_CANT_COVER_WITH = {"ring", "earring"}` or empty until design needs restriction.
3. Add local helper functions:
   - `order_equipment_list(items)`
   - `get_worn_equipment(character, exclude_covered=False)`
   - `equipment_type_count(items)`
   - `single_equipment_type_count(items, slot_or_type)`
4. Helpers must read from `character.get_all_equipped()` instead of `character.contents`.
5. Keep names semantically local, but optionally provide compatibility aliases like `get_worn_clothes = get_worn_equipment` only if existing code needs them.

**Verification:**

- Unit test ordering by slot.
- Unit test `exclude_covered=True` hides covered equipment.
- `python -m py_compile typeclasses/characters.py` inside container or host if imports allow.

### Task 2: Change `Character` inheritance to local-only appearance ownership

**Objective:** Stop inheriting upstream `ClothedCharacter` while keeping other current mixins.

**Files:**

- Modify: `typeclasses/characters.py`

**Steps:**

1. Change class definition from:

```python
class Character(ObjectParent, ClothedCharacter, GenderCharacter, ContribRPCharacter):
```

To:

```python
class Character(ObjectParent, DefaultCharacter, GenderCharacter, ContribRPCharacter):
```

2. Confirm MRO still gives Evennia character behavior and existing hooks.
3. Keep `DefaultCharacter` import already present.

**Verification:**

- Import probe for `typeclasses.characters.Character`.
- Existing character creation should still call `at_object_creation()`.

### Task 3: Extend `Equipment` with clothing compatibility metadata and wrappers

**Objective:** Let `Equipment` replace `ContribClothing` as the wearable object typeclass.

**Files:**

- Modify: `typeclasses/equipment.py`
- Test: `tests/test_equipment_system.py`

**Steps:**

1. In `Equipment.at_object_creation()`, add defaults:

```python
"worn": False,
"covered_by": None,
"clothing_type": None,
```

2. If `clothing_type` is missing and `equip_slot` exists, set `clothing_type = equip_slot`.
3. Add `wear(self, wearer, wearstyle=True, quiet=False)` wrapper:
   - Calls `wearer.equip_item(self, slot=self.db.equip_slot, wear_style=wearstyle, quiet=quiet)`.
4. Add `remove(self, wearer, quiet=False)` wrapper:
   - Calls `wearer.unequip_item(self)` or resolves its slot first.
5. Add `at_get(self, getter)`:
   - Clear `db.worn`, `db.covered_by`, maybe `db.wear_style` only if object is no longer equipped.
6. Add `at_pre_move(self, destination, **kwargs)`:
   - Return `False` if `db.covered_by` is truthy.

**Verification:**

- Test newly created equipment has all compatibility fields.
- Test `at_pre_move` blocks covered equipment.
- Test wrapper delegates to character methods.

### Task 4: Refactor `Character.equip_item()` for clothing semantics

**Objective:** Make existing equip logic fully replace upstream wear behavior.

**Files:**

- Modify: `typeclasses/characters.py`
- Test: `tests/test_equipment_system.py`

**Steps:**

1. Change signature to:

```python
def equip_item(self, item, slot=None, wear_style=None, quiet=False):
```

2. Validate item is Equipment-compatible:
   - `getattr(item.db, "is_equipment", False)` or inherited typeclass check if safe.
3. Resolve slot from explicit arg, `item.db.equip_slot`, or `item.db.clothing_type`.
4. Enforce:
   - valid slot
   - broken equipment cannot be equipped, if desired
   - two-hand conflicts as currently implemented
   - slot/type limit
   - overall worn limit
5. Normalize style:
   - `True` or empty means no extra style.
   - String style must be <= `WEARSTYLE_MAXLENGTH`.
6. Remove item from `db.inventory` when equipped, not only weapon slots.
   - Current code only removes weapons. That causes equipped clothing to remain listed as backpack contents.
7. Put replaced item into inventory or room only for `auto_unequip=True` slots.
8. For `auto_unequip=False` slots, reject replacement and return `False` before modifying state.
   - Current code warns but then still continues and overwrites. This is a bug.
9. Set item metadata:
   - `item.db.worn = wear_style if isinstance(wear_style, str) else True`
   - `item.db.wear_style = wear_style if isinstance(wear_style, str) else ""`
   - `item.db.equip_slot = slot`
   - `item.db.clothing_type = getattr(item.db, "clothing_type", None) or slot`
   - `item.location = self` if local inventory/equipment uses object containment, otherwise keep consistent with existing inventory model.
10. Apply auto-cover rules by setting `covered_item.db.covered_by = item`.
11. Emit room message when `quiet=False`; emit player message with current Chinese style.

**Verification:**

- Test equipping removes item from inventory.
- Test top/bottom replacement rejects and does not overwrite.
- Test style string appears in description.
- Test two-hand conflict still works.

### Task 5: Refactor `Character.unequip_item()` to accept slot or item and reveal covered items

**Objective:** Make remove behavior equivalent to upstream `ContribClothing.remove()` but slot-aware.

**Files:**

- Modify: `typeclasses/characters.py`
- Test: `tests/test_equipment_system.py`

**Steps:**

1. Change signature to:

```python
def unequip_item(self, slot_or_item, quiet=False):
```

2. If arg is a string, treat it as slot.
3. If arg is an object, find its current slot in `db.equipment`.
4. Reject if item is missing or not equipped.
5. Reject if `item.db.covered_by` is set, with Chinese message naming the covering item.
6. Clear any items currently covered by this item:
   - For each equipped item where `thing.db.covered_by == item`, set `covered_by = None`.
7. Add unequipped item to `db.inventory`; if full, drop to room as current code does.
8. Clear metadata:
   - equipment slot to `None`
   - `item.db.worn = False`
   - `item.db.covered_by = None`
   - `item.db.wear_style = ""`
9. Emit player and room messages.

**Verification:**

- Test cannot remove covered item.
- Test removing cover reveals covered item.
- Test inventory-full drop path still works.

### Task 6: Override local appearance methods in `Character`

**Objective:** Recreate upstream description and carried-item hiding behavior locally.

**Files:**

- Modify: `typeclasses/characters.py`
- Test: `tests/test_equipment_system.py` or a new appearance-focused test

**Steps:**

1. Implement `get_display_desc(self, looker, **kwargs)`:
   - Start from `self.db.desc` or default description.
   - Build outfit lines from `get_worn_equipment(self, exclude_covered=True)`.
   - Use Chinese text, for example:
     - `正在穿戴：帽子：皮帽、主手武器：鐵劍。`
     - If none: `目前身上沒有穿戴任何裝備。`
   - Include `wear_style` after item name.
2. Implement `get_display_things(self, looker, **kwargs)`:
   - Preserve Evennia default grouping style as much as possible.
   - Exclude objects that are equipped/worn.
   - Also avoid listing objects stored only in `db.inventory` twice if object containment is used.
3. Keep `get_equipment_description()` as reusable formatter for `look`, `equipment`, and tests.

**Verification:**

- Test look description includes equipped visible item.
- Test covered item does not appear.
- Test carried things excludes worn equipment.

### Task 7: Add local wear/remove/cover/uncover commands

**Objective:** Replace upstream clothing commands with local commands that understand `db.inventory` and `db.equipment`.

**Files:**

- Modify: `commands/player_commands.py`
- Modify: `commands/default_cmdsets.py`
- Test: `tests/test_player_commands.py` or new command tests

**Steps:**

1. Add `CmdWearEquipment`:
   - `key = "wear"`
   - aliases: `穿`, `穿戴`, `equip`, `裝備`
   - parse `wear <obj> [=] [style]` and `wear <obj> <style>`.
   - Search candidates from `caller.get_inventory()` plus maybe `caller.contents` for backward compatibility.
   - Call `caller.equip_item(item, wear_style=style)`.
2. Add `CmdRemoveEquipment`:
   - `key = "remove"`
   - aliases: `脫下`, `卸下`, `unequip`
   - Accept slot name or item name.
   - Call `caller.unequip_item(slot_or_item)`.
3. Add `CmdCoverEquipment`:
   - `key = "cover"`
   - aliases: `遮住`, `覆蓋`
   - Parse `cover <worn item> with <worn or inventory item>`.
   - If cover item is not worn, equip it first.
   - Set `target.db.covered_by = cover_item`.
4. Add `CmdUncoverEquipment`:
   - `key = "uncover"`
   - aliases: `露出`, `揭開`
   - Clear `db.covered_by` if legal.
5. Register these commands in `CharacterCmdSet` after current player commands.
6. Remove unused import `ClothedCharacterCmdSet` from `commands/default_cmdsets.py`.

**Verification:**

- Command tests for usage strings and successful calls.
- Live smoke after implementation: wear item, equipment, look self, cover item, uncover, remove.

### Task 8: Update local inventory/equipment display to match new source of truth

**Objective:** Avoid duplicate or misleading equipment in backpack display.

**Files:**

- Modify: `commands/player_commands.py`
- Test: `tests/test_player_commands.py`

**Steps:**

1. In `CmdInventory`, treat `caller.get_inventory()` as backpack only.
2. Do not annotate backpack items as equipped, because equipped items should have been removed from inventory.
3. Optionally add a separate worn section, but prefer keeping `equipment` command authoritative.
4. In `CmdEquipment`, show covered state:
   - `（被 <cover> 覆蓋）`
   - style text if present.

**Verification:**

- Equipping an item removes it from `inventory` output.
- `equipment` shows style and cover state.

### Task 9: Update equipment creation and cloning defaults

**Objective:** Ensure all admin-created equipment has complete clothing metadata.

**Files:**

- Modify: `world/equipment_tools.py`
- Test: `tests/test_equipment_system.py`

**Steps:**

1. In `_clone_equipment_attributes()`, include:
   - `worn=False`
   - `covered_by=None`
   - `clothing_type=template.db.clothing_type or template.db.equip_slot`
2. In `create_equipment()`, include same defaults.
3. Consider adding an admin flag later for `clothing_type`, but do not add it now unless needed.

**Verification:**

- New and cloned equipment have compatibility fields.

### Task 10: Clean imports and de-risk NPC inheritance

**Objective:** Avoid mixed clothing behavior across player and NPC classes.

**Files:**

- Inspect/possibly modify: `typeclasses/llm_npc.py`

**Steps:**

1. `llm_npc.py` also imports and inherits `ClothedCharacter`.
2. Decide whether NPCs need the same local equipment appearance.
3. Minimal safe path:
   - Leave NPCs unchanged for this feature if they do not use equipment.
   - Add a TODO or follow-up task to migrate NPCs later.
4. Better unified path:
   - Extract local clothing/equipment mixin to a small local class and use it in both `Character` and `LocalLLMNPC`.
5. Do not copy a second divergent implementation into `llm_npc.py`.

**Verification:**

- Import `typeclasses.llm_npc` still succeeds.

### Task 11: Test and smoke verification

**Objective:** Prove the replacement does not just compile, but works in the live Evennia environment.

**Files:**

- Modify/create tests under `tests/`

**Commands:**

Use Docker, not host Python, for Evennia-backed tests:

```bash
cd /home/hina/services && docker compose -f /home/hina/services/docker-compose.yaml exec -T evennia bash -lc 'cd /opt/evennia/game && python -m py_compile typeclasses/characters.py typeclasses/equipment.py commands/player_commands.py commands/default_cmdsets.py world/equipment_tools.py'
```

Then targeted tests:

```bash
cd /home/hina/services && docker compose -f /home/hina/services/docker-compose.yaml exec -T evennia bash -lc 'cd /opt/evennia/game && python -m pytest tests/test_equipment_system.py tests/test_player_commands.py -v'
```

If pytest is unavailable, fallback:

```bash
cd /home/hina/services && docker compose -f /home/hina/services/docker-compose.yaml exec -T evennia bash -lc 'cd /opt/evennia/game && python -m unittest tests.test_player_commands -v'
```

Live smoke via `evennia shell -c` should verify:

1. Create or find a temporary player character.
2. Create a hat/top/bottom/weapon Equipment object.
3. Add it to inventory.
4. Run command-level wear/equip.
5. Check `db.equipment` slot.
6. Check item removed from `db.inventory`.
7. Check `look` includes visible equipment.
8. Cover and uncover an item.
9. Remove item and verify return to inventory or room.
10. Delete temporary fixtures.

## Risk points

- `ObjectParent` plus `DefaultCharacter` MRO may need exact ordering verification.
- Existing tests are partly mock/spec tests, not true method tests. They should be strengthened before trusting refactor safety.
- Existing `equip_item()` currently warns on occupied `top`/`bottom` but still overwrites. Fixing this changes behavior, but it matches the stated config and prevents silent item loss.
- `db.inventory` storing object references can become stale if objects are deleted or moved. This plan does not solve that broader storage design.
- If live code expects contrib command names from `ClothedCharacterCmdSet`, they are currently commented out, so replacing them locally should be low risk.

## Success criteria

- `characters.py` no longer imports or inherits `ClothedCharacter`.
- Player-facing clothing functions are implemented locally and use `Equipment`.
- Wear/remove/cover/uncover behavior works with `db.inventory` and `db.equipment`.
- Equipped items affect stats exactly as before.
- Equipped items show in `look` and `equipment`, not as backpack clutter.
- Covered items are hidden and cannot be removed until uncovered or cover is removed.
- Targeted tests and live smoke pass inside the Evennia container.
