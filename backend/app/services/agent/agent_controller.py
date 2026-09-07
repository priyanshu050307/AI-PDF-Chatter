import uuid
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.models.document import Document
from app.models.agent import AgentRun, AgentStep
from app.services.agent.tools import get_agent_tools, BaseAgentTool
from app.services.agent.evidence_ledger import EvidenceLedger
from app.services.agent.agent_router import AgentRouter, AgentRoute
from app.services.context_builder import ContextBuilder, StructuredContext
from app.services.ai_service import get_ai_service
from app.services.rag_service import RAGService
from app.core.errors import NotFoundError, ValidationError, AIProviderUnavailableError


class AgentController:
    """
    Agentic AI Controller & Execution Loop.
    Executes bounded, observable, schema-validated, and secure multi-step document investigations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tools = get_agent_tools(db)
        self.router = AgentRouter()

    async def run_investigation(
        self,
        user: User,
        document_id: uuid.UUID,
        query: str,
        conversation_id: Optional[uuid.UUID] = None,
        mode: str = "auto",
        current_page: Optional[int] = None,
        spoiler_mode: str = "spoiler_free"
    ) -> Dict[str, Any]:
        """
        Executes bounded Agentic Investigation or routes to fast Normal RAG.
        Returns response containing: answer, route, steps, citations, and run telemetry.
        """
        start_time = time.time()

        # Determine max_page cap for spoiler protection
        max_page = current_page if spoiler_mode == "spoiler_free" else None

        # 1. Route Query
        route, is_agentic = self.router.route_query(query, mode_override=mode)

        # Create AgentRun record
        run = AgentRun(
            id=uuid.uuid4(),
            user_id=user.id,
            document_id=document_id,
            conversation_id=conversation_id,
            query=query,
            state="CREATED",
            route=route.value,
            max_steps=settings.AGENT_MAX_STEPS,
            model=settings.LLM_MODEL,
            provider=settings.LLM_PROVIDER
        )
        self.db.add(run)
        await self.db.commit()

        # Fast Path for Simple Factual queries in Auto mode
        if not is_agentic and mode == "auto":
            run.state = "ROUTING"
            await self.db.commit()

            rag_service = RAGService(self.db)
            rag_res = await rag_service.query_document(
                user=user,
                document_id=document_id,
                query=query,
                conversation_id=conversation_id,
                current_page=current_page
            )

            run.state = "COMPLETED"
            run.completed_at = run.started_at
            run.latency_ms = (time.time() - start_time) * 1000
            run.telemetry_json = {"fast_path": True, "route": route.value}
            await self.db.commit()

            return {
                "run_id": str(run.id),
                "query": query,
                "answer": rag_res["content"],
                "route": route.value,
                "state": "COMPLETED",
                "steps": [],
                "citations": rag_res.get("citations", []),
                "latency_ms": run.latency_ms
            }

        # 2. Agentic RAG Multi-Step Execution Loop
        run.state = "PLANNING"
        await self.db.commit()

        ledger = EvidenceLedger()
        steps_history: List[Dict[str, Any]] = []

        # Formulate initial bounded plan steps based on route
        planned_actions = self._create_initial_plan(route, query, max_page)

        # Log Planning Step
        plan_step = AgentStep(
            id=uuid.uuid4(),
            run_id=run.id,
            step_index=0,
            action_type="PLAN",
            tool_name="planner",
            tool_input_json={"query": query, "route": route.value, "planned_steps_count": len(planned_actions)},
            tool_output_json={"plan": [a["tool"] for a in planned_actions]},
            status="COMPLETED",
            duration_ms=5.0
        )
        self.db.add(plan_step)
        run.step_count += 1
        run.state = "EXECUTING"
        await self.db.commit()

        step_idx = 1
        for action in planned_actions:
            if step_idx > settings.AGENT_MAX_STEPS or (time.time() - start_time) > settings.AGENT_TIMEOUT_SECONDS:
                break

            tool_name = action["tool"]
            tool_input = action["input"]
            if tool_name not in self.tools:
                continue

            tool_instance = self.tools[tool_name]
            step_start = time.time()

            try:
                # Execute tool under timeout protection
                tool_output = await asyncio.wait_for(
                    tool_instance.run(user=user, document_id=document_id, tool_input=tool_input),
                    timeout=settings.AGENT_TIMEOUT_SECONDS
                )
                step_status = "COMPLETED"
                duration_ms = (time.time() - step_start) * 1000

                # Extract and deduplicate evidence into ledger
                added_count = ledger.add_from_tool_output(tool_name, str(document_id), tool_output)

                # Persist step record
                step_record = AgentStep(
                    id=uuid.uuid4(),
                    run_id=run.id,
                    step_index=step_idx,
                    action_type="TOOL_CALL",
                    tool_name=tool_name,
                    tool_input_json=tool_input,
                    tool_output_json={"status": "success", "evidence_added": added_count},
                    status=step_status,
                    duration_ms=duration_ms
                )
                self.db.add(step_record)
                run.step_count += 1
                await self.db.commit()

                steps_history.append({
                    "step": step_idx,
                    "tool": tool_name,
                    "description": f"Executed {tool_name}",
                    "status": "COMPLETED",
                    "duration_ms": duration_ms
                })

            except asyncio.TimeoutError:
                step_record = AgentStep(
                    id=uuid.uuid4(),
                    run_id=run.id,
                    step_index=step_idx,
                    action_type="TOOL_CALL",
                    tool_name=tool_name,
                    tool_input_json=tool_input,
                    tool_output_json={"error": "Tool execution timed out"},
                    status="TIMED_OUT",
                    duration_ms=(time.time() - step_start) * 1000
                )
                self.db.add(step_record)
                await self.db.commit()
            except Exception as exc:
                logger.warning(f"Agent tool '{tool_name}' error: {exc}")
                step_record = AgentStep(
                    id=uuid.uuid4(),
                    run_id=run.id,
                    step_index=step_idx,
                    action_type="TOOL_CALL",
                    tool_name=tool_name,
                    tool_input_json=tool_input,
                    tool_output_json={"error": str(exc)},
                    status="FAILED",
                    duration_ms=(time.time() - step_start) * 1000
                )
                self.db.add(step_record)
                await self.db.commit()

            step_idx += 1

        # 3. Final Answer Synthesis
        run.state = "SYNTHESIZING"
        await self.db.commit()

        formatted_chunks = ledger.to_chunks_format()

        # Extract graph context if present in ledger
        graph_context = {}
        for r in ledger.records:
            if r.source_type == "entity":
                if "entities" not in graph_context:
                    graph_context["entities"] = []
                graph_context["entities"].append({"name": r.title, "description": r.content})
            elif r.source_type == "relationship":
                if "relationships" not in graph_context:
                    graph_context["relationships"] = []
                graph_context["relationships"].append({"description": r.content, "observed_page": r.page_number})
            elif r.source_type == "event":
                if "events" not in graph_context:
                    graph_context["events"] = []
                graph_context["events"].append({"title": r.title, "page_number": r.page_number, "description": r.content})

        struct_ctx = StructuredContext(
            page_number=current_page,
            retrieved_chunks=formatted_chunks,
            narrative_context=graph_context
        )

        context_builder = ContextBuilder()
        system_prompt, snapshot, citations = context_builder.build_system_prompt_and_snapshot(
            user_query=query,
            structured_context=struct_ctx
        )

        ai_service = get_ai_service()
        ai_res = await ai_service.generate_answer(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": query}]
        )

        run.state = "COMPLETED"
        run.completed_at = func.now()
        run.latency_ms = (time.time() - start_time) * 1000
        run.telemetry_json = {
            "evidence_records_count": len(ledger.records),
            "citations_count": len(citations),
            "steps_count": len(steps_history)
        }
        await self.db.commit()

        return {
            "run_id": str(run.id),
            "query": query,
            "answer": ai_res["content"],
            "route": route.value,
            "state": "COMPLETED",
            "steps": steps_history,
            "citations": citations,
            "latency_ms": run.latency_ms
        }

    def _create_initial_plan(self, route: AgentRoute, query: str, max_page: Optional[int]) -> List[Dict[str, Any]]:
        """Formulates bounded initial tool execution plan based on query route."""
        actions = []

        if route == AgentRoute.CHARACTER_NARRATIVE:
            # Step 1: Find matched entity
            actions.append({
                "tool": "find_entity",
                "input": {"name_or_alias": query}
            })
            # Step 2: Retrieve timeline events
            actions.append({
                "tool": "find_events",
                "input": {"keyword": query, "max_page": max_page}
            })
            # Step 3: Supporting hybrid retrieval
            actions.append({
                "tool": "search_evidence",
                "input": {"query": query, "top_k": 3, "max_page": max_page}
            })
        elif route == AgentRoute.COMPARISON:
            # Split query by comparison terms if possible
            q_clean = query.replace("compare", "").replace("between", "").replace("and", "vs")
            parts = [p.strip() for p in q_clean.split("vs") if p.strip()]
            entity_a = parts[0] if len(parts) >= 1 else query
            entity_b = parts[1] if len(parts) >= 2 else query

            actions.append({
                "tool": "compare_entities",
                "input": {"entity_a_name": entity_a, "entity_b_name": entity_b, "max_page": max_page}
            })
            actions.append({
                "tool": "search_evidence",
                "input": {"query": query, "top_k": 3, "max_page": max_page}
            })
        elif route == AgentRoute.ANNOTATION_ANALYSIS:
            actions.append({
                "tool": "get_my_annotations",
                "input": {"keyword": query}
            })
            actions.append({
                "tool": "search_evidence",
                "input": {"query": query, "top_k": 3, "max_page": max_page}
            })
        else:  # MULTI_STEP_INVESTIGATION
            actions.append({
                "tool": "get_document_structure",
                "input": {}
            })
            actions.append({
                "tool": "search_evidence",
                "input": {"query": query, "top_k": 5, "max_page": max_page}
            })

        return actions
