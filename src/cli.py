#!/usr/bin/env python3
"""
CLI interface for browser automation workflow system
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import yaml

from mcp_server import MCPServer
from workflow_registry import WorkflowRegistry
from router import Router

console = Console()


@click.group()
def cli():
    """Browser Automation Workflow System"""
    pass


@cli.command()
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
def server(headless):
    """Start the MCP server"""
    async def run_server():
        console.print("🚀 Starting MCP Server...", style="bold green")
        server = MCPServer(headless=headless)
        
        try:
            result = await server.execute_command("list_workflows", {})
            console.print(f"📋 Available workflows: {result}")
            
            # Keep server running
            console.print("✅ MCP Server is running. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            console.print("\n🛑 Shutting down server...")
        finally:
            await server.cleanup()
    
    asyncio.run(run_server())


@cli.command()
def workflows():
    """List all available workflows"""
    registry = WorkflowRegistry()
    workflows = registry.list_workflows()
    
    if not workflows:
        console.print("📭 No workflows found", style="yellow")
        return
    
    table = Table(title="Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green") 
    table.add_column("Domain", style="blue")
    table.add_column("Steps", justify="center")
    table.add_column("Description", style="dim")
    
    for workflow in workflows:
        table.add_row(
            workflow['name'],
            workflow['version'],
            workflow.get('domain', 'N/A'),
            str(workflow['steps']),
            workflow.get('description', '')
        )
    
    console.print(table)


@cli.command()
@click.argument('prompt')
def run(prompt):
    """Run a workflow from natural language prompt"""
    async def execute_prompt():
        console.print(f"🤖 Processing: {prompt}", style="bold")
        
        router = Router()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executing workflow...", total=1)
            
            try:
                result = await router.handle_prompt(prompt)
                progress.update(task, completed=1)
                
                console.print("✅ Result:", style="bold green")
                console.print(result)
                
            except Exception as e:
                console.print(f"❌ Error: {e}", style="bold red")
    
    asyncio.run(execute_prompt())


@cli.command()
@click.argument('name')
def create(name):
    """Create a new workflow interactively"""
    console.print(f"📝 Creating workflow: {name}", style="bold")
    
    registry = WorkflowRegistry()
    
    # Basic workflow creation
    steps = []
    console.print("Add workflow steps (press Enter with empty input to finish):")
    
    while True:
        action = console.input("Action (navigate/click/type/extract/screenshot): ").strip()
        if not action:
            break
        
        if action == "navigate":
            url = console.input("URL: ")
            steps.append({"action": "navigate", "args": {"url": url}})
        elif action == "screenshot":
            path = console.input("Screenshot path (optional): ").strip() or "screenshot.png"
            steps.append({"action": "screenshot", "args": {"path": path}})
        else:
            console.print(f"Action {action} not implemented yet", style="yellow")
    
    if steps:
        from workflow_registry import WorkflowSpec
        from datetime import datetime
        
        spec = WorkflowSpec(
            name=name,
            version="1.0",
            domain=None,
            variables={},
            steps=steps,
            metadata={
                "description": f"Custom workflow: {name}",
                "created": datetime.now().isoformat()
            }
        )
        
        if registry.save_workflow(spec):
            console.print(f"✅ Workflow '{name}' created successfully", style="green")
        else:
            console.print(f"❌ Failed to create workflow '{name}'", style="red")
    else:
        console.print("❌ No steps added, workflow not created", style="red")


@cli.command()
def init():
    """Initialize the system with sample workflows"""
    console.print("🔧 Initializing system...", style="bold")
    
    registry = WorkflowRegistry()
    registry.create_sample_workflows()
    
    console.print("✅ System initialized with sample workflows", style="green")


if __name__ == "__main__":
    cli()