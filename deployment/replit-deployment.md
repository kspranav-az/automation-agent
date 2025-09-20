# Replit Deployment Guide for Browser Automation System

Since Docker containerization is not supported in Replit, here are the deployment alternatives:

## Current Setup (Single Process)

The system is currently configured to run as a single Python process with all components integrated:

```bash
python main.py  # Runs the complete system
```

## Replit Deployment Options

### Option 1: Replit Autoscale Deployment (Recommended)

Best for stateless workflows that don't need persistent browser sessions:

```bash
# In replit.nix or using Replit's package manager
{
  deps = [
    "python3"
    "playwright"
    "chromium"
  ];
}
```

Deploy configuration:
- **Deployment Target**: Autoscale
- **Run Command**: `python main.py`
- **Build Command**: `pip install -r requirements.txt && playwright install chromium`

### Option 2: Replit VM Deployment

For stateful workflows that need persistent browser sessions:

```bash
# Configuration
{
  "deployment": {
    "target": "vm",
    "run": ["python", "main.py"],
    "build": ["pip", "install", "-r", "requirements.txt"]
  }
}
```

### Option 3: Multiple Replit Services

Split components across multiple Replit projects:

1. **MCP Server**: Core browser automation
2. **Router Service**: Prompt parsing and workflow routing  
3. **Dashboard**: Web interface for monitoring
4. **Workflow Registry**: Workflow storage and management

## Process Separation Alternative

Instead of Docker containers, use Python multiprocessing:

```python
# deployment/process_manager.py
import multiprocessing
import asyncio
from concurrent.futures import ProcessPoolExecutor

class ProcessManager:
    def __init__(self):
        self.processes = {}
    
    def start_mcp_server(self):
        """Run MCP server in separate process"""
        from src.mcp_server import MCPServer
        server = MCPServer()
        asyncio.run(server.run())
    
    def start_dashboard(self):
        """Run dashboard in separate process"""
        from src.web_dashboard import run_dashboard
        asyncio.run(run_dashboard())
    
    def start_all(self):
        """Start all services"""
        with ProcessPoolExecutor(max_workers=4) as executor:
            executor.submit(self.start_mcp_server)
            executor.submit(self.start_dashboard)
```

## Browser Alternatives

Since Playwright requires system dependencies, use these alternatives:

### Option 1: Browserless Integration

```python
# Use remote browser service
from browser_use import Agent, BrowserSession

browser_session = BrowserSession(
    cdp_url="wss://production-sfo.browserless.io?token={TOKEN}"
)

agent = Agent(
    task="Your automation task",
    llm=llm,
    browser_session=browser_session
)
```

### Option 2: Selenium Grid

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Use remote WebDriver
driver = webdriver.Remote(
    command_executor='http://selenium-hub:4444/wd/hub',
    options=options
)
```

## Environment Configuration

Set these environment variables in Replit Secrets:

```bash
OPENAI_API_KEY=your_openai_key
JIRA_USER=your_jira_username  
JIRA_PASS=your_jira_password
BROWSERLESS_TOKEN=your_browserless_token  # If using Browserless
ENVIRONMENT=production
BROWSER_HEADLESS=true
```

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple Replit instances behind a load balancer
- Use Redis for shared state between instances
- Store workflows in external database (PostgreSQL)

### Vertical Scaling  
- Use Replit's VM deployment for more resources
- Optimize browser sessions and memory usage
- Implement connection pooling for databases

## Monitoring and Logging

Since Docker logging isn't available, use:

```python
import logging
from rich.logging import RichHandler

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler()]
)
```

## Security Best Practices

1. **Secrets Management**: Use Replit Secrets for all API keys
2. **Domain Allowlists**: Restrict browser automation to approved domains
3. **Rate Limiting**: Implement request throttling
4. **Audit Logging**: Log all workflow executions
5. **Input Validation**: Sanitize all user inputs

## Production Readiness Checklist

- [ ] Environment variables configured
- [ ] Browser dependencies installed
- [ ] Workflow validation tests pass
- [ ] Error handling and recovery implemented  
- [ ] Monitoring and alerting configured
- [ ] Security controls in place
- [ ] Performance optimization complete
- [ ] Backup and recovery procedures documented