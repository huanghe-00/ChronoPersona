"""Minimal demo script for MVA memory system."""

from chronopersona.mocks import MockAgentCore, MockMemoryStore, MockVersionManager


def main() -> None:
    print("=" * 50)
    print("ChronoPersona MVA Demo")
    print("=" * 50)

    store = MockMemoryStore()
    vm = MockVersionManager()
    agent = MockAgentCore()

    # Demo 1: Basic memory write + retrieve
    print("\n[Demo 1] Memory Write & Retrieve")
    mid = store.add(
        MemoryEntry(content="我喜欢川菜"),
        branch_id="main",
    )
    print(f"Added memory: {mid}")
    ctx = store.retrieve("川菜", branch_id="main")
    print(f"Retrieved: {[m.content for m in ctx.episodic_memories]}")

    # Demo 2: Branch isolation
    print("\n[Demo 2] Branch Isolation")
    store.add(MemoryEntry(content="心理咨询记录 #1"), branch_id="therapist")
    ctx_cross = store.retrieve("咨询", branch_id="rpg-hero")
    print(f"Cross-branch retrieve result: {ctx_cross.episodic_memories}")

    # Demo 3: Agent turn
    print("\n[Demo 3] Agent Turn")
    out = agent.run_turn("你好", branch_id="main")
    print(f"Agent reply: {out.reply_text}")
    print(f"Emotion: {out.emotion_state.current_state}")

    # Demo 4: Persona switch
    print("\n[Demo 4] Persona Switch")
    agent.switch_persona("therapist", branch_id="therapist")
    out2 = agent.run_turn("我感觉很焦虑", branch_id="therapist")
    print(f"Agent reply (therapist): {out2.reply_text}")
    print(f"Branch: {out2.branch_id}")

    # Demo 5: Version commit
    print("\n[Demo 5] Version Commit")
    v = vm.commit("main", ChangeSet())
    print(f"Committed version: {v.version} for branch {v.branch_id}")

    print("\n" + "=" * 50)
    print("Demo complete.")
    print("=" * 50)


if __name__ == "__main__":
    from chronopersona.contracts.schemas import ChangeSet, MemoryEntry

    main()
