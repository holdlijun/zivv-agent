import time
from app.services.scheduler import pull_jobs, get_token_details
from app.agent.graph import graph
from app.agent.nodes import slm_tagger_node, deep_dive_node
from app.services.persistence import persist_result, mark_job_failed
from app.core.config import config


def run_worker():
    print("[*] Zivv Distributed Agent Worker 启动成功...")
    while True:
        batch_start = time.time()
        jobs = pull_jobs()
        if jobs:
            print(f"[*] [Worker] Pulled {len(jobs)} jobs: {[j['id'] for j in jobs]}")
        if not jobs:
            time.sleep(config.POLL_INTERVAL)
            continue

        for job in jobs:
            token = get_token_details(job["token_id"])
            if not token:
                mark_job_failed(job["id"], "token not found")
                continue

            state = {
                "job_id": job["id"],
                "token_id": job["token_id"],
                "contract": token["contract"],
                "symbol": token["symbol"] or "Unknown",
                "name": token["name"] or "Unknown",
                "stage": job["stage"],
                "data": token,
                "tags": [],
                "vibe_score": None,
                "report": None,
                "status": "pending",
                "error_msg": None,
            }

            try:
                # 根据任务阶段路由到对应的 Agent
                if job["stage"] == 1:
                    print(f"[*] [Main] Job:{job['id']} Stage:1 -> Entering Graph")
                    graph.invoke(state)
                elif job["stage"] == 2:
                    print(f"[*] [Main] Job:{job['id']} Stage:2 -> Manual Node Call")
                    res = slm_tagger_node(state)
                    persist_result(res)
                elif job["stage"] == 3:
                    print(f"[*] [Main] Job:{job['id']} Stage:3 -> Manual Node Call")
                    res = deep_dive_node(state)
                    persist_result(res)
            except Exception as e:
                print(f"[!] [Main] Job:{job['id']} 运行崩溃: {e}")
                mark_job_failed(job["id"], str(e))
        batch_cost = time.time() - batch_start
        if jobs:
            print(f"[*] batch_size={len(jobs)} cost={batch_cost:.3f}s")


if __name__ == "__main__":
    run_worker()
