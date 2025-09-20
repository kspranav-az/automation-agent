#!/usr/bin/env python3
"""
MCP Server implementation using browser-use library as backbone
Provides browser automation endpoints following MCP protocol
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import traceback

from browser_use import Agent
from openai import OpenAI
import os
import yaml


@dataclass
class MCPCommand:
    """Represents an MCP command with parameters"""
    name: str
    parameters: Dict[str, Any]
    

class MCPServer:
    """
    MCP Server for browser automation using browser-use library
    Exposes browser actions and workflow commands as RPC-style endpoints
    """
    
    def __init__(self, headless: bool = True):
        self.browser = None
        self.headless = headless
        self.llm = None
        self.agent = None
        self.setup_llm()
        self.commands = {}
        self.workflows_dir = Path("workflows")
        self.workflows_dir.mkdir(exist_ok=True)
        self.logs = []
        
        # Register available commands
        self._register_commands()
        
    def _register_commands(self):
        """Register all available MCP commands"""
        self.commands = {
            "navigate": self.navigate,
            "click": self.click,
            "type": self.type_text,
            "extract": self.extract,
            "screenshot": self.screenshot,
            "run_workflow": self.run_workflow,
            "record_workflow": self.record_workflow,
            "list_workflows": self.list_workflows,
        }
        
    def setup_llm(self):
        """Setup LLM for AI-powered automation"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm = OpenAI(api_key=api_key)
                print("✅ OpenAI LLM configured successfully")
            else:
                print("⚠️  No OpenAI API key found, using mock responses")
        except Exception as e:
            print(f"❌ LLM setup failed: {e}")
            self.llm = None
    
    async def initialize_browser(self):
        """Initialize browser with real browser-use agent"""
        try:
            if self.llm:
                # Create real browser-use agent
                self.agent = Agent(
                    task="Browser automation agent for workflow execution",
                    llm=self.llm
                )
                print("✅ Browser agent initialized successfully")
                self.browser = self.agent  # Use agent as browser
                return True
            else:
                print("⚠️  No LLM available, using mock browser")
                self.browser = None
                return False
        except Exception as e:
            print(f"❌ Browser initialization failed: {e}")
            return False
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        try:
            if not self.browser:
                await self.initialize_browser()
            
            if not self.browser:
                await self.initialize_browser()
            
            if self.agent and self.llm:
                # Use real browser automation
                try:
                    # Create agent with navigation task
                    nav_agent = Agent(
                        task=f"Navigate to {url} and confirm the page loads",
                        llm=self.llm
                    )
                    result = await nav_agent.run()
                    return {
                        "success": True, 
                        "url": url,
                        "result": str(result)
                    }
                except Exception as e:
                    return {"success": False, "error": f"Navigation failed: {str(e)}"}
            else:
                # Fallback for demo without API key
                return {"success": True, "url": url, "message": "Navigation simulated (no API key)"}
            
            await page.goto(url)
            return {
                "success": True, 
                "url": url,
                "title": await page.title()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element by selector"""
        try:
            if self.agent and self.llm:
                click_agent = Agent(
                    task=f"Click on the element with selector '{selector}'",
                    llm=self.llm
                )
                result = await click_agent.run()
                return {"success": True, "selector": selector, "result": str(result)}
            else:
                return {"success": True, "selector": selector, "message": "Click simulated (no API key)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element"""
        try:
            if self.agent and self.llm:
                type_agent = Agent(
                    task=f"Type '{text}' into the element with selector '{selector}'",
                    llm=self.llm
                )
                result = await type_agent.run()
                return {"success": True, "selector": selector, "text": text, "result": str(result)}
            else:
                return {"success": True, "selector": selector, "text": text, "message": "Type simulated (no API key)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def extract(self, selector: str) -> Dict[str, Any]:
        """Extract text content from an element"""
        try:
            if self.agent and self.llm:
                extract_agent = Agent(
                    task=f"Extract text content from the element with selector '{selector}'",
                    llm=self.llm
                )
                result = await extract_agent.run()
                return {"success": True, "selector": selector, "content": str(result)}
            else:
                return {"success": True, "selector": selector, "content": "Mock extracted content (no API key)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def screenshot(self, path: str = "screenshot.png") -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if self.agent and self.llm:
                screenshot_agent = Agent(
                    task=f"Take a screenshot and save it to {path}",
                    llm=self.llm
                )
                result = await screenshot_agent.run()
                return {"success": True, "path": path, "result": str(result)}
            else:
                return {"success": True, "path": path, "message": "Screenshot simulated (no API key)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_workflow(self, name: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a workflow by name with variables"""
        try:
            workflow_path = self.workflows_dir / f"{name}.yaml"
            if not workflow_path.exists():
                return {"success": False, "error": f"Workflow '{name}' not found"}
            
            with open(workflow_path, 'r') as f:
                workflow = yaml.safe_load(f)
            
            # Simple workflow execution
            results = []
            for step in workflow.get('steps', []):
                action = step.get('action')
                args = step.get('args', {})
                
                # Substitute variables
                if variables:
                    args = self._substitute_variables(args, variables)
                else:
                    variables = {}
                
                if action in self.commands:
                    result = await self.commands[action](**args)
                    results.append(result)
                    if not result.get('success'):
                        break
            
            return {"success": True, "workflow": name, "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def record_workflow(self, name: str) -> Dict[str, Any]:
        """Start recording a new workflow"""
        try:
            # Basic workflow recording structure
            workflow = {
                "name": name,
                "version": "1.0",
                "steps": [],
                "variables": {}
            }
            
            workflow_path = self.workflows_dir / f"{name}.yaml"
            with open(workflow_path, 'w') as f:
                yaml.dump(workflow, f)
            
            return {"success": True, "workflow": name, "recording": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_workflows(self) -> Dict[str, Any]:
        """List all available workflows"""
        try:
            workflows = []
            for workflow_file in self.workflows_dir.glob("*.yaml"):
                with open(workflow_file, 'r') as f:
                    workflow = yaml.safe_load(f)
                    workflows.append({
                        "name": workflow.get('name'),
                        "version": workflow.get('version'),
                        "file": workflow_file.name
                    })
            
            return {"success": True, "workflows": workflows}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _substitute_variables(self, args: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in arguments"""
        result = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                result[key] = variables.get(var_name, value)
            else:
                result[key] = value
        return result
    
    async def execute_command(self, command_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP command"""
        try:
            if command_name not in self.commands:
                return {"success": False, "error": f"Unknown command: {command_name}"}
            
            command_func = self.commands[command_name]
            result = await command_func(**parameters)
            
            # Log the execution
            self.logs.append({
                "command": command_name,
                "parameters": parameters,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return result
        except Exception as e:
            error_result = {"success": False, "error": str(e), "traceback": traceback.format_exc()}
            self.logs.append({
                "command": command_name,
                "parameters": parameters,
                "result": error_result,
                "timestamp": asyncio.get_event_loop().time()
            })
            return error_result
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.agent and hasattr(self.agent, 'close'):
                await self.agent.close()
            elif self.browser and hasattr(self.browser, 'close'):
                await self.browser.close()
            print("✅ Resources cleaned up successfully")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


# Example usage and test
async def main():
    """Test the MCP server"""
    print("🚀 Starting MCP Server...")
    server = MCPServer(headless=True)
    
    try:
        # Test basic functionality
        print("📝 Testing basic commands...")
        
        # Test navigation
        result = await server.execute_command("navigate", {"url": "https://example.com"})
        print(f"Navigation result: {result}")
        
        # Test screenshot
        result = await server.execute_command("screenshot", {"path": "test_screenshot.png"})
        print(f"Screenshot result: {result}")
        
        # List workflows
        result = await server.execute_command("list_workflows", {})
        print(f"Workflows: {result}")
        
        print("✅ MCP Server test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(traceback.format_exc())
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())