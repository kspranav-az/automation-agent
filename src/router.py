#!/usr/bin/env python3
"""
Router - Planner-Executor that routes prompts to workflows or agents
"""

import asyncio
from typing import Dict, Any, Optional, Tuple
import re
import json
import os
from openai import OpenAI

from mcp_server import MCPServer
from workflow_registry import WorkflowRegistry


class Router:
    """
    Routes user prompts to appropriate workflows or falls back to browser agents
    """
    
    def __init__(self):
        self.registry = WorkflowRegistry()
        self.server = MCPServer()
        self.llm = None
        self.setup_llm()
        
    def setup_llm(self):
        """Setup LLM for AI-powered prompt parsing"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm = OpenAI(api_key=api_key)
                print("✅ Router LLM configured for AI parsing")
            else:
                print("⚠️  No OpenAI API key, using regex parsing fallback")
        except Exception as e:
            print(f"❌ Router LLM setup failed: {e}")
            self.llm = None
        
    async def handle_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Main routing logic: prompt -> workflow or agent
        """
        try:
            # Parse the prompt to identify site, intent, and variables
            site, intent, variables = await self.parse_prompt(prompt)
            
            # Try to find matching workflow
            workflow = self.registry.find_workflow(site, intent)
            
            if workflow:
                print(f"📋 Found workflow: {workflow.name}")
                try:
                    # Run the workflow
                    result = await self.server.run_workflow(workflow.name, variables)
                    return {
                        "success": True,
                        "source": "workflow",
                        "workflow": workflow.name,
                        "result": result
                    }
                except Exception as e:
                    print(f"⚠️  Workflow failed, falling back to agent: {e}")
                    return await self.fallback_to_agent(prompt, workflow)
            else:
                print("🤖 No matching workflow, using agent")
                return await self.fallback_to_agent(prompt)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "router"
            }
    
    async def parse_prompt(self, prompt: str) -> Tuple[Optional[str], str, Dict[str, Any]]:
        """
        AI-powered parsing to extract site, intent, and variables from natural language
        """
        if self.llm:
            return await self.ai_parse_prompt(prompt)
        else:
            return self.regex_parse_prompt(prompt)
    
    async def ai_parse_prompt(self, prompt: str) -> Tuple[Optional[str], str, Dict[str, Any]]:
        """
        Use AI to parse natural language prompts intelligently
        """
        try:
           
            response = self.llm.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a workflow parsing assistant. Parse user prompts to extract:\n"
                        "1. site: domain/platform (jira, github, salesforce, etc.)\n"
                        "2. intent: action type (navigate, export, create, search, test, etc.)\n"
                        "3. variables: extracted parameters (project_key, url, dates, etc.)\n\n"
                        "Respond ONLY with JSON in this exact format:\n"
                        "{\"site\": \"domain or null\", \"intent\": \"action\", \"variables\": {\"key\": \"value\"}}"
                    },
                    {
                        "role": "user", 
                        "content": f"Parse this prompt: {prompt}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            site = result.get("site")
            if site == "null" or site == "None":
                site = None
            intent = result.get("intent", "general")
            variables = result.get("variables", {})
            
            print(f"🤖 AI parsed - Site: {site}, Intent: {intent}, Variables: {variables}")
            return site, intent, variables
            
        except Exception as e:
            print(f"⚠️  AI parsing failed, falling back to regex: {e}")
            return self.regex_parse_prompt(prompt)
    
    def regex_parse_prompt(self, prompt: str) -> Tuple[Optional[str], str, Dict[str, Any]]:
        """
        Fallback regex-based parsing
        """
        prompt_lower = prompt.lower()
        
        # Detect common sites/domains
        site = None
        if "jira" in prompt_lower:
            site = "jira.company.com"
        elif "github" in prompt_lower:
            site = "github.com"
        elif "example.com" in prompt_lower:
            site = "example.com"
        
        # Extract intent keywords
        intent = ""
        if any(word in prompt_lower for word in ["export", "download", "get", "extract"]):
            intent = "export"
        elif any(word in prompt_lower for word in ["navigate", "go", "visit", "open"]):
            intent = "navigate"
        elif any(word in prompt_lower for word in ["test", "check", "verify"]):
            intent = "test"
        else:
            intent = "general"
        
        # Extract basic variables (simplified)
        variables = {}
        
        # Look for project keys
        project_match = re.search(r'project[:\s]+([A-Z]+)', prompt, re.IGNORECASE)
        if project_match:
            variables['project_key'] = project_match.group(1)
        
        # Look for URLs
        url_match = re.search(r'https?://[^\s]+', prompt)
        if url_match:
            variables['url'] = url_match.group(0)
        
        print(f"🔍 Regex parsed - Site: {site}, Intent: {intent}, Variables: {variables}")
        return site, intent, variables
    
    async def fallback_to_agent(self, prompt: str, failed_workflow=None) -> Dict[str, Any]:
        """
        Fallback to browser-use agent when workflow fails or doesn't exist
        """
        try:
            # For now, simulate agent execution
            print(f"🤖 Agent processing: {prompt}")
            
            # Execute basic commands based on prompt
            result = {"success": True, "message": "Agent execution simulated"}
            
            if "navigate" in prompt.lower():
                # Extract URL or use default
                url = "https://example.com"
                url_match = re.search(r'https?://[^\s]+', prompt)
                if url_match:
                    url = url_match.group(0)
                
                nav_result = await self.server.navigate(url)
                result["navigation"] = nav_result
            
            if "screenshot" in prompt.lower():
                screenshot_result = await self.server.screenshot()
                result["screenshot"] = screenshot_result
            
            return {
                "success": True,
                "source": "agent",
                "prompt": prompt,
                "result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "agent"
            }


# Test function
async def test_router():
    """Test the router functionality"""
    router = Router()
    
    # Initialize sample workflows
    router.registry.create_sample_workflows()
    
    test_prompts = [
        "Navigate to example.com and take a screenshot",
        "Go to jira and export tickets", 
        "Test the navigation workflow"
    ]
    
    for prompt in test_prompts:
        print(f"\n🧪 Testing: {prompt}")
        result = await router.handle_prompt(prompt)
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_router())