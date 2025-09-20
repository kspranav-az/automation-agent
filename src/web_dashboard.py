#!/usr/bin/env python3
"""
Web Dashboard for monitoring workflow executions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from mcp_server import MCPServer
from workflow_registry import WorkflowRegistry
from router import Router
from self_healing import SelfHealingEngine


class DashboardServer:
    """
    Web dashboard server for monitoring and managing workflows
    """
    
    def __init__(self):
        self.app = FastAPI(title="Browser Automation Dashboard")
        self.registry = WorkflowRegistry()
        self.mcp_server = MCPServer()
        self.router = Router()
        self.healing_engine = SelfHealingEngine(self.registry)
        
        # WebSocket connections for real-time updates
        self.active_connections: List[WebSocket] = []
        
        # Execution history
        self.execution_history = []
        
        # Setup routes
        self.setup_routes()
        
        # Create templates directory
        self.templates_dir = Path("templates")
        self.templates_dir.mkdir(exist_ok=True)
        self.templates = Jinja2Templates(directory="templates")
        
        # Create static files directory
        self.static_dir = Path("static")
        self.static_dir.mkdir(exist_ok=True)
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Create dashboard templates
        self.create_templates()
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                "page_title": "Browser Automation Dashboard"
            })
        
        @self.app.get("/api/workflows")
        async def get_workflows():
            workflows = self.registry.list_workflows()
            return JSONResponse({"workflows": workflows})
        
        @self.app.get("/api/workflow/{workflow_name}")
        async def get_workflow(workflow_name: str):
            workflow = self.registry.get_workflow(workflow_name)
            if workflow:
                return JSONResponse({
                    "workflow": {
                        "name": workflow.name,
                        "version": workflow.version,
                        "domain": workflow.domain,
                        "steps": workflow.steps,
                        "variables": workflow.variables,
                        "metadata": workflow.metadata
                    }
                })
            return JSONResponse({"error": "Workflow not found"}, status_code=404)
        
        @self.app.post("/api/workflow/{workflow_name}/run")
        async def run_workflow(workflow_name: str, variables: Dict[str, Any] = None):
            try:
                result = await self.mcp_server.run_workflow(workflow_name, variables or {})
                
                # Record execution
                execution_record = {
                    "workflow_name": workflow_name,
                    "timestamp": datetime.now().isoformat(),
                    "variables": variables,
                    "result": result,
                    "status": "success" if result.get("success") else "failed"
                }
                self.execution_history.append(execution_record)
                
                # Broadcast to WebSocket clients
                await self.broadcast_execution_update(execution_record)
                
                return JSONResponse(result)
            except Exception as e:
                error_record = {
                    "workflow_name": workflow_name,
                    "timestamp": datetime.now().isoformat(),
                    "variables": variables,
                    "error": str(e),
                    "status": "error"
                }
                self.execution_history.append(error_record)
                await self.broadcast_execution_update(error_record)
                
                return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        
        @self.app.post("/api/prompt")
        async def handle_prompt(prompt_data: Dict[str, str]):
            try:
                prompt = prompt_data.get("prompt", "")
                result = await self.router.handle_prompt(prompt)
                
                # Record execution
                execution_record = {
                    "prompt": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "result": result,
                    "status": "success" if result.get("success") else "failed",
                    "source": result.get("source", "unknown")
                }
                self.execution_history.append(execution_record)
                await self.broadcast_execution_update(execution_record)
                
                return JSONResponse(result)
            except Exception as e:
                return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        
        @self.app.get("/api/executions")
        async def get_executions(limit: int = 50):
            recent_executions = self.execution_history[-limit:] if self.execution_history else []
            return JSONResponse({"executions": recent_executions})
        
        @self.app.get("/api/repair-suggestions")
        async def get_repair_suggestions():
            suggestions = self.healing_engine.get_repair_suggestions()
            return JSONResponse({
                "suggestions": [
                    {
                        "workflow_name": s.workflow_name,
                        "step_index": s.step_index,
                        "issue_type": s.issue_type,
                        "issue_description": s.issue_description,
                        "confidence_score": s.confidence_score,
                        "timestamp": s.timestamp
                    }
                    for s in suggestions
                ]
            })
        
        @self.app.post("/api/repair-suggestions/{suggestion_id}/apply")
        async def apply_repair_suggestion(suggestion_id: int, approval_data: Dict[str, bool]):
            try:
                approved = approval_data.get("approved", False)
                suggestions = self.healing_engine.get_repair_suggestions()
                
                if 0 <= suggestion_id < len(suggestions):
                    suggestion = suggestions[suggestion_id]
                    result = await self.healing_engine.apply_repair(suggestion, approved)
                    return JSONResponse(result)
                
                return JSONResponse({"success": False, "error": "Suggestion not found"}, status_code=404)
            except Exception as e:
                return JSONResponse({"success": False, "error": str(e)}, status_code=500)
        
        @self.app.get("/api/stats")
        async def get_dashboard_stats():
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            
            recent_executions = [
                e for e in self.execution_history 
                if datetime.fromisoformat(e["timestamp"]) >= last_24h
            ]
            
            success_count = sum(1 for e in recent_executions if e.get("status") == "success")
            failed_count = sum(1 for e in recent_executions if e.get("status") in ["failed", "error"])
            
            return JSONResponse({
                "total_workflows": len(self.registry.workflows),
                "total_executions": len(self.execution_history),
                "executions_24h": len(recent_executions),
                "success_rate_24h": (success_count / len(recent_executions) * 100) if recent_executions else 0,
                "failed_executions_24h": failed_count,
                "repair_suggestions": len(self.healing_engine.get_repair_suggestions())
            })
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            try:
                while True:
                    # Keep connection alive and handle messages
                    data = await websocket.receive_text()
                    # Echo back for now
                    await websocket.send_text(f"Echo: {data}")
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
    
    async def broadcast_execution_update(self, execution_record: Dict[str, Any]):
        """Broadcast execution updates to all connected WebSocket clients"""
        message = json.dumps({
            "type": "execution_update",
            "data": execution_record
        })
        
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)
    
    def create_templates(self):
        """Create HTML templates for the dashboard"""
        
        dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border: 1px solid #e1e5e9;
        }
        .card h3 {
            margin: 0 0 1rem 0;
            color: #333;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }
        .stat-item {
            text-align: center;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 0.9rem;
        }
        .workflow-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .workflow-item {
            padding: 0.75rem;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: between;
            align-items: center;
        }
        .workflow-item:last-child {
            border-bottom: none;
        }
        .btn {
            padding: 0.5rem 1rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .btn:hover {
            background: #5a67d8;
        }
        .btn-small {
            padding: 0.25rem 0.5rem;
            font-size: 0.8rem;
        }
        .execution-log {
            max-height: 400px;
            overflow-y: auto;
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9rem;
        }
        .log-entry {
            margin-bottom: 0.5rem;
            padding: 0.5rem;
            background: white;
            border-radius: 3px;
            border-left: 3px solid #667eea;
        }
        .log-success { border-left-color: #48bb78; }
        .log-error { border-left-color: #e53e3e; }
        .prompt-input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
            margin-bottom: 1rem;
        }
        .status {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-success { background: #c6f6d5; color: #22543d; }
        .status-error { background: #fed7d7; color: #742a2a; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 Browser Automation Dashboard</h1>
        <p>Monitor and manage your workflow executions</p>
    </div>

    <div class="container">
        <div id="stats-grid" class="grid">
            <div class="card">
                <h3>📊 System Statistics</h3>
                <div id="stats-container" class="stats">
                    <div class="stat-item">
                        <div class="stat-number" id="total-workflows">-</div>
                        <div class="stat-label">Total Workflows</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="executions-24h">-</div>
                        <div class="stat-label">Executions (24h)</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="success-rate">-</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="repair-suggestions">-</div>
                        <div class="stat-label">Pending Repairs</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3>🤖 Quick Execute</h3>
                <input type="text" id="prompt-input" class="prompt-input" 
                       placeholder="Enter a natural language prompt...">
                <button onclick="executePrompt()" class="btn">Execute</button>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>📋 Available Workflows</h3>
                <ul id="workflows-list" class="workflow-list">
                    <li>Loading workflows...</li>
                </ul>
            </div>

            <div class="card">
                <h3>📈 Recent Executions</h3>
                <div id="execution-log" class="execution-log">
                    <div class="log-entry">Loading execution history...</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>🔧 Repair Suggestions</h3>
            <div id="repair-suggestions">
                <p>Loading repair suggestions...</p>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'execution_update') {
                addExecutionLogEntry(data.data);
                updateStats();
            }
        };

        // Load initial data
        document.addEventListener('DOMContentLoaded', function() {
            updateStats();
            loadWorkflows();
            loadExecutions();
            loadRepairSuggestions();
        });

        async function updateStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('total-workflows').textContent = stats.total_workflows || 0;
                document.getElementById('executions-24h').textContent = stats.executions_24h || 0;
                document.getElementById('success-rate').textContent = (stats.success_rate_24h || 0).toFixed(1) + '%';
                document.getElementById('repair-suggestions').textContent = stats.repair_suggestions || 0;
            } catch (error) {
                console.error('Failed to update stats:', error);
            }
        }

        async function loadWorkflows() {
            try {
                const response = await fetch('/api/workflows');
                const data = await response.json();
                
                const list = document.getElementById('workflows-list');
                list.innerHTML = '';
                
                data.workflows.forEach(workflow => {
                    const li = document.createElement('li');
                    li.className = 'workflow-item';
                    li.innerHTML = `
                        <div>
                            <strong>${workflow.name}</strong> (v${workflow.version})
                            <br><small>${workflow.description || 'No description'}</small>
                        </div>
                        <button onclick="runWorkflow('${workflow.name}')" class="btn btn-small">Run</button>
                    `;
                    list.appendChild(li);
                });
            } catch (error) {
                console.error('Failed to load workflows:', error);
            }
        }

        async function loadExecutions() {
            try {
                const response = await fetch('/api/executions');
                const data = await response.json();
                
                const log = document.getElementById('execution-log');
                log.innerHTML = '';
                
                data.executions.slice(-10).forEach(execution => {
                    addExecutionLogEntry(execution);
                });
            } catch (error) {
                console.error('Failed to load executions:', error);
            }
        }

        async function loadRepairSuggestions() {
            try {
                const response = await fetch('/api/repair-suggestions');
                const data = await response.json();
                
                const container = document.getElementById('repair-suggestions');
                
                if (data.suggestions.length === 0) {
                    container.innerHTML = '<p>✅ No repair suggestions - all workflows are healthy!</p>';
                    return;
                }
                
                container.innerHTML = data.suggestions.map((suggestion, index) => `
                    <div class="log-entry">
                        <strong>${suggestion.workflow_name}</strong> - Step ${suggestion.step_index}
                        <br><small>${suggestion.issue_description}</small>
                        <br><span class="status">Confidence: ${(suggestion.confidence_score * 100).toFixed(0)}%</span>
                        <button onclick="applyRepair(${index})" class="btn btn-small" style="margin-left: 1rem;">Apply Fix</button>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Failed to load repair suggestions:', error);
            }
        }

        function addExecutionLogEntry(execution) {
            const log = document.getElementById('execution-log');
            const entry = document.createElement('div');
            
            const status = execution.status || 'unknown';
            const statusClass = status === 'success' ? 'log-success' : 'log-error';
            
            entry.className = `log-entry ${statusClass}`;
            entry.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${execution.workflow_name || execution.prompt || 'Unknown'}</strong>
                        <span class="status status-${status === 'success' ? 'success' : 'error'}">${status}</span>
                    </div>
                    <small>${new Date(execution.timestamp).toLocaleTimeString()}</small>
                </div>
            `;
            
            log.insertBefore(entry, log.firstChild);
            
            // Keep only last 20 entries
            while (log.children.length > 20) {
                log.removeChild(log.lastChild);
            }
        }

        async function executePrompt() {
            const prompt = document.getElementById('prompt-input').value;
            if (!prompt) return;
            
            try {
                const response = await fetch('/api/prompt', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt})
                });
                
                const result = await response.json();
                document.getElementById('prompt-input').value = '';
                
                // The WebSocket will handle the UI update
                if (!result.success) {
                    alert('Execution failed: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Failed to execute prompt: ' + error.message);
            }
        }

        async function runWorkflow(workflowName) {
            try {
                const response = await fetch(`/api/workflow/${workflowName}/run`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    alert('Workflow failed: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Failed to run workflow: ' + error.message);
            }
        }

        async function applyRepair(suggestionIndex) {
            if (!confirm('Are you sure you want to apply this repair? This will modify the workflow.')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/repair-suggestions/${suggestionIndex}/apply`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({approved: true})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('Repair applied successfully!');
                    loadRepairSuggestions(); // Refresh the list
                } else {
                    alert('Failed to apply repair: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Failed to apply repair: ' + error.message);
            }
        }

        // Auto-refresh every 30 seconds
        setInterval(() => {
            updateStats();
            loadExecutions();
            loadRepairSuggestions();
        }, 30000);
    </script>
</body>
</html>
        """
        
        # Write the dashboard template
        with open(self.templates_dir / "dashboard.html", "w") as f:
            f.write(dashboard_html)
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the dashboard server"""
        print(f"🌐 Starting dashboard server at http://{host}:{port}")
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


# Main function to run the dashboard
async def run_dashboard():
    """Run the web dashboard"""
    dashboard = DashboardServer()
    
    # Initialize sample data
    dashboard.registry.create_sample_workflows()
    await dashboard.mcp_server.initialize_browser()
    
    print("✅ Dashboard initialized with sample data")
    
    # Start the server
    await dashboard.start_server(port=8000)


if __name__ == "__main__":
    asyncio.run(run_dashboard())