# Docker MCP Gateway Setup

## Overview

This guide explains how to configure the Model Context Protocol (MCP) Docker Gateway for use with Docker Desktop running locally.

## Configuration

The MCP Docker Gateway configuration is located at `~/.cursor/mcp.json`.

### Standard Configuration

```json
{
  "mcpServers": {
    "docker": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      },
      "enabled": true
    }
  }
}
```

### WSL2 with Docker Desktop

For WSL2 environments, the Docker socket is typically available at `/var/run/docker.sock`. If you encounter connection issues, verify Docker Desktop is running and the socket is accessible:

```bash
# Check if Docker socket exists
ls -la /var/run/docker.sock

# Test Docker connection
docker ps
```

### Alternative Configuration (if needed)

If the standard socket path doesn't work, you can try:

```json
{
  "mcpServers": {
    "docker": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "env": {
        "DOCKER_HOST": "tcp://localhost:2375"
      },
      "enabled": true
    }
  }
}
```

**Note**: This requires Docker Desktop to expose the TCP port (not recommended for security reasons).

## Setup Steps

1. **Ensure Docker Desktop is Running**

   ```bash
   docker ps
   ```

2. **Verify Docker MCP Gateway is Available**

   ```bash
   docker mcp gateway --help
   ```

3. **Copy Configuration**
   - The configuration file is located at `~/.cursor/mcp.json`
   - A reference example is available at `mcp.json.example` in the project root

4. **Restart Cursor**
   - After updating `mcp.json`, restart Cursor to load the new configuration

## Multiple MCP Servers

If you need to use multiple MCP servers (e.g., Docker Gateway + Playwright), you can combine them:

```json
{
  "mcpServers": {
    "docker": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      },
      "enabled": true
    },
    "playwright": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-playwright"],
      "env": {
        "NODE_ENV": "development"
      },
      "enabled": true
    }
  }
}
```

## Troubleshooting

### Docker Desktop Not Running

**Error**: `Docker Desktop is not running` or gateway not loading

**Solution**:

1. **Start Docker Desktop** - The MCP Gateway requires Docker Desktop to be running
2. **Verify Docker is running**:
   ```bash
   docker ps
   ```
3. **Check Docker Desktop WSL2 Integration**:
   - Open Docker Desktop
   - Go to Settings → Resources → WSL Integration
   - Ensure your WSL distribution is enabled
   - Click "Apply & Restart"

### Docker Gateway Not Available

**Error**: `docker mcp gateway` command not found

**Solution**: Ensure you have Docker Desktop with MCP Toolkit installed. The MCP Gateway is part of Docker Desktop's MCP Toolkit feature.

### Connection Refused

**Error**: Cannot connect to Docker daemon

**Solutions**:

1. Verify Docker Desktop is running
2. Check Docker socket permissions:
   ```bash
   ls -la /var/run/docker.sock
   sudo chmod 666 /var/run/docker.sock  # If needed (not recommended for production)
   ```
3. Verify your user is in the `docker` group:
   ```bash
   groups | grep docker
   ```

### WSL2 Specific Issues

If running in WSL2:

1. Ensure Docker Desktop is configured to use WSL2 integration
2. Check Docker Desktop settings: Settings → Resources → WSL Integration
3. Verify the WSL distribution is enabled

## Testing the Configuration

After setup, test the Docker MCP Gateway:

```bash
# Test Docker connection
docker ps

# Test MCP Gateway
docker mcp gateway run --help
```

## Additional Resources

- [Docker MCP Toolkit Documentation](https://docs.docker.com/desktop/mcp/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Cursor MCP Configuration](https://docs.cursor.com/mcp)
