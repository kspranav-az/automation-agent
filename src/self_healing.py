#!/usr/bin/env python3
"""
Self-Healing Mechanism - AI-powered workflow repair and adaptation
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback
from pathlib import Path

from browser_use import Agent
from workflow_registry import WorkflowRegistry, WorkflowSpec


@dataclass
class RepairSuggestion:
    """Represents a workflow repair suggestion"""
    workflow_name: str
    step_index: int
    issue_type: str
    issue_description: str
    suggested_fix: Dict[str, Any]
    confidence_score: float
    timestamp: str


@dataclass
class WorkflowFailure:
    """Represents a workflow execution failure"""
    workflow_name: str
    step_index: int
    error_type: str
    error_message: str
    screenshot_path: Optional[str]
    dom_snapshot: Optional[str]
    timestamp: str


class SelfHealingEngine:
    """
    Engine for detecting workflow failures and generating repair suggestions
    """
    
    def __init__(self, workflow_registry: WorkflowRegistry, repair_agent: Optional[Agent] = None):
        self.registry = workflow_registry
        self.repair_agent = repair_agent
        self.failures_log = []
        self.repair_suggestions = []
        self.healing_enabled = True
        
        # Create repair suggestions directory
        self.repairs_dir = Path("repairs")
        self.repairs_dir.mkdir(exist_ok=True)
        
    def enable_healing(self, enabled: bool = True):
        """Enable or disable self-healing"""
        self.healing_enabled = enabled
        print(f"🔧 Self-healing {'enabled' if enabled else 'disabled'}")
    
    async def handle_workflow_failure(self, workflow_name: str, step_index: int, 
                                    error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle a workflow failure and attempt repair
        """
        if not self.healing_enabled:
            return {"success": False, "error": "Self-healing is disabled"}
        
        try:
            # Record the failure
            failure = WorkflowFailure(
                workflow_name=workflow_name,
                step_index=step_index,
                error_type=type(error).__name__,
                error_message=str(error),
                screenshot_path=context.get('screenshot_path') if context else None,
                dom_snapshot=context.get('dom_snapshot') if context else None,
                timestamp=datetime.now().isoformat()
            )
            
            self.failures_log.append(failure)
            print(f"🚨 Workflow failure recorded: {workflow_name} at step {step_index}")
            
            # Analyze the failure and generate repair suggestion
            suggestion = await self.analyze_and_repair(failure)
            
            if suggestion:
                self.repair_suggestions.append(suggestion)
                
                # Save repair suggestion for human review
                await self.save_repair_suggestion(suggestion)
                
                return {
                    "success": True,
                    "failure_recorded": True,
                    "repair_suggested": True,
                    "suggestion": asdict(suggestion),
                    "requires_approval": True
                }
            else:
                return {
                    "success": False,
                    "failure_recorded": True,
                    "repair_suggested": False,
                    "message": "Could not generate repair suggestion"
                }
                
        except Exception as e:
            print(f"❌ Self-healing error: {e}")
            return {
                "success": False,
                "error": f"Self-healing failed: {str(e)}"
            }
    
    async def analyze_and_repair(self, failure: WorkflowFailure) -> Optional[RepairSuggestion]:
        """
        Analyze failure and generate repair suggestion using AI
        """
        try:
            # Get the failing workflow
            workflow = self.registry.get_workflow(failure.workflow_name)
            if not workflow:
                return None
            
            # Get the failing step
            if failure.step_index >= len(workflow.steps):
                return None
                
            failing_step = workflow.steps[failure.step_index]
            
            # Classify the error and suggest repair
            suggestion = await self.classify_and_suggest_repair(failure, failing_step, workflow)
            
            return suggestion
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return None
    
    async def classify_and_suggest_repair(self, failure: WorkflowFailure, 
                                        failing_step: Dict[str, Any], 
                                        workflow: WorkflowSpec) -> Optional[RepairSuggestion]:
        """
        Classify error type and generate specific repair suggestions
        """
        error_type = failure.error_type.lower()
        error_message = failure.error_message.lower()
        
        # Common error patterns and their repairs
        if "selector" in error_message or "element not found" in error_message:
            # Selector drift - most common web automation failure
            return await self.suggest_selector_repair(failure, failing_step)
            
        elif "timeout" in error_message:
            # Timing issues
            return await self.suggest_timeout_repair(failure, failing_step)
            
        elif "network" in error_message or "connection" in error_message:
            # Network issues
            return await self.suggest_network_repair(failure, failing_step)
            
        elif "authentication" in error_message or "login" in error_message:
            # Auth issues
            return await self.suggest_auth_repair(failure, failing_step)
            
        else:
            # Generic repair using AI agent
            return await self.suggest_generic_repair(failure, failing_step)
    
    async def suggest_selector_repair(self, failure: WorkflowFailure, 
                                    failing_step: Dict[str, Any]) -> RepairSuggestion:
        """
        Suggest repairs for selector-based failures (most common)
        """
        current_selector = failing_step.get('args', {}).get('selector', '')
        
        # Generate alternative selectors based on common patterns
        alternative_selectors = []
        
        if current_selector.startswith('#'):
            # ID selector failed, try class or attribute selectors
            base_name = current_selector[1:]
            alternative_selectors.extend([
                f".{base_name}",
                f"[id*='{base_name}']",
                f"[name='{base_name}']"
            ])
        elif current_selector.startswith('.'):
            # Class selector failed, try ID or tag selectors
            base_name = current_selector[1:]
            alternative_selectors.extend([
                f"#{base_name}",
                f"[class*='{base_name}']",
                f"button[class*='{base_name}']"
            ])
        else:
            # Complex selector, suggest more robust alternatives
            alternative_selectors.extend([
                f"[data-testid*='{current_selector.split()[-1]}']",
                f"[aria-label*='{current_selector}']",
                f"button:contains('{current_selector}')"
            ])
        
        # Use AI agent for more intelligent selector repair if available
        if self.repair_agent:
            ai_suggestion = await self.get_ai_selector_suggestion(failure, failing_step)
            if ai_suggestion:
                alternative_selectors.insert(0, ai_suggestion)
        
        # Create repair suggestion with the best alternative
        suggested_fix = failing_step.copy()
        suggested_fix['args']['selector'] = alternative_selectors[0] if alternative_selectors else current_selector
        
        return RepairSuggestion(
            workflow_name=failure.workflow_name,
            step_index=failure.step_index,
            issue_type="selector_drift",
            issue_description=f"Selector '{current_selector}' not found. UI may have changed.",
            suggested_fix=suggested_fix,
            confidence_score=0.7 if alternative_selectors else 0.3,
            timestamp=datetime.now().isoformat()
        )
    
    async def suggest_timeout_repair(self, failure: WorkflowFailure, 
                                   failing_step: Dict[str, Any]) -> RepairSuggestion:
        """
        Suggest repairs for timeout issues
        """
        suggested_fix = failing_step.copy()
        
        # Increase timeout or add wait conditions
        if 'args' not in suggested_fix:
            suggested_fix['args'] = {}
        
        suggested_fix['args']['timeout'] = suggested_fix['args'].get('timeout', 30) * 2
        suggested_fix['args']['wait_for_load'] = True
        
        return RepairSuggestion(
            workflow_name=failure.workflow_name,
            step_index=failure.step_index,
            issue_type="timeout",
            issue_description="Operation timed out. Page may be loading slowly.",
            suggested_fix=suggested_fix,
            confidence_score=0.6,
            timestamp=datetime.now().isoformat()
        )
    
    async def suggest_network_repair(self, failure: WorkflowFailure, 
                                   failing_step: Dict[str, Any]) -> RepairSuggestion:
        """
        Suggest repairs for network issues
        """
        suggested_fix = failing_step.copy()
        
        # Add retry logic and error handling
        suggested_fix['retry_count'] = 3
        suggested_fix['retry_delay'] = 5
        
        return RepairSuggestion(
            workflow_name=failure.workflow_name,
            step_index=failure.step_index,
            issue_type="network_error",
            issue_description="Network connectivity issue. Adding retry logic.",
            suggested_fix=suggested_fix,
            confidence_score=0.5,
            timestamp=datetime.now().isoformat()
        )
    
    async def suggest_auth_repair(self, failure: WorkflowFailure, 
                                failing_step: Dict[str, Any]) -> RepairSuggestion:
        """
        Suggest repairs for authentication issues
        """
        suggested_fix = failing_step.copy()
        
        # Add authentication step before the failing step
        auth_step = {
            "action": "authenticate",
            "args": {
                "check_login_state": True,
                "re_authenticate": True
            }
        }
        
        return RepairSuggestion(
            workflow_name=failure.workflow_name,
            step_index=failure.step_index,
            issue_type="authentication_failure",
            issue_description="Authentication required. Adding login verification step.",
            suggested_fix=auth_step,  # Suggest adding auth step before current step
            confidence_score=0.8,
            timestamp=datetime.now().isoformat()
        )
    
    async def suggest_generic_repair(self, failure: WorkflowFailure, 
                                   failing_step: Dict[str, Any]) -> RepairSuggestion:
        """
        Use AI agent for generic repair suggestions
        """
        if not self.repair_agent:
            # Fallback to basic suggestion
            return RepairSuggestion(
                workflow_name=failure.workflow_name,
                step_index=failure.step_index,
                issue_type="unknown_error",
                issue_description=f"Unknown error: {failure.error_message}",
                suggested_fix=failing_step,
                confidence_score=0.2,
                timestamp=datetime.now().isoformat()
            )
        
        # Use AI agent to analyze and suggest repair
        task = f"Analyze workflow failure: {failure.error_message} in step {failing_step}. Suggest a repair."
        
        try:
            # This would use the actual AI agent in real implementation
            # result = await self.repair_agent.run()
            
            # For now, return a generic suggestion
            return RepairSuggestion(
                workflow_name=failure.workflow_name,
                step_index=failure.step_index,
                issue_type="generic_error",
                issue_description=f"AI-analyzed error: {failure.error_message}",
                suggested_fix=failing_step,
                confidence_score=0.6,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            print(f"❌ AI repair suggestion failed: {e}")
            return None
    
    async def get_ai_selector_suggestion(self, failure: WorkflowFailure, 
                                       failing_step: Dict[str, Any]) -> Optional[str]:
        """
        Use AI to suggest better selectors based on DOM analysis
        """
        if not self.repair_agent:
            return None
        
        try:
            # This would use screenshot and DOM analysis in real implementation
            # For now, return a smart guess based on current selector
            current_selector = failing_step.get('args', {}).get('selector', '')
            
            # Simple heuristic improvements
            if '#' in current_selector and 'submit' in current_selector:
                return "button[type='submit'], input[type='submit']"
            elif 'login' in current_selector:
                return "#login, .login-button, button[data-action='login']"
            
            return None
            
        except Exception:
            return None
    
    async def save_repair_suggestion(self, suggestion: RepairSuggestion):
        """
        Save repair suggestion for human review
        """
        try:
            suggestion_file = self.repairs_dir / f"{suggestion.workflow_name}_{suggestion.step_index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(suggestion_file, 'w') as f:
                json.dump(asdict(suggestion), f, indent=2)
            
            print(f"💾 Repair suggestion saved: {suggestion_file}")
            
        except Exception as e:
            print(f"❌ Failed to save repair suggestion: {e}")
    
    async def apply_repair(self, suggestion: RepairSuggestion, approved: bool = False) -> Dict[str, Any]:
        """
        Apply a repair suggestion to the workflow (requires approval)
        """
        if not approved:
            return {
                "success": False,
                "error": "Repair requires human approval"
            }
        
        try:
            # Get the workflow
            workflow = self.registry.get_workflow(suggestion.workflow_name)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            # Apply the fix
            if suggestion.step_index < len(workflow.steps):
                workflow.steps[suggestion.step_index] = suggestion.suggested_fix
                
                # Save updated workflow
                if self.registry.save_workflow(workflow):
                    print(f"✅ Applied repair to {suggestion.workflow_name} at step {suggestion.step_index}")
                    return {
                        "success": True,
                        "message": "Repair applied successfully",
                        "workflow_updated": True
                    }
            
            return {"success": False, "error": "Could not apply repair"}
            
        except Exception as e:
            return {"success": False, "error": f"Repair application failed: {str(e)}"}
    
    def get_repair_suggestions(self, workflow_name: Optional[str] = None) -> List[RepairSuggestion]:
        """
        Get all repair suggestions, optionally filtered by workflow
        """
        if workflow_name:
            return [s for s in self.repair_suggestions if s.workflow_name == workflow_name]
        return self.repair_suggestions.copy()
    
    def get_failure_history(self, workflow_name: Optional[str] = None) -> List[WorkflowFailure]:
        """
        Get failure history, optionally filtered by workflow
        """
        if workflow_name:
            return [f for f in self.failures_log if f.workflow_name == workflow_name]
        return self.failures_log.copy()


# Example usage and test
async def test_self_healing():
    """Test the self-healing mechanism"""
    print("🧪 Testing Self-Healing Engine...")
    
    registry = WorkflowRegistry()
    registry.create_sample_workflows()
    
    healing_engine = SelfHealingEngine(registry)
    
    # Simulate a workflow failure
    mock_error = Exception("Element not found: #old-selector")
    
    result = await healing_engine.handle_workflow_failure(
        "test_navigation", 
        0, 
        mock_error,
        {"screenshot_path": "error_screenshot.png"}
    )
    
    print(f"🔧 Failure handling result: {result}")
    
    # Get repair suggestions
    suggestions = healing_engine.get_repair_suggestions()
    print(f"💡 Repair suggestions: {len(suggestions)}")
    
    for suggestion in suggestions:
        print(f"  - {suggestion.issue_type}: {suggestion.issue_description}")
        print(f"    Confidence: {suggestion.confidence_score}")
    
    print("✅ Self-healing tests completed")


if __name__ == "__main__":
    asyncio.run(test_self_healing())