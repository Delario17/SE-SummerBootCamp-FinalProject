"""Factory function to create the guardrail pipeline from configuration."""
from src.guardrails.base import GuardrailPipeline
from src.guardrails.file_fence import FileFence
from src.guardrails.command_classifier import CommandClassifier
from src.guardrails.hitl import HITLGuard
from src.guardrails.sandbox import SandboxExecutor


def create_guardrail_pipeline(config: dict) -> GuardrailPipeline:
    """Create a full guardrail pipeline from configuration.

    Layer order: FileFence -> CommandClassifier -> HITLGuard -> SandboxExecutor
    """
    guardrail_config = config.get("guardrails", {})

    layers = [
        FileFence(allowed_paths=guardrail_config.get("allowed_paths", [])),
        CommandClassifier(rules=guardrail_config.get("command_rules", [])),
        HITLGuard(timeout=guardrail_config.get("hitl", {}).get("timeout", 30)),
        SandboxExecutor(
            memory_limit_mb=guardrail_config.get("sandbox", {}).get("memory_limit_mb", 512),
            cpu_time_limit=guardrail_config.get("sandbox", {}).get("cpu_time_limit", 30),
        ),
    ]

    return GuardrailPipeline(layers=layers)