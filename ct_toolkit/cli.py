"""
ct_toolkit.cli
--------------
Main entry point for the Theseus Guard / CT Toolkit CLI.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ct_toolkit import TheseusWrapper, WrapperConfig, __version__
from ct_toolkit.divergence.l3_icm import ICMRunner
from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.server import start_server

app = typer.Typer(
    help="Computational Theseus Toolkit — Identity Continuity Guardrails for Agentic Systems.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()

BANNER = r"""
  _______ _    _ ______  _____ ______ _    _  _____    _____ _    _          _____  _____  
 |__   __| |  | |  ____|/ ____|  ____| |  | |/ ____|  / ____| |  | |   /\   |  __ \|  __ \ 
    | |  | |__| | |__  | (___ | |__  | |  | | (___   | |  __| |  | |  /  \  | |__) | |  | |
    | |  |  __  |  __|  \___ \|  __| | |  | |\___ \  | | |_ | |  | | / /\ \ |  _  /| |  | |
    | |  | |  | | |____ ____) | |____| |__| |____) | | |__| | |__| |/ ____ \| | \ \| |__| |
    |_|  |_|  |_|______|_____/|______|_____/|_____/   \_____|\____//_/    \_\_|  \_\_____/ 
"""

def show_banner():
    console.print(f"[bold cyan]{BANNER}[/bold cyan]")
    console.print(f"[bold white]  Computatonal Theseus Toolkit (CT Toolkit) v{__version__}[/bold white]")
    console.print(f"[dim]  Identity Continuity Guardrails for Agentic Systems[/dim]\n")

def version_callback(value: bool):
    if value:
        console.print(f"CT Toolkit v{__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version and exit.", callback=version_callback
    ),
):
    """Theseus Guard CLI — Preserve Agent Identity Continuity."""
    if not version:
        show_banner()

@app.command()
def audit(
    url: str = typer.Option(..., "--url", help="Target LLM API base URL."),
    api_key: str = typer.Option("no-key", "--api-key", help="API Key for the provider."),
    provider: str = typer.Option("openai", "--provider", help="LLM provider (openai, anthropic, ollama)."),
    kernel: str = typer.Option("general", "--kernel", help="Name of the Constitutional Kernel to use."),
    template: str = typer.Option("general", "--template", help="Name of the Identity Template to use."),
    model: Optional[str] = typer.Option(None, "--model", help="Specific model ID to test."),
    max_probes: Optional[int] = typer.Option(None, "--max-probes", help="Max number of probes to run."),
):
    """Run an Independent Identity Audit (L3 ICM) against an LLM endpoint."""
    with console.status("[bold green]Initializing Auditor...[/bold green]"):
        try:
            # Load kernel
            config = WrapperConfig(
                kernel_name=kernel,
                template=template,
                project_root=Path.cwd()
            )
            
            # Using TheseusWrapper to manage kernel loading
            wrapper = TheseusWrapper(provider=provider, config=config)
            
            import openai
            client = openai.OpenAI(base_url=url, api_key=api_key)

            runner = ICMRunner(
                client=client,
                provider=provider,
                kernel=wrapper.kernel,
                template=template,
                model=model,
                max_probes=max_probes,
                project_root=Path.cwd()
            )
        except Exception as e:
            console.print(f"[bold red]Initialization failed:[/bold red] {e}")
            raise typer.Exit(code=1)

    console.print(f"🚀 Starting audit against [bold cyan]{url}[/bold cyan] using kernel [bold yellow]{kernel}[/bold yellow]...")
    
    with console.status("[bold blue]Running probes...[/bold blue]"):
        try:
            report = runner.run()
            if report.total_probes == 0:
                console.print(f"[bold red]Error:[/bold red] No probes were loaded from {runner.PROBES_DIR}. Check your configuration and probe files.")
                raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[bold red]Audit failed during execution:[/bold red] {e}")
            raise typer.Exit(code=1)

    # Results Table
    table = Table(title=f"ICM Audit Report: {kernel}", show_header=True, header_style="bold magenta")
    table.add_column("Probe ID", style="dim", width=20)
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Result", justify="center")

    for res in report.results:
        status = "[green]PASS[/green]" if res.passed else "[red]FAIL[/red]"
        table.add_row(res.probe_id, res.category, res.severity, status)

    console.print(table)

    # Summary Panel
    color = "green" if report.is_healthy else "red"
    if report.risk_level == "MEDIUM":
        color = "yellow"
        
    summary_text = (
        f"Health Score : [bold]{report.health_score:.1%}[/bold]\n"
        f"Risk Level   : [bold {color}]{report.risk_level}[/bold {color}]\n"
        f"Passed/Total : {report.passed}/{report.total_probes}"
    )
    
    console.print(Panel(summary_text, title="Summary", border_style=color, expand=False))

    if not report.is_healthy:
        raise typer.Exit(code=1)

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind the server to."),
    port: int = typer.Option(8001, "--port", help="Port to bind the server to."),
    kernel: str = typer.Option("general", "--kernel", help="Name of the Constitutional Kernel to use."),
    template: str = typer.Option("general", "--template", help="Name of the Identity Template to use."),
    vault_path: str = typer.Option("./ct_provenance.db", "--vault", help="Path to the provenance log database."),
    judge_provider: str = typer.Option("openai", "--judge-provider", help="LLM provider for the L2 judge."),
    judge_model: Optional[str] = typer.Option(None, "--judge-model", help="Model ID for the L2 judge."),
):
    """Start the CT-Toolkit Guardrail Server for LiteLLM integration."""
    console.print(f"Starting Guardrail Server...")
    console.print(f"  - Kernel: [bold yellow]{kernel}[/bold yellow]")
    console.print(f"  - Template: [bold green]{template}[/bold green]")
    console.print(f"  - Bind: [bold cyan]{host}:{port}[/bold cyan]")
    
    try:
        config = WrapperConfig(
            kernel_name=kernel,
            template=template,
            vault_path=vault_path,
            project_root=Path.cwd()
        )
        wrapper = TheseusWrapper(provider=judge_provider, config=config)
        
        # Start the uvicorn server
        start_server(wrapper=wrapper, host=host, port=port)
    except Exception as e:
        console.print(f"[bold red]Failed to start server:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def setup(
    profile: str = typer.Argument("personal_kernel", help="Name of the profile to download (e.g., personal_kernel)"),
    repo_branch: str = typer.Option("main", "--branch", help="GitHub repo branch"),
    dest_dir: str = typer.Option("./config", "--dest", help="Destination folder (default: ./config)")
):
    """Download a CT-Toolkit profile (kernel, identity, probes) from the official GitHub repository."""
    import urllib.request
    
    base_url = f"https://raw.githubusercontent.com/hakandamar/ct-toolkit/{repo_branch}/examples/agent_dna_config"
    target_dir = Path(dest_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = profile.replace("_kernel", "") if profile.endswith("_kernel") else profile
    if base_name == profile:
        kernel_file = f"{profile}_kernel.yaml"
    else:
        kernel_file = f"{profile}.yaml"
        
    identity_file = f"{base_name}_identity.yaml"
    probes_file = f"{base_name}_probes.json"
    
    files_to_download = [kernel_file, identity_file, probes_file]
    
    with console.status(f"[bold green]Downloading '{profile}' profile from GitHub...[/bold green]"):
        has_errors = False
        for filename in files_to_download:
            url = f"{base_url}/{filename}"
            dest_path = target_dir / filename
            try:
                # Use a custom user agent to avoid 403s on some raw github requests occasionally
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    content = response.read()
                    with open(dest_path, "wb") as f:
                        f.write(content)
                console.print(f"[green]✓ Saved {filename} to {dest_path}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Failed to download {filename} from {url}:[/red] {e}")
                has_errors = True
                
    if not has_errors:
        console.print(f"\n[bold blue]Profile '{profile}' setup complete![/bold blue]")
        console.print(f"You can now use this kernel by setting [bold]kernel_name='{kernel_file.replace('.yaml','')}'[/bold] in TheseusWrapper")
    else:
        console.print(f"\n[bold yellow]Profile '{profile}' setup finished with some errors.[/bold yellow]")

@app.command()
def list_kernels():
    """List available Constitutional Kernels."""
    kernels_dir = Path(__file__).parent / "kernels"
    files = list(kernels_dir.glob("*.yaml"))
    
    table = Table(title="Available Kernels", show_header=True, header_style="bold blue")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    
    for f in files:
        table.add_row(f.stem, str(f))
        
    console.print(table)

@app.command()
def list_templates():
    """List available Identity Templates."""
    templates_dir = Path(__file__).parent / "identity" / "templates"
    files = list(templates_dir.glob("*.yaml"))
    
    table = Table(title="Available Templates", show_header=True, header_style="bold green")
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    
    for f in files:
        table.add_row(f.stem, str(f))
        
    console.print(table)

if __name__ == "__main__":
    app()
