"""CLI entry point for the Coding Agent Harness."""
import click
import asyncio
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.2")
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
    except ValueError as e:
        click.echo(f"Config error: {e}", err=True)
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
    """Configure API key, model, and API base URL."""
    import keyring

    SERVICE = "harness"
    USERNAME = "api_key"

    # ── Clear ──────────────────────────────────────────────
    if clear:
        try:
            keyring.delete_password(SERVICE, USERNAME)
            click.echo("✓ API key removed from keyring.")
        except keyring.errors.PasswordDeleteError:
            click.echo("No API key was stored.")
        return

    # ── Show current status ────────────────────────────────
    existing = keyring.get_password(SERVICE, USERNAME)
    if existing and not reset:
        masked = existing[:4] + "****" + existing[-4:] if len(existing) > 8 else "****"
        click.echo(f"API key is already configured: {masked}")
        click.echo()
        click.echo("To change it, run:")
        click.echo("  harness setup --reset")
        click.echo("To remove it, run:")
        click.echo("  harness setup --clear")
        click.echo()
        _print_config_guide()
        return

    # ── Collect API key ────────────────────────────────────
    if existing and reset:
        click.echo("Overwriting existing API key...")
        click.echo()

    click.echo("Enter your API key (input will be hidden):")
    api_key = click.prompt("API Key", hide_input=True, confirmation_prompt=True)
    keyring.set_password(SERVICE, USERNAME, api_key)
    click.echo("✓ API key stored securely in system keyring.")
    click.echo()

    # ── Guide for model / api_base ─────────────────────────
    _print_config_guide()


def _print_config_guide():
    """Print guidance for configuring model and api_base."""
    from pathlib import Path

    user_config = Path.home() / ".harness" / "config.yaml"
    local_config = Path("harness.yaml")

    click.echo("─" * 55)
    click.echo("Next: configure model and API base URL")
    click.echo("─" * 55)
    click.echo()
    click.echo("The harness reads model and api_base from a YAML config file.")
    click.echo()

    if local_config.exists():
        click.echo(f"  Config file found: {local_config.resolve()}")
    elif user_config.exists():
        click.echo(f"  Config file found: {user_config}")
    else:
        click.echo("  No config file found. Create one at either:")
        click.echo(f"    • {local_config.resolve()}  (project-level)")
        click.echo(f"    • {user_config}  (user-level)")
        click.echo()
        click.echo("Example config (~/.harness/config.yaml):")
        click.echo()
        click.echo("  llm:")
        click.echo('    model: "gpt-4o"')
        click.echo('    api_base: "https://your-relay.com/v1"')
        click.echo('    temperature: 0.1')
        click.echo('    max_tokens: 4096')

    click.echo()
    click.echo("After editing the config, verify with:")
    click.echo("  harness status")


@cli.command()
def status():
    """Show harness status and configuration."""
    import keyring

    SERVICE = "harness"
    USERNAME = "api_key"

    click.echo("Harness Status:")
    click.echo(f"  Version: 0.1.2")

    api_key = keyring.get_password(SERVICE, USERNAME)
    if api_key:
        masked = api_key[:4] + "****" + api_key[-4:] if len(api_key) > 8 else "****"
        click.echo(f"  API Key: {masked} (keyring)")
    else:
        click.echo(f"  API Key: not configured (run 'harness setup')")

    from pathlib import Path
    from src.config.loader import ConfigLoader

    default_config = Path("harness.yaml")
    user_config = Path.home() / ".harness" / "config.yaml"
    config_path = None
    if default_config.exists():
        config_path = default_config.resolve()
    elif user_config.exists():
        config_path = user_config

    if config_path:
        click.echo(f"  Config:   {config_path}")
        try:
            loader = ConfigLoader()
            cfg = loader.load(str(config_path))
            llm = cfg.get("llm", {})
            click.echo(f"  Model:    {llm.get('model', 'N/A')}")
            click.echo(f"  API Base: {llm.get('api_base', 'N/A')}")
        except Exception:
            pass
    else:
        click.echo(f"  Config:   using built-in defaults")
        click.echo(f"  Model:    gpt-4o (default)")
        click.echo(f"  API Base: not set (edit harness.yaml to configure)")


if __name__ == "__main__":
    cli()