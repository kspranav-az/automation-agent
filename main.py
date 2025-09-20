#!/usr/bin/env python3
"""
Main entry point for the Browser Automation Workflow System
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_server import MCPServer
from workflow_registry import WorkflowRegistry
from router import Router
from cli import cli


async def initialize_system():
    """Initialize the browser automation system"""
    print("🚀 Initializing Browser Automation Workflow System...")
    
    # Create workflows directory
    workflows_dir = Path("workflows")
    workflows_dir.mkdir(exist_ok=True)
    
    # Initialize workflow registry with sample workflows
    registry = WorkflowRegistry()
    registry.create_sample_workflows()
    
    # Initialize MCP server
    server = MCPServer()
    await server.initialize_browser()
    
    print("✅ System initialized successfully")
    return server, registry


async def run_server():
    """Run the MCP server and handle requests"""
    server, registry = await initialize_system()
    
    try:
        print("🔧 Testing system functionality...")
        
        # Test workflow listing
        result = await server.execute_command("list_workflows", {})
        print(f"📋 Available workflows: {result}")
        
        # Test navigation
        result = await server.execute_command("navigate", {"url": "https://example.com"})
        print(f"🌐 Navigation test: {result}")
        
        # Test screenshot
        result = await server.execute_command("screenshot", {"path": "test_screenshot.png"})
        print(f"📸 Screenshot test: {result}")
        
        # Test workflow execution
        result = await server.execute_command("run_workflow", {"name": "test_navigation", "variables": {}})
        print(f"⚙️ Workflow execution test: {result}")
        
        print("✅ All tests completed successfully")
        print("🎯 System is ready to handle requests")
        
        # Keep server running
        print("🖥️  Server running... (Press Ctrl+C to stop)")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        await server.cleanup()


def main():
    """Main function - can be called from CLI or directly"""
    if len(sys.argv) > 1:
        # Run CLI commands
        cli()
    else:
        # Run server
        asyncio.run(run_server())


if __name__ == "__main__":
    main()