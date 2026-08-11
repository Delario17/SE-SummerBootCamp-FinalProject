#!/usr/bin/env python3
"""Demo 3: Full guardrail pipeline — four-layer state machine.

This demo shows the complete guardrail pipeline in action:
FileFence -> CommandClassifier -> HITL -> Sandbox
Each layer is tested independently and then as a pipeline.
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Action
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.sandbox import SandboxExecutor
from src.guardrails.base import GuardrailPipeline


async def main():
    print("=" * 60)
    print("Demo 3: Guardrail Pipeline -- Four-Layer State Machine")
    print("=" * 60)

    # Configure all four layers
    file_fence = FileFence(allowed_paths=["./src", "./tests", "./demo"])
    classifier = CommandClassifier(rules=[
        {"pattern": r"^(ls|cat|pytest|echo|mkdir|python)\b", "level": "safe"},
        {"pattern": r"^(pip install|git commit)\b", "level": "warn"},
        {"pattern": r"\brm -rf\b|\bDROP TABLE\b|git push --force|\bsudo\b", "level": "dangerous"},
    ])
    hitl = HITLGuard(timeout=30, input_func=lambda _: "y")  # Simulate approval
    sandbox = SandboxExecutor(memory_limit_mb=512, cpu_time_limit=10)
    pipeline = GuardrailPipeline([file_fence, classifier, hitl, sandbox])

    # Test 1: Safe command passes all layers
    print("\n[Test 1] Safe command (ls) passes all four layers:")
    action1 = Action(tool_name="run_shell", arguments={"cmd": "ls ./src"})
    result1 = await pipeline.check(action1)
    print(f"  Action: run_shell('ls ./src')")
    print(f"  Result: blocked={result1.blocked}, level={result1.level}")
    assert result1.blocked is False, "FAIL: Safe command should pass!"
    print("  PASS")

    # Test 2: File fence blocks path traversal
    print("\n[Test 2] File fence blocks path traversal:")
    action2 = Action(tool_name="read_file", arguments={"path": "../../../etc/passwd"})
    result2 = await pipeline.check(action2)
    print(f"  Action: read_file('../../../etc/passwd')")
    print(f"  Result: blocked={result2.blocked}, reason={result2.reason}")
    assert result2.blocked is True, "FAIL: Path traversal should be blocked!"
    print("  PASS")

    # Test 3: Dangerous command triggers HITL
    print("\n[Test 3] Dangerous command goes through classification -> HITL:")
    action3 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf ./tmp"})
    result3 = await pipeline.check(action3)
    print(f"  Action: run_shell('rm -rf ./tmp')")
    print(f"  Result: blocked={result3.blocked}, level={result3.level}")
    print(f"  Requires HITL: {result3.requires_hitl}")
    assert result3.level == "dangerous", "FAIL: rm -rf should be dangerous!"
    print("  PASS")

    # Test 4: Sandbox executes safe command
    print("\n[Test 4] Sandbox executes a safe command in isolation:")
    action4 = Action(tool_name="run_shell", arguments={"cmd": "echo 'sandbox test' && pwd"})
    result4 = await sandbox.execute(action4)
    print(f"  Action: run_shell('echo sandbox test')")
    print(f"  Success: {result4.success}")
    print(f"  Output: {result4.stdout.strip()}")
    print(f"  Working dir: {result4.stdout.strip().split()[-1] if result4.stdout else 'N/A'}")
    assert result4.success is True, "FAIL: Safe command should succeed in sandbox!"
    print("  PASS")

    # Test 5: HITL timeout simulation
    print("\n[Test 5] HITL timeout rejects dangerous command:")
    hitl_timeout = HITLGuard(timeout=0.01, input_func=lambda _: None)
    action5 = Action(tool_name="run_shell", arguments={"cmd": "rm -rf /"})
    result5 = await hitl_timeout.request_approval(action5)
    print(f"  Action: run_shell('rm -rf /')")
    print(f"  Result: blocked={result5.blocked}, reason={result5.reason}")
    assert result5.blocked is True, "FAIL: Timeout should block!"
    assert result5.reason == "timeout", "FAIL: Reason should be timeout!"
    print("  PASS")

    print("\n" + "=" * 60)
    print("Demo 3: ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())