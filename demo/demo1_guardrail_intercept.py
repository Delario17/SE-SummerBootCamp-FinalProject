#!/usr/bin/env python3
"""Demo 1: Guardrail intercepts a dangerous action.

This demo shows the guardrail system intercepting a dangerous command (rm -rf /)
and preventing its execution. Uses Mock LLM for deterministic behavior.
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Action, GuardrailResult
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.base import GuardrailPipeline


async def main():
    print("=" * 60)
    print("Demo 1: Guardrail Intercepts Dangerous Action")
    print("=" * 60)

    # Configure guardrails
    file_fence = FileFence(allowed_paths=["./src", "./tests", "./demo"])
    classifier = CommandClassifier(rules=[
        {"pattern": r"^(ls|cat|pytest|echo)\b", "level": "safe"},
        {"pattern": r"\brm -rf\b", "level": "dangerous"},
    ])

    # Test 1: File fence blocks outside access
    print("\n[Test 1] File fence should block /etc/passwd access:")
    action1 = Action(tool_name="read_file", arguments={"path": "/etc/passwd"})
    result1 = await file_fence.check(action1)
    print(f"  Action: read_file('/etc/passwd')")
    print(f"  Result: blocked={result1.blocked}, reason={result1.reason}")
    assert result1.blocked is True, "FAIL: /etc/passwd should be blocked!"
    print("  PASS")

    # Test 2: Command classifier flags rm -rf
    print("\n[Test 2] Command classifier flags rm -rf as dangerous:")
    action2 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result2 = await classifier.check(action2)
    print(f"  Action: run_shell('rm -rf /')")
    print(f"  Result: level={result2.level}, blocked={result2.blocked}")
    assert result2.level == "dangerous", "FAIL: rm -rf should be dangerous!"
    print("  PASS")

    # Test 3: Pipeline stops at first block
    print("\n[Test 3] Pipeline stops at file fence (first layer):")
    pipeline = GuardrailPipeline([file_fence, classifier])
    action3 = Action(tool_name="read_file", arguments={"path": "/etc/shadow"})
    result3 = await pipeline.check(action3)
    print(f"  Action: read_file('/etc/shadow')")
    print(f"  Result: blocked={result3.blocked}, reason={result3.reason}")
    assert result3.blocked is True, "FAIL: Pipeline should block!"
    print("  PASS")

    # Test 4: HITL rejects dangerous command
    print("\n[Test 4] HITL rejects dangerous command (simulated rejection):")
    hitl = HITLGuard(timeout=30, input_func=lambda _: "n")
    action4 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result4 = await hitl.request_approval(action4)
    print(f"  Action: run_shell('rm -rf ./tmp')")
    print(f"  Result: blocked={result4.blocked}, reason={result4.reason}")
    assert result4.blocked is True, "FAIL: HITL should reject!"
    print("  PASS")

    print("\n" + "=" * 60)
    print("Demo 1: ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())