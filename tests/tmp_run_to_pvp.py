from tests.run_combat_live_smoke import CombatLiveSmokeRunner

r = CombatLiveSmokeRunner()
r.create_temp_characters()
try:
    r.test_combat_lock_and_basic_kill()
    r.test_stun_flow()
    r.test_poison_round_tick_kill()
    r.test_alias_target_resolution()
    r.test_self_target_guards()
    r.test_insufficient_mp()
    try:
        r.test_player_pvp_room_gate()
        print('pvp_gate_ok')
    except Exception as e:
        print('pvp_gate_failed', repr(e))
        print('alpha_tail', r.tail(r.alpha, 30))
        print('beta_tail', r.tail(r.beta, 30))
        print('alpha_state', r.alpha.db.combat_state)
        print('beta_state', r.beta.db.combat_state)
        print('room_pvp', getattr(r.room.db, 'pvp_enabled', None))
        print('beta_hp', r.beta.db.hp)
        print('beta_account', r.beta.db_account)
        print('beta_is_npc', r.beta.db.is_npc)
        raise
finally:
    r.cleanup()
