"""Command Line Interface for AI PDF Chatter Evaluation Framework."""

import argparse
import asyncio
import json
import sys
from typing import Optional

from app.eval.datasets import list_datasets
from app.eval.runner import EvaluationRunner


def main():
    parser = argparse.ArgumentParser(description="AI PDF Chatter - Unified AI Evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: list
    list_parser = subparsers.add_parser("list", help="List available evaluation datasets")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run an evaluation benchmark run")
    run_parser.add_argument("--dataset", type=str, default="retrieval-v1", help="Dataset version (e.g. retrieval-v1, agent-v1, multidoc-v1)")
    run_parser.add_argument("--provider", type=str, default="ollama", help="LLM provider (e.g. ollama, openai, mock)")
    run_parser.add_argument("--model", type=str, default="qwen3:4b-instruct", help="LLM model name")
    run_parser.add_argument("--limit", type=int, default=0, help="Limit number of evaluation cases")
    run_parser.add_argument("--output", type=str, choices=["json", "markdown", "console"], default="console", help="Output format")

    args = parser.parse_args()

    if args.command == "list":
        datasets = list_datasets()
        print("\n=== AI PDF Chatter Benchmark Datasets ===")
        for d in datasets:
            print(f"- {d['dataset_version']} ({d['case_count']} cases): {d['description']}")
        print()
        sys.exit(0)

    elif args.command == "run":
        print(f"\n[EVAL] Running Evaluation Benchmark: Dataset='{args.dataset}', Provider='{args.provider}', Model='{args.model}'...")
        runner = EvaluationRunner()
        results = asyncio.run(
            runner.run_evaluation(
                dataset_version=args.dataset,
                llm_provider=args.provider,
                llm_model=args.model,
                limit=args.limit if args.limit > 0 else None
            )
        )

        if args.output == "json":
            print(json.dumps(results, indent=2))
        elif args.output == "markdown":
            print(generate_markdown_report(results))
        else:
            print_console_summary(results)
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


def print_console_summary(results: dict):
    print("\n" + "=" * 60)
    print(f" EVALUATION RUN RESULTS: {results['run_name']}")
    print("=" * 60)
    print(f"Dataset Version:    {results['dataset_version']}")
    print(f"Pipeline Version:   {results['pipeline_version']}")
    print(f"Model/Provider:     {results['llm_model']} ({results['llm_provider']})")
    print(f"Quality Gates:      {'PASS [OK]' if results['quality_gates_result']['passed'] else 'FAIL [FAIL]'}")
    print("-" * 60)
    
    ms = results["metrics_summary"]
    print(f"Recall@K:           {ms.get('recall_at_k', 0.0):.2%}")
    print(f"Precision@K:        {ms.get('precision_at_k', 0.0):.2%}")
    print(f"Faithfulness:       {ms.get('faithfulness', 0.0):.2%}")
    print(f"Citation Correct:   {ms.get('citation_correctness', 0.0):.2%}")
    print(f"Agent Efficiency:   {ms.get('agent_efficiency_score', 0.0):.2%}")
    print(f"Spoiler Leakage:    {ms.get('spoiler_leakage_rate', 0.0):.2%}")
    
    lat = results["latency_summary"]
    print("-" * 60)
    print(f"Latency P50:        {lat.get('p50', 0.0)} ms")
    print(f"Latency P95:        {lat.get('p95', 0.0)} ms")
    print(f"Latency P99:        {lat.get('p99', 0.0)} ms")
    print("=" * 60 + "\n")


def generate_markdown_report(results: dict) -> str:
    gates = results['quality_gates_result']['gates']
    gates_table = "\n".join([
        f"| **{g}** | `{info['target']}` | `{info['actual']}` | {'PASS [OK]' if info['passed'] else 'FAIL [FAIL]'} |"
        for g, info in gates.items()
    ])

    return f"""# AI PDF Chatter — Evaluation Report ({results['run_name']})

## Run Metadata
- **Run ID**: `{results['id']}`
- **Dataset**: `{results['dataset_version']}`
- **Pipeline Version**: `{results['pipeline_version']}`
- **LLM**: `{results['llm_model']}` (`{results['llm_provider']}`)
- **Embedding**: `{results['embedding_model']}` (`{results['embedding_dimension']}-dim`)
- **Status**: `{results['status']}`
- **Quality Gates Result**: **{'PASS [OK]' if results['quality_gates_result']['passed'] else 'FAIL [FAIL]'}**

---

## Quality Gates Summary
| Quality Gate | Target Standard | Measured Value | Status |
| :--- | :--- | :--- | :--- |
{gates_table}

---

## Metrics Summary
- **Recall@K**: `{results['metrics_summary'].get('recall_at_k', 0.0):.2%}`
- **Precision@K**: `{results['metrics_summary'].get('precision_at_k', 0.0):.2%}`
- **Faithfulness**: `{results['metrics_summary'].get('faithfulness', 0.0):.2%}`
- **Citation Correctness**: `{results['metrics_summary'].get('citation_correctness', 0.0):.2%}`
- **Agent Efficiency Score**: `{results['metrics_summary'].get('agent_efficiency_score', 0.0):.2%}`
- **Spoiler Leakage Rate**: `{results['metrics_summary'].get('spoiler_leakage_rate', 0.0):.2%}`

---

## Latency Breakdown
- **P50 Latency**: `{results['latency_summary'].get('p50', 0.0)} ms`
- **P95 Latency**: `{results['latency_summary'].get('p95', 0.0)} ms`
- **P99 Latency**: `{results['latency_summary'].get('p99', 0.0)} ms`
- **Sample Size**: `{results['latency_summary'].get('sample_size', 0)} cases`
"""



if __name__ == "__main__":
    main()
