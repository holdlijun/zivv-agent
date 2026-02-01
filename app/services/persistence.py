import json
from app.core.db import get_db_connection
from app.agent.state import AgentState

MAX_RETRIES = 5
RETRY_BASE_SECONDS = 5


def mark_job_failed(job_id: int, error_msg: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE cleaning_jobs
                SET
                    retries = retries + 1,
                    last_error = %s,
                    status = CASE WHEN retries + 1 > %s THEN 3 ELSE 0 END,
                    next_run_at = CASE
                        WHEN retries + 1 > %s THEN NOW()
                        ELSE NOW() + (retries + 1) * (%s * INTERVAL '1 second')
                    END,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (error_msg, MAX_RETRIES, MAX_RETRIES, RETRY_BASE_SECONDS, job_id),
            )
            conn.commit()
    finally:
        conn.close()


def persist_result(state: AgentState):
    print(f"[*] [Persist][Job:{state['job_id']}] Saving results for Stage:{state['stage']}")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if state.get("status") == "error":
                cur.execute(
                    """
                    UPDATE cleaning_jobs
                    SET
                        retries = retries + 1,
                        last_error = %s,
                        status = CASE WHEN retries + 1 > %s THEN 3 ELSE 0 END,
                        next_run_at = CASE
                            WHEN retries + 1 > %s THEN NOW()
                            ELSE NOW() + (retries + 1) * (%s * INTERVAL '1 second')
                        END,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (state.get("error_msg") or "error", MAX_RETRIES, MAX_RETRIES, RETRY_BASE_SECONDS, state["job_id"]),
                )
                conn.commit()
                return

            # 记录分级分析结果
            if state["stage"] == 2 and state.get("tags"):
                # 将 risk_level 和 short_comment 组合存入 risk_hint
                risk_hint = f"[{state.get('risk_level', 'Medium')}] {state.get('short_comment', '')}"
                cur.execute(
                    "INSERT INTO token_tags (token_id, tags, vibe_score, risk_hint) VALUES (%s, %s, %s, %s)",
                    (state["token_id"], json.dumps(state["tags"]), state.get("vibe_score"), risk_hint),
                )

                cur.execute(
                    "INSERT INTO analysis_reports (token_id, report_text) VALUES (%s, %s)",
                    (state["token_id"], state["report"]),
                )

            # 记录链上 Alpha 数据
            if state.get("alpha_data"):
                alpha = state["alpha_data"]
                cur.execute(
                    """
                    INSERT INTO token_alpha (
                        token_id, smart_money_score, holder_concentration, 
                        is_cabal_confirmed, top_holders_pnl, degen_score
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (token_id) DO UPDATE SET
                        smart_money_score = EXCLUDED.smart_money_score,
                        holder_concentration = EXCLUDED.holder_concentration,
                        is_cabal_confirmed = EXCLUDED.is_cabal_confirmed,
                        top_holders_pnl = EXCLUDED.top_holders_pnl,
                        updated_at = NOW()
                    """,
                    (
                        state["token_id"],
                        alpha.get("smart_money_count"), # 暂时用 count 代替 score
                        alpha.get("holder_concentration"),
                        alpha.get("is_cabal_confirmed"),
                        json.dumps(alpha) if alpha else None,
                        alpha.get("degen_score")
                    )
                )

            # 更新 Project 表用于前端展示
            if state.get("status") == "passed":
                # 计算 risk_hint 用于同步到 Project 表
                risk_hint = None
                if state.get("risk_level") and state.get("short_comment"):
                    risk_hint = f"[{state.get('risk_level')}] {state.get('short_comment')}"
                elif state["stage"] == 2:
                    # 如果当前刚好是 stage 2，直接构造
                    risk_hint = f"[{state.get('risk_level', 'Medium')}] {state.get('short_comment', '')}"

                cur.execute(
                    """
                    INSERT INTO "Project" (
                        id, symbol, name, "imageUrl", "chainId", "contractAddress", 
                        "marketCap", "liquidity", "priceChange24h", age, "safetyLevel", tags, "riskHint", description, "aiReport", "hypeScore", type
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'MEME')
                    ON CONFLICT (id) DO UPDATE SET 
                        tags = EXCLUDED.tags,
                        "riskHint" = EXCLUDED."riskHint",
                        "hypeScore" = EXCLUDED."hypeScore",
                        description = EXCLUDED.description,
                        "aiReport" = EXCLUDED."aiReport",
                        "marketCap" = EXCLUDED."marketCap",
                        "liquidity" = EXCLUDED."liquidity",
                        "priceChange24h" = EXCLUDED."priceChange24h"
                    """,
                    (
                        str(state["contract"]),
                        state["symbol"],
                        state["name"],
                        state["data"].get("image_url"),
                        state["data"].get("chain") or "bsc",
                        state["contract"],
                        str(state["data"].get("market_cap") or "0"),
                        str(state["data"].get("liquidity") or "0"),
                        state["data"].get("price_change_24h"),
                        "New",
                        "SAFE",
                        state.get("tags") or [],
                        risk_hint,
                        state["data"].get("description") or "",
                        state.get("report") or "",
                        state.get("vibe_score") or 0,
                    ),
                )

            cur.execute(
                "UPDATE cleaning_jobs SET status = 2, updated_at = NOW() WHERE id = %s",
                (state["job_id"],),
            )
            print(f"[*] [Persist][Job:{state['job_id']}] Job marked as COMPLETED")

            # 阶段派发下一阶段任务
            if state.get("status") == "passed":
                next_stage = state["stage"] + 1
                if next_stage <= 3:
                    if next_stage == 3 and (state.get("vibe_score") or 0) < 60:
                        pass
                    else:
                        print(f"[*] [Persist][Job:{state['job_id']}] Creating/Updating NEXT STAGE job: {next_stage}")
                        cur.execute(
                            """
                            INSERT INTO cleaning_jobs (token_id, stage, status, next_run_at, created_at, updated_at)
                            VALUES (%s, %s, 0, NOW(), NOW(), NOW())
                            ON CONFLICT (token_id, stage) DO UPDATE 
                            SET status = 0, updated_at = NOW()
                            WHERE cleaning_jobs.status != 2
                            """,
                            (state["token_id"], next_stage),
                        )

            conn.commit()
    finally:
        conn.close()
