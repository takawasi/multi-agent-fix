"""CLI interface for multi-agent-fix."""

import sys
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .runner import (
    detect_test_framework,
    run_tests,
    get_test_context,
    apply_fix,
)
from .agent import run_parallel_agents

console = Console()
err_console = Console(file=sys.stderr)


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--agents", "-n", default=3, type=int, help="Number of parallel agents")
@click.option(
    "--framework",
    "-f",
    type=click.Choice(["pytest", "npm", "cargo", "go", "auto"]),
    default="auto",
    help="Test framework",
)
@click.option("--dry-run", is_flag=True, help="Show fixes without applying")
@click.option("--max-attempts", default=3, type=int, help="Max fix attempts per test")
@click.version_option()
def main(path: str, agents: int, framework: str, dry_run: bool, max_attempts: int):
    """Parallel AI agents race to fix your failing tests.

    Examples:

        multi-agent-fix ./my-project
        multi-agent-fix --agents 5 ./src
        multi-agent-fix --framework pytest --dry-run ./tests
    """
    project_path = Path(path).resolve()

    # Detect framework
    if framework == "auto":
        framework = detect_test_framework(project_path)

    err_console.print(f"[bold blue]Project:[/] {project_path}")
    err_console.print(f"[dim]Framework: {framework}[/dim]")
    err_console.print(f"[dim]Agents: {agents}[/dim]")
    err_console.print()

    # Run initial tests
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=err_console,
        transient=True,
    ) as progress:
        progress.add_task("Running tests...", total=None)
        result = run_tests(project_path, framework)

    if result.passed:
        console.print("[green]All tests passing![/green]")
        return

    if not result.failed_tests:
        console.print("[yellow]Tests failed but couldn't parse failures:[/yellow]")
        console.print(result.output)
        sys.exit(1)

    console.print(
        f"[red]Found {len(result.failed_tests)} failing test(s)[/red]"
    )
    for test in result.failed_tests:
        console.print(f"  [dim]- {test}[/dim]")
    console.print()

    # Try to fix each failing test
    fixed_count = 0
    for test_name in result.failed_tests:
        console.print(Panel(f"Fixing: {test_name}", style="blue"))

        # Get test context
        test_ctx = get_test_context(project_path, test_name, framework)
        if not test_ctx.source:
            console.print(f"[yellow]Could not read test source for {test_name}[/yellow]")
            continue

        for attempt in range(max_attempts):
            console.print(f"[dim]Attempt {attempt + 1}/{max_attempts}[/dim]")

            # Run agents in parallel
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=err_console,
                transient=True,
            ) as progress:
                progress.add_task(f"Running {agents} agents...", total=None)
                fixes = run_parallel_agents(
                    test_name,
                    test_ctx.file,
                    test_ctx.source,
                    result.output,
                    agents,
                )

            if not fixes:
                console.print("[yellow]No fixes generated[/yellow]")
                continue

            console.print(f"[green]Generated {len(fixes)} fix(es)[/green]")

            # Try each fix
            original_content = Path(test_ctx.file).read_text() if Path(test_ctx.file).exists() else ""

            for fix in fixes:
                if dry_run:
                    # Show fix without applying
                    table = Table(title=f"Agent {fix.agent_id}")
                    table.add_column("Field", style="cyan")
                    table.add_column("Value")
                    table.add_row("File", fix.file)
                    table.add_row("Explanation", fix.explanation)
                    console.print(table)
                    console.print("[dim]Content preview (first 500 chars):[/dim]")
                    console.print(fix.new_content[:500])
                    console.print()
                    continue

                # Apply fix and test
                if apply_fix(project_path, fix.file, fix.new_content):
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=err_console,
                        transient=True,
                    ) as progress:
                        progress.add_task("Testing fix...", total=None)
                        new_result = run_tests(project_path, framework)

                    if new_result.passed or test_name not in new_result.failed_tests:
                        console.print(
                            f"[green]Agent {fix.agent_id} fixed the test![/green]"
                        )
                        console.print(f"[dim]{fix.explanation}[/dim]")
                        fixed_count += 1
                        break
                    else:
                        # Revert and try next fix
                        apply_fix(project_path, fix.file, original_content)
            else:
                # No fix worked for this attempt
                continue

            # Fix succeeded, move to next test
            break
        else:
            console.print(f"[red]Could not fix {test_name}[/red]")

    console.print()
    if fixed_count > 0:
        console.print(
            f"[green]Fixed {fixed_count}/{len(result.failed_tests)} test(s)[/green]"
        )
    else:
        console.print("[red]No tests were fixed[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
