# Browser Automation Workflow System

## Overview

This is a comprehensive browser automation platform built around the Model Context Protocol (MCP) that enables corporate users to automate SaaS workflows through natural language prompts. The system combines pre-recorded workflows with intelligent AI agents to handle complex browser-based tasks. Key features include workflow recording and management, intelligent routing between workflows and agents, self-healing capabilities for UI changes, and a web dashboard for monitoring and administration.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**MCP Server Architecture**
- Built on the browser-use library as the backbone for browser automation
- Exposes browser actions (navigate, click, type, extract) and workflow operations as RPC-style endpoints
- Containerized design serving as the main entry point for all services
- Handles sensitive data masking and logging for security compliance

**Workflow Management System**
- Workflows stored as versioned YAML/JSON specifications with parameterized inputs
- Each workflow contains deterministic steps, variable definitions, and metadata
- Domain-specific constraints and sensitive data flags for security
- Version control and approval mechanisms for workflow updates

**Intelligent Router (Planner-Executor)**
- Parses natural language prompts to identify target site, intent, and variables
- Routes requests to existing workflows when available
- Falls back to AI browser agents when no suitable workflow exists
- Continuously improves by learning from agent executions and creating new workflows

**Self-Healing Engine**
- Detects UI selector drift and workflow failures at runtime
- Uses AI agents with DOM analysis and screenshot reasoning to propose fixes
- Requires human approval before committing workflow repairs
- Maintains audit trails of all healing activities

**Domain Tools System**
- Modular adapters that inject domain-specific logic into workflows
- Example: Jira tool with specialized login handling and export capabilities
- Built-in security constraints for allowed domains and required permissions
- Designed for easy extension to new SaaS platforms

**Web Dashboard Interface**
- Real-time monitoring of workflow executions and system status
- Workflow management with recording, editing, and approval workflows
- Self-healing notifications and repair suggestion reviews
- User management with role-based access control

### Security Architecture

**Sensitive Data Handling**
- Secrets managed outside of prompts and logs through environment variables
- Data masking at the MCP server level for logging and UI display
- Domain tools flag sensitive operations and require appropriate permissions
- Role-based access control for different user types (Admin, Operator, Approver, User)

**Validation and Constraints**
- Domain allowlists for security-critical tools
- Required permission checks before executing sensitive operations
- Audit trails for all workflow changes and executions

### Deployment Architecture

**Containerization Strategy**
- MCP server, router, domain tools, and CI runner all containerized
- Supports both local development and remote production deployments
- Scalable browser concurrency for handling multiple concurrent workflows

**CI/CD Integration**
- Automated workflow testing with shared browser configurations
- Early detection of selector drift and workflow failures
- Guardrails prevent deployment of broken workflows

## External Dependencies

### Browser Automation
- **browser-use**: Core library providing the browser automation engine and Agent class
- **Playwright**: Underlying browser drivers (via browser-use)
- **OpenAI API**: Powers AI agents for intelligent parsing and browser automation

### Web Framework and UI
- **FastAPI**: Web framework for the dashboard server and API endpoints
- **WebSockets**: Real-time communication for live execution monitoring
- **Jinja2**: Template engine for web dashboard rendering
- **Rich**: Enhanced CLI interface with progress indicators and formatting

### AI and Machine Learning
- **OpenAI GPT-5**: Latest model for intelligent prompt parsing and workflow automation
- **Natural Language Processing**: AI-powered intent recognition and variable extraction
- **Browser Agent Intelligence**: AI-driven browser automation with visual understanding

### Data Storage and Configuration
- **YAML**: Workflow specification storage format
- **JSON**: Alternative format for workflow specs and API responses
- **File System**: Primary storage for workflows and execution logs

### Development and CLI Tools
- **Click**: Command-line interface framework
- **asyncio**: Asynchronous programming support for concurrent operations
- **uvicorn**: ASGI server for serving the web dashboard

### Security and Environment
- **Replit Secrets**: Secure API key management (OPENAI_API_KEY, JIRA credentials)
- **Environment Variables**: Runtime configuration and credential access
- **Domain Allowlists**: Security constraints for browser automation targets

### Deployment and Scaling
- **Replit Autoscale**: Recommended deployment target for stateless workflows
- **Replit VM**: Alternative for stateful browser sessions
- **Process Separation**: Python multiprocessing instead of Docker containers
- **Browserless.io**: Optional remote browser service for enhanced reliability

### Optional External Services
- **Jira/Atlassian**: Example domain integration with allowlisted domains
- **External SaaS platforms**: Extensible to other corporate tools through domain adapters
- **Remote Browser Services**: Browserless, Selenium Grid alternatives