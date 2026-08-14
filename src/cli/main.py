"""CLI entry point for the Coding Agent Harness."""
import click
import asyncio
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.1")
def cli():
    """AI4SE Coding Agent Harness — a governable, observable coding agent runtime."""
    pass


@cli.command()
@click.argument("task")
@click.option(
    "--config", "-c",
    default="harness.yaml",
    help="Path to configuration file.",
)
@click.option(
    "--mock", is_flag=True,
    help="Use mock LLM backend (for testing).",
)
def run(task: str, config: str, mock: bool):
    """Run a coding task with the agent.

    TASK is the description of what you want the agent to do.
    """
    from src.config.loader import ConfigLoader
    from src.loop.agent import AgentLoop

    loader = ConfigLoader()
    try:
        cfg = loader.load(config)
    except FileNotFoundError:
        click.echo(
            f"Config file not found: {config}\n"
            f"Run 'harness setup' to configure the harness.",
            err=True,
        )
        sys.exit(1)

    if mock:
        from src.llm.mock_backend import MockLLMBackend
        from src.models import LLMResponse, ToolCall
        backend = MockLLMBackend(responses=[
            LLMResponse(
                tool_calls=[ToolCall(
                    id="c1", name="finish",
                    arguments={"summary": "Mock mode: task acknowledged."},
                )],
                finish_reason="tool_calls",
            )
        ])
    else:
        from src.llm.openai_backend import OpenAICompatBackend
        llm_config = cfg.get("llm", {})
        import keyring
        api_key = keyring.get_password("harness", "api_key")
        if not api_key:
            click.echo(
                "No API key found. Run 'harness setup' to configure your key.",
                err=True,
            )
            sys.exit(1)
        backend = OpenAICompatBackend(
            api_key=api_key,
            model=llm_config.get("model", "gpt-4o"),
            api_base=llm_config.get("api_base", ""),
            temperature=llm_config.get("temperature", 0.1),
            max_tokens=llm_config.get("max_tokens", 4096),
        )

    async def _run():
        loop = AgentLoop(cfg)
        result = await loop.run(task, backend)
        return result

    click.echo(f"Task: {task}")
    click.echo(f"Config: {config}")
    click.echo(f"Mode: {'Mock' if mock else 'Live'}")

    result = asyncio.run(_run())
    click.echo(f"\n{'=' * 50}")
    click.echo(f"Result: {result.stop_reason.value}")
    click.echo(f"Turns: {result.turns}")
    click.echo(f"Summary: {result.summary}")


@cli.command()
@click.option("--reset", is_flag=True, help="Reset (overwrite) existing API key.")
@click.option("--clear", is_flag=True, help="Remove the stored API key.")
def setup(reset: bool, clear: bool):
    """Configure API key and settings."""
    import keyring

    SERVICE = "harness"
    USERNAME = "api_key"

    if clear:
        try:
            keyring.delete_password(SERVICE, USERNAME)
            click.echo("API key removed from keyring.")
        except keyring.errors.PasswordDeleteError:
            click.echo("No API key was stored.")
        return

    existing = keyring.get_password(SERVICE, USERNAME)
    if existing and not reset:
        click.echo("API key is already configured. Use --reset to overwrite or --clear to remove.")
        return

    click.echo("Enter your API key (input will be hidden):")
    api_key = click.prompt("API Key", hide_input=True, confirmation_prompt=True)
    keyring.set_password(SERVICE, USERNAME, api_key)
    click.echo("API key stored securely in system keyring.")


@cli.command()
def status():
    """Show harness status and configuration."""
    import keyring

    SERVICE = "harness"
    USERNAME = "api_key"

    click.echo("Harness Status:")
    click.echo(f"  Version: 0.1.0")

    api_key = keyring.get_password(SERVICE, USERNAME)
    if api_key:
        click.echo(f"  API Key: **** (stored in keyring)")
    else:
        click.echo(f"  API Key: not configured (run 'harness setup')")

    from pathlib import Path
    default_config = Path("harness.yaml")
    user_config = Path.home() / ".harness" / "config.yaml"
    if default_config.exists():
        click.echo(f"  Config: {default_config.resolve()}")
    elif user_config.exists():
        click.echo(f"  Config: {user_config}")
    else:
        click.echo(f"  Config: not found")


if __name__ == "__main__":
    cli()