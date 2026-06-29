"""
Custom at_initial_setup hook for Agent 迷航。

這個 hook 只會在世界第一次初始化時執行一次。
"""

from world.agent_world import build_agent_world
from world.agent_xyzgrid import migrate_existing_world_to_xyzgrid



def at_initial_setup():
    # 先補齊 spec 房間/場景，再把同一批 live rooms/exits 掛上 XYZGrid。
    build_agent_world()
    migrate_existing_world_to_xyzgrid(spawn=True)
