from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import rule_filter_node, slm_tagger_node, alpha_detective_node, deep_dive_node
from app.services.persistence import persist_result

def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("rule_filter", rule_filter_node)
    workflow.add_node("slm_tagger", slm_tagger_node)
    workflow.add_node("alpha_detective", alpha_detective_node) # 保留定义，暂时不连入流程
    workflow.add_node("deep_dive", deep_dive_node)
    
    # 每一阶段处理完后都执行持久化
    workflow.add_node("persist", persist_result)

    # 简化的流转逻辑
    workflow.set_entry_point("rule_filter") # 实际入口控制在 main.py

    # 逻辑流转: L1 -> L2 -> L3 -> Persist
    workflow.add_conditional_edges(
        "rule_filter",
        lambda x: "slm_tagger" if x["status"] == "passed" else "persist"
    )
    
    # 临时禁用 alpha_detective，直接流向 deep_dive
    workflow.add_conditional_edges(
        "slm_tagger",
        lambda x: "deep_dive" if x["status"] == "passed" and (x.get("vibe_score") or 0) >= 60 else "persist"
    )
    
    # workflow.add_edge("alpha_detective", "deep_dive") # 暂时移除
    workflow.add_edge("deep_dive", "persist")
    workflow.add_edge("persist", END)

    return workflow.compile()

graph = create_graph()
