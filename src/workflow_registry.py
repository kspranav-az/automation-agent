#!/usr/bin/env python3
"""
Workflow Registry - Stores and manages workflow specifications
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class WorkflowSpec:
    """Workflow specification"""
    name: str
    version: str
    domain: Optional[str]
    variables: Dict[str, str]
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class WorkflowRegistry:
    """
    Manages workflow storage, versioning and retrieval
    """
    
    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(exist_ok=True)
        self.workflows = {}
        self.load_all_workflows()
    
    def load_all_workflows(self):
        """Load all workflows from disk"""
        try:
            for workflow_file in self.workflows_dir.glob("*.yaml"):
                with open(workflow_file, 'r') as f:
                    workflow_data = yaml.safe_load(f)
                    if workflow_data:
                        spec = WorkflowSpec(
                            name=workflow_data.get('name', workflow_file.stem),
                            version=workflow_data.get('version', '1.0'),
                            domain=workflow_data.get('domain'),
                            variables=workflow_data.get('variables', {}),
                            steps=workflow_data.get('steps', []),
                            metadata=workflow_data.get('metadata', {})
                        )
                        self.workflows[spec.name] = spec
            print(f"📁 Loaded {len(self.workflows)} workflows")
        except Exception as e:
            print(f"❌ Error loading workflows: {e}")
    
    def find_workflow(self, site: Optional[str], intent: str) -> Optional[WorkflowSpec]:
        """Find a workflow matching site and intent"""
        for workflow in self.workflows.values():
            # Simple matching logic
            if site and workflow.domain and site in workflow.domain:
                return workflow
            elif intent.lower() in workflow.name.lower():
                return workflow
        return None
    
    def get_workflow(self, name: str) -> Optional[WorkflowSpec]:
        """Get workflow by name"""
        return self.workflows.get(name)
    
    def save_workflow(self, spec: WorkflowSpec) -> bool:
        """Save workflow to disk"""
        try:
            workflow_data = {
                'name': spec.name,
                'version': spec.version,
                'domain': spec.domain,
                'variables': spec.variables,
                'steps': spec.steps,
                'metadata': spec.metadata
            }
            
            workflow_path = self.workflows_dir / f"{spec.name}.yaml"
            with open(workflow_path, 'w') as f:
                yaml.dump(workflow_data, f, default_flow_style=False)
            
            self.workflows[spec.name] = spec
            print(f"💾 Saved workflow: {spec.name}")
            return True
        except Exception as e:
            print(f"❌ Error saving workflow: {e}")
            return False
    
    def create_sample_workflows(self):
        """Create sample workflows for testing"""
        
        # Sample Jira workflow
        jira_workflow = WorkflowSpec(
            name="jira_ticket_export",
            version="1.0",
            domain="jira.company.com",
            variables={
                "project_key": "str",
                "start_date": "str",
                "end_date": "str"
            },
            steps=[
                {
                    "action": "navigate",
                    "args": {"url": "https://example.com"}
                },
                {
                    "action": "screenshot", 
                    "args": {"path": "jira_export.png"}
                }
            ],
            metadata={
                "description": "Export Jira tickets for a project",
                "created": datetime.now().isoformat(),
                "sensitive": False
            }
        )
        
        # Sample test workflow
        test_workflow = WorkflowSpec(
            name="test_navigation",
            version="1.0", 
            domain="example.com",
            variables={},
            steps=[
                {
                    "action": "navigate",
                    "args": {"url": "https://example.com"}
                },
                {
                    "action": "screenshot",
                    "args": {"path": "test.png"}
                },
                {
                    "action": "extract",
                    "args": {"selector": "h1"}
                }
            ],
            metadata={
                "description": "Simple test workflow",
                "created": datetime.now().isoformat(),
                "sensitive": False
            }
        )
        
        self.save_workflow(jira_workflow)
        self.save_workflow(test_workflow)
        print("📝 Created sample workflows")
        
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows"""
        return [
            {
                "name": spec.name,
                "version": spec.version,
                "domain": spec.domain,
                "description": spec.metadata.get('description', ''),
                "steps": len(spec.steps)
            }
            for spec in self.workflows.values()
        ]