"""
Scripts

Scripts are powerful jacks-of-all-trades. They have no in-game
existence and can be used to represent persistent game systems in some
circumstances. Scripts can also have a time component that allows them
to "fire" regularly or a limited number of times.

There is generally no "tree" of Scripts inheriting from each other.
Rather, each script tends to inherit from the base Script class and
just overloads its hooks to have it perform its function.

"""

from evennia.scripts.scripts import DefaultScript


class Script(DefaultScript):
    """
    This is the base TypeClass for all Scripts. Scripts describe
    all entities/systems without a physical existence in the game world
    that require database storage (like an economic system or
    combat tracker). They
    can also have a timer/ticker component.

    A script type is customized by redefining some or all of its hook
    methods and variables.

    * available properties (check docs for full listing, this could be
      outdated).

     key (string) - name of object
     name (string)- same as key
     aliases (list of strings) - aliases to the object. Will be saved
              to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     desc (string)      - optional description of script, shown in listings
     obj (Object)       - optional object that this script is connected to
                          and acts on (set automatically by obj.scripts.add())
     interval (int)     - how often script should run, in seconds. <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     create(key, **kwargs)
     start() - start script (this usually happens automatically at creation
               and at obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0), returns time
                 until next tick

    * Hook methods (should also include self as the first argument):

     at_script_creation() - called only once, when an object of this
                            class is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat
                  stats at regular intervals is only valid to run while there is
                  actual combat going on).
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first
                  call to at_repeat().
      at_repeat() - Called every self.interval seconds. It will be called
                  immediately upon launch unless self.delay_start is True, which
                  will delay the first call of this method by self.interval
                  seconds. If self.interval==0, this method will never
                  be called.
      at_pause()
      at_stop() - Called as the script object is stopped and is about to be
                  removed from the game, e.g. because is_valid() returned False.
      at_script_delete()
      at_server_reload() - Called when server reloads. Can be used to
                  save temporary variables you want should survive a reload.
      at_server_shutdown() - called at a full server shutdown.
      at_server_start()

    """

    pass


# ---------------------------------------------------------------------------
# CombatScript — Evennia-persistent combat session
#
# Persists across `evennia reload` by storing CombatSession state in ScriptDB.
# On every server start, at_start() recovers active sessions into manager.sessions.
# ---------------------------------------------------------------------------

import random
import uuid
from typing import List, Optional


class CombatScript(DefaultScript):
    """
    A turn-based combat session backed by Evennia's ScriptDB for persistence.

    This wraps a CombatSession (plain Python class). On creation the session is
    stored in Both the Evennia ScriptDB (persistent) AND manager.sessions
    (for fast in-process access).  After a reload, at_start() recovers all
    CombatScripts from the database and rebuilds the in-memory session.

    Combat advances on player action (not on a timer), so:
      - interval = 0  (no at_repeat)
      - is_valid() checks has_ended() — expired sessions are auto-deleted
      - at_stop() cleans up the manager.sessions entry
    """

    # ScriptDB stored attributes — these survive server reload
    # Stored in ScriptDB via self.db.<name>

    def at_script_creation(self):
        """Called once when the script is first created."""
        self.db.combatant_ids = []  # list of object dbrefs
        self.db.session_id = None
        self.db.session_state = {}  # serialized CombatSession state (dict)
        self.db.round_count = 1
        self.db.current_turn_index = 0
        self.interval = 0  # no timer
        self.repeats = 0  # infinite (ends via is_valid())
        self.persistent = True

    def is_valid(self) -> bool:
        """Return False when combat has ended → Evennia auto-deletes this script."""
        if not self.db.session_state:
            return False
        # Reconstruct minimally to call has_ended()
        from world.combat_manager import CombatSession

        state = self.db.session_state
        # Check if any combatants have hp > 0
        living = [
            cid for cid in state.get("combatants_ids", []) if self._get_hp(cid) > 0
        ]
        return len(living) > 1  # valid while 2+ combatants alive

    def _get_hp(self, combatant_id):
        """Fetch hp from ScriptDB stored snapshot."""
        snapshot = self.db.session_state.get("combatant_snapshots", {})
        data = snapshot.get(combatant_id, {})
        return data.get("hp", 0)

    def at_start(self):
        """Called on every server start / reload. Recovers session into manager."""
        state = self.db.session_state
        if not state:
            return

        from world.combat_manager import CombatSession, manager

        # Recover combatants from ScriptDB snapshots (dbrefs + attributes)
        combatants = self._reconstruct_combatants()
        if not combatants:
            return

        # Build CombatSession from recovered state
        session = CombatSession.__new__(CombatSession)
        session.session_id = self.db.session_id or str(self.dbref)
        session.combatants = combatants
        session.turn_order = sorted(
            combatants,
            key=lambda c: c.get_stat("agility") + c.get_stat("spd"),
            reverse=True,
        )
        session.current_turn_index = self.db.current_turn_index
        session.round_count = self.db.round_count
        session.is_active = True
        session._turn_timer = None
        session.timer_factory = None

        # Store in manager.sessions
        manager.sessions[session.session_id] = session

        # Restore combatant state from snapshot
        snapshot = self.db.session_state.get("combatant_snapshots", {})
        for combatant in combatants:
            snap = snapshot.get(combatant.dbref, {})
            if snap:
                for k, v in snap.items():
                    setattr(combatant.db, k, v)
            combatant.db.combat_session = session.session_id

    def _reconstruct_combatants(self):
        """Load combatants from Evennia database using stored dbrefs."""
        from evennia.utils.utils import make_iter

        combatant_ids = self.db.combatant_ids or []
        combatants = []
        for cid in combatant_ids:
            # cid might be a string dbref like "#12" or an int
            cid_str = str(cid).lstrip("#")
            try:
                from evennia.objects.models import ObjectDB

                obj = ObjectDB.objects.get(id=int(cid_str))
                # Re-fetch from actual DB to get current state
                combatants.append(obj)
            except Exception:
                pass
        return combatants

    def save_state(self):
        """Snapshot the current session state into ScriptDB."""
        if not hasattr(self, "_session"):
            return
        session = self._session
        self.db.session_id = getattr(session, "session_id", None)
        self.db.combatant_ids = [
            getattr(c, "dbref", None) or getattr(c, "id", None)
            for c in session.combatants
        ]
        self.db.current_turn_index = session.current_turn_index
        self.db.round_count = session.round_count

        # Snapshot key combatant attributes
        snapshot = {}
        for c in session.combatants:
            cid = getattr(c, "dbref", None) or getattr(c, "id", None)
            if cid:
                snapshot[cid] = {
                    "hp": getattr(c.db, "hp", 0),
                    "mp": getattr(c.db, "mp", 0),
                    "combat_status": getattr(c.db, "combat_status", "normal"),
                    "combat_state": getattr(c.db, "combat_state", "idle"),
                    "active_buffs": dict((getattr(c.db, "active_buffs", {}) or {})),
                }
        self.db.session_state = {
            "combatants_ids": self.db.combatant_ids,
            "combatant_snapshots": snapshot,
        }

    def at_stop(self):
        """Called when script is stopped/deleted. Remove from manager.sessions."""
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        if sid and sid in manager.sessions:
            del manager.sessions[sid]

    def at_server_reload(self):
        """Save state before server reload (Same as save_state)."""
        self.save_state()

    def at_server_shutdown(self):
        """Save state before server shutdown."""
        self.save_state()

    # --- Methods that delegate to the in-memory CombatSession ---
    # Called by combat_commands.py via manager.sessions[session_id].method()

    def next_turn(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        if not session:
            return None
        self._session = session  # mark for save_state
        result = session.next_turn()
        self._auto_save()
        return result

    def process_status_effects(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        if session:
            self._session = session
            session.process_status_effects()
            self._auto_save()

    def has_ended(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        return session.has_ended() if session else True

    def living_combatants(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        return session.living_combatants() if session else []

    def get_current_actor(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        return session.get_current_actor() if session else None

    def trigger_ai_turn(self, actor):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        if session:
            self._session = session
            session.trigger_ai_turn(actor)
            self._auto_save()

    def _auto_save(self):
        """Save state after every mutation."""
        try:
            self.save_state()
        except Exception:
            pass
