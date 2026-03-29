# Gemini CLI - MCP/OpenAI Bridge Server

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![npm version](https://img.shields.io/npm/v/@intelligentinternet/gemini-cli-mcp-openai-bridge)](https://www.npmjs.com/package/@intelligentinternet/gemini-cli-mcp-openai-bridge)

[中文文档](https://github.com/Intelligent-Internet/gemini-cli-common-bridge/blob/main/README.zh.md)

> **🎉 Built on Open Source Gemini CLI - Thanks to Google!**  
> This project is built upon the open-source [Gemini CLI](https://github.com/google-gemini/gemini-cli) by Google. We appreciate Google's commitment to open source and their contribution to the developer community.

`@intelligentinternet/gemini-cli-mcp-openai-bridge` (or `gemini-cli-bridge`) is a versatile server application designed as a powerful extension to the `gemini-cli` ecosystem. It serves two primary roles:

1. **MCP Toolkit**: Exposes all built-in tools from `gemini-cli` (such as file system operations, web search powered by Gemini models, and web content understanding) through a unified MCP endpoint.
   - Can also connect to any number of external MCP servers (only allowed in YOLO mode or when specific tools are configured in `configured` mode).

2. **OpenAI-Compatible API Bridge**: Provides a fully compatible endpoint with the OpenAI Chat Completions API (`/v1/chat/completions`). This enables any third-party tool or application that supports the OpenAI API (such as [Open WebUI](https://github.com/open-webui/open-webui)) to seamlessly interact with the underlying Gemini models of `gemini-cli`.

## Features

- **Built on `gemini-cli`**: Directly built upon the core functionality of `gemini-cli`, ensuring deep integration with Gemini models.
- **Native `gemini-cli` Tools**: Exposes `gemini-cli`'s built-in tools through the MCP protocol.
- **External MCP Tool Aggregation**: Acts as an MCP hub, connecting and proxying tools from other tool servers (only in `yolo` mode or when specific tools are configured in `restricted` mode).
- **Full OpenAI API Compatibility**: Provides `/v1/chat/completions` and `/v1/models` endpoints with support for both streaming and non-streaming requests.
- **Flexible Model Configuration**: Allows configuring separate default LLM models for tool execution (such as web search summarization).
- **Inherited Configuration & Authentication**: Automatically uses the same settings and authentication state as the main `gemini-cli` tool, requiring no duplicate configuration.
- **Configurable Security Policies**: Implements MCP tool-based security model with `read-only`, `edit`, `configured`, and `yolo` modes to control tool execution.

## Prerequisites

- [Node.js](https://nodejs.org/) v18 or higher
- All dependencies and configuration required by [Gemini CLI](https://github.com/google-gemini/gemini-cli)
  - This project automatically installs `gemini-cli` as a submodule (from the official `gemini-cli` GitHub repository), so you don't need to install it separately.
  - If you already have `gemini-cli` installed, it will be overridden by this project's submodule version.

## Installation

```bash
npm install -g @intelligentinternet/gemini-cli-mcp-openai-bridge
```

## Usage

**Security Warning**: This bridge server **does not ask for user confirmation** when invoking tools.
- For your safety, the MCP bridge service defaults to `read-only` mode and will not bridge other MCP services you have configured in settings.json.
- This project does not provide a runtime sandbox. If you wish to configure a `YOLO` security policy, please ensure your environment cannot be damaged by accidentally executed shell commands (strongly recommended to run in a container).

### 1. Start the Server

Run the command in your terminal. You can use command-line arguments to override default settings.

```bash
# Start server on all network interfaces at port 9000 with debug mode enabled
gemini-cli-bridge --host=127.0.0.1 --port=9000 --debug

# Use a faster model for tool calls and load internal GEMINI.md prompts
gemini-cli-bridge --tools-model=gemini-2.5-flash --use-internal-prompt
```

After the server starts successfully, you will see output similar to:

```
[BRIDGE-SERVER] [INFO] Starting Gemini CLI Bridge (MCP + OPENAI)...
[BRIDGE-SERVER] [INFO] Server running {
  port: 8765,
  host: '127.0.0.1',
  mcpUrl: 'http://127.0.0.1:8765/mcp',
  openAIUrl: 'http://127.0.0.1:8765/v1'
}
```

### 2. Build from Source (Developers)

```bash
git clone https://github.com/Intelligent-Internet/gemini-cli-common-bridge.git
cd gemini-cli-common-bridge
npm install
npm run build
npm run start
```

## Authentication

This bridge server **does not manage its own authentication credentials**. It shares the exact same authentication mechanism as the main `gemini-cli` tool to ensure seamless and secure operation.

- **Cached Credentials**: If you have already logged in through `gemini-cli`'s interactive flow, the bridge server will automatically use the cached credentials.
- **Environment Variables**: The server will automatically look for and use environment variables such as `GEMINI_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS`.

As long as your `gemini-cli` is configured and working properly, this bridge server will automatically gain authorization.

## 🛡️ Security Model & Configuration

One of the core designs of `gemini-cli-bridge` is to provide a basic but essential security model to protect your local environment from accidental or malicious operations. Security is crucial when connecting powerful AI models with local tools (such as file system access and shell commands).

**By default, the server runs in the most secure `read-only` mode.**

### Security Modes

You can set the server's security level through the `--mode` command-line argument or by configuring `securityPolicy.mode` in the `settings.json` file. Command-line arguments take precedence.

Four modes are available:

#### 1. `read-only` (Read-Only Mode - **Default**)

This is the most secure and default mode. If you don't make any security configuration, the server will run in this mode.

- ✅ **Allowed**: Only built-in tools that do not modify the local file system or execute arbitrary code. Examples: `read_file`, `list_directory`, `glob`, `google_web_search`, `web_fetch`.
- ❌ **Forbidden**: All tools with write permissions (such as `write_file`, `replace`), `run_shell_command`, and all tools from external MCP proxies.

**Use Case**: When you only need the AI model to read local files, gather information, or perform web searches, this is the ideal choice.

#### 2. `edit` (Edit Mode)

This mode is designed for local code generation and file editing tasks, providing a balance between functionality and security.

- ✅ **Allowed**: All built-in read-only tools, plus tools with file writing and modification permissions, such as `write_file` and `replace`.
- ❌ **Forbidden**: `run_shell_command` (prevents executing arbitrary commands) and all external MCP proxy tools (prevents accidental network interactions).

**Use Case**: For use in trusted local development environments for development tasks such as code refactoring and generating new files.

#### 3. `configured` (Configured Mode)

This mode gives you complete control over security through your `settings.json` file. Its behavior is entirely defined by your `securityPolicy` configuration block.

- **Behavior**:
  - **Tools**: Only tools explicitly listed in the `allowedTools` array will be enabled.
  - **Shell Commands**: If `run_shell_command` is in `allowedTools`, its executable commands will be strictly limited by the `allow` and `deny` lists in `shellCommandPolicy`.
  - **MCP Proxy**: By default, all MCP proxy tools are disabled. You must use the `--allow-mcp-proxy` command-line argument to explicitly enable them.

**Use Case**: For advanced users or scenarios requiring fine-grained permission management of specific tools and commands in controlled environments.

#### 4. `yolo` (YOLO Mode - **Highly Dangerous**)

This mode disables almost all built-in security guardrails.

- ✅ **Allowed**: All **built-in** tools, including `run_shell_command` without any restrictions.
- **MCP Proxy**: Disabled by default, but can be enabled with the `--allow-mcp-proxy` parameter.

> **⚠️ Extreme Danger Warning**: `yolo` mode gives the AI model the ability to execute any command on your system, including destructive operations like `rm -rf /`. **Never** use this mode in production environments or any untrusted network environments.

### External Tool Security (MCP Proxy)

`bridge-server` can connect to external MCP (Model-Context Protocol) servers, known as "MCP proxies," which can provide additional tools (e.g., connecting to internal Jira, operating GitHub, or generating images).

- **Disabled by Default**: For security, all MCP proxy tools are **completely disabled** in `read-only` and `edit` modes.
- **Explicit Enablement**: You can only enable all discovered MCP proxy tools in `configured` or `yolo` modes by adding the `--allow-mcp-proxy` command-line argument.

> **🔴 MCP Proxy Warning**: Enabling MCP proxy means `bridge-server` will allow the AI model to communicate with third-party services through these proxies. Please ensure you completely trust the source of each configured MCP server and the tools they provide.

### Mandatory Safety Confirmation

To prevent accidental enablement of high-risk modes, `bridge-server` has built-in mandatory interactive confirmation mechanisms.

- **Trigger Conditions**:
  1. Starting in `yolo` mode.
  2. Using the `--allow-mcp-proxy` parameter at startup.
- **Confirmation Process**: The server will pause at startup and require you to type `YES` (all uppercase) in the console and press Enter. If the input doesn't match, the server will safely exit.
- **Skip Confirmation**: In fully automated scripts or when you fully understand the risks, you can use the `--i-know-what-i-am-doing` command-line argument to skip this interactive confirmation.

### File Operation Scope

All built-in file system tools (such as `read_file`, `write_file`, `list_directory`, etc.) are strictly restricted to operate within **one** directory.

- **Default Scope**: By default, this operation scope is the **current working directory where you start `bridge-server`**.
- **Custom Scope**: You can explicitly specify the operation scope using the `--target-dir /path/to/your/project` command-line argument.

This mechanism effectively prevents the AI agent from accidentally reading or modifying any files outside your project directory.

### Listen Host

The server defaults to listening on `127.0.0.1`. You can modify this setting through the `--host` command-line argument or the `GEMINI_MCP_HOST` environment variable.

If you want the server to listen on all network interfaces, you can set it to `0.0.0.0`. (Do not use this setting in production environments unless you have additional network security measures or are running in a container network)

Note: In production environments, it is **strongly recommended** to use firewalls or other network security measures to restrict access to this port. **This service does not provide any authentication, authorization, or auditing features**.

## Full Configuration

You can configure the server's behavior through configuration files, command-line arguments, and environment variables.

### Command-Line Arguments & Environment Variables

Arguments take precedence over environment variables and configuration files.

| Parameter | Alias | Environment Variable | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--host` | `-h` | - | `127.0.0.1` | Host address for the server to listen on. Use `0.0.0.0` to listen on all network interfaces. |
| `--port` | `-p` | `GEMINI_MCP_PORT` | `8765` | Port for the server to listen on. |
| `--tools-model` | - | `GEMINI_TOOLS_DEFAULT_MODEL` | `gemini-2.5-flash` | Default model for tool execution. |
| `--use-internal-prompt` | - | - | `false` | If set, loads the `GEMINI.md` file and default system prompts as context. (Client-provided system prompts will be treated as the first user prompt) |
| `--debug` | - | - | `false` | Enable verbose debug logging. |
| `--mode` | - | - | `read-only` | Set the server's security mode. Options: `read-only`, `edit`, `configured`, `yolo`. |
| `--allow-mcp-proxy` | - | - | `false` | Enable MCP proxy tools in `configured` or `yolo` modes. |
| `--i-know-what-i-am-doing` | - | - | `false` | Skip safety confirmation for high-risk modes. Use only when you fully understand the risks. |
| `--target-dir` | - | - | Current working directory | Set the root directory for file operations. |
| `--help` | `?` | - | - | Show help information. |

### Configuration File (`.gemini/settings.json`)

**Security Policy (`securityPolicy`)** is the most important configuration item. You can configure it in the user directory (`~/.gemini/settings.json`) or workspace directory (`.gemini/settings.json`).

When mode is `configured`, the server will strictly follow this configuration; command-line arguments will override the `mode` in this setting.

```json
// .gemini/settings.json example
{
  "securityPolicy": {
    "mode": "configured",
    "allowedTools": [
      "read_file",
      "list_directory",
      "google_web_search",
      "run_shell_command"
    ],
    "shellCommandPolicy": {
      "allow": ["ls -l", "git status", "npm run test"],
      "deny": ["rm", "sudo", "docker"]
    }
  },
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PAT}", "ghcr.io/github/github-mcp-server"],
      "trust": true
    }
  }
}
```

- **`securityPolicy`**: Controls the server's security boundaries. **If this item is missing and no explicit command-line arguments are set, the server will default to the most secure `read-only` mode**.
  - **`mode`**:
    - `"read-only"` (default): Only allows execution of read-only tools (such as `read_file`, `list_directory`).
    - `"edit"`: Allows file editing tools but forbids `run_shell_command`.
    - `"configured"`: Recommended mode. Only allows tools explicitly listed in the `allowedTools` array.
    - `"yolo"`: Most insecure mode. Allows all tools without any restrictions.
  - **`allowedTools`**: In `configured` mode, defines which tools (including those from external MCP servers) can be registered and called.
  - **`shellCommandPolicy`**: Provides fine-grained control over the `run_shell_command` tool. `deny` rules take precedence over `allow` rules.

- **`mcpServers`**: Configures external MCP servers to extend the bridge's tool capabilities.

- Other configuration items can refer to the [Gemini CLI Configuration Documentation](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md).

### `settings.json` Configuration Support in `bridge-server`

| Configuration Item | Support Status | Reason & Description |
| :--- | :--- | :--- |
| **`securityPolicy`** | ✅ **Fully Supported** | **Core feature**. This is the main security mechanism added by `bridge-server` to control tool access permissions and command execution. |
| **`coreTools`** | ✅ **Fully Supported** | Directly affects which built-in tools are registered during `ToolRegistry` initialization, controlling the tool set exposed through MCP. |
| **`excludeTools`** | ✅ **Fully Supported** | Similar to `coreTools`, used to remove specific tools from the available tool set, part of the security policy. |
| **`toolDiscoveryCommand`** | ✅ **Fully Supported** | The server will execute this command to discover custom tools and expose them through the MCP protocol. |
| **`toolCallCommand`** | ✅ **Fully Supported** | When calling a discovered custom tool through MCP, the server will execute this command. |
| **`mcpServers`** | ✅ **Fully Supported** | The server will attempt to connect and integrate all external tool servers configured in `mcpServers`. |
| **`selectedAuthType`** | ✅ **Fully Supported** | **Key configuration**. Determines how `bridge-server` authenticates with Google APIs. |
| **`fileFiltering`** | ✅ **Fully Supported** | File tools used internally by `bridge-server` (such as `glob`) will follow rules like `respectGitIgnore` in this configuration. |
| **`telemetry`** | ✅ **Fully Supported** | The server will initialize and configure OpenTelemetry based on these settings for telemetry data collection. |
| **`usageStatisticsEnabled`** | ✅ **Fully Supported** | Controls whether to send anonymous usage statistics to Google. |
| **`contextFileName`** | 🟡 **Conditional Support** | Only effective when `bridge-server` is started with the `--use-internal-prompt` argument. |
| **`theme`** | ❌ **Not Supported** | `bridge-server` is a UI-less backend service with no visual themes. |
| **`autoAccept`** | ❌ **Not Relevant** | `bridge-server` is internally hard-coded to `YOLO` approval mode and never waits for interactive user confirmation. Its security is ensured by `securityPolicy`. |
| **`sandbox`** | ❌ **Not Supported** | `bridge-server` **does not create** sandboxes. It can only detect if it's already running in a sandbox created by other processes (such as `gemini-cli`). |
| **`checkpointing`** | ❌ **Not Supported** | This feature is tightly coupled with `gemini-cli`'s interactive sessions and local Git snapshots, not applicable to stateless servers. |
| **`preferredEditor`** | ❌ **Not Supported** | Used to open external editors in `gemini-cli`, `bridge-server` has no such interaction flow. |
| **`bugCommand`** | ❌ **Not Supported** | This is configuration for `gemini-cli`'s `/bug` command, unrelated to `bridge-server`. |
| **`hideTips`** | ❌ **Not Supported** | Pure UI configuration. |
| **`hideWindowTitle`** | ❌ **Not Supported** | Pure UI configuration. |
| **`accessibility`** | ❌ **Not Supported** | Pure UI configuration, used to disable loading animations, etc. |

## API Endpoints

### MCP Endpoint

- **URL**: `http://localhost:8765/mcp`
- **Protocol**: Model Context Protocol (MCP)
- **Usage**: Connect MCP-compatible clients to access all configured tools

### OpenAI Compatible Endpoints

#### Chat Completions
- **URL**: `http://localhost:8765/v1/chat/completions`
- **Method**: POST
- **Compatibility**: Full OpenAI Chat Completions API compatibility
- **Features**: Supports streaming and non-streaming responses, function calling

#### Models
- **URL**: `http://localhost:8765/v1/models`
- **Method**: GET
- **Returns**: List of available Gemini models

## Telemetry, Terms of Service & Privacy

This service **does not introduce any new telemetry or data collection mechanisms**. It relies entirely on the OpenTelemetry (OTEL) system built into the `@google/gemini-cli-core` package. All telemetry data (if enabled) will follow the main configuration of `gemini-cli`.

Your usage is subject to the terms of service and privacy policies corresponding to the `gemini-cli` account type you use for authentication.

- [Gemini CLI Telemetry Documentation](https://github.com/google-gemini/gemini-cli/blob/main/docs/telemetry.md)
- [Gemini CLI Terms of Service and Privacy Statement](https://github.com/google-gemini/gemini-cli/blob/main/docs/tos-privacy.md)

## Example Usage

### Using with Open WebUI

1. Start the bridge server:
   ```bash
   gemini-cli-bridge --mode=edit --port=8765
   ```

2. Configure Open WebUI to use the bridge server:
   - Base URL: `http://localhost:8765/v1`
   - API Key: Any value (authentication is handled by gemini-cli)

### Using with MCP Clients

Connect your MCP client to `http://localhost:8765/mcp` to access all configured tools.

### Using with curl

```bash
# Chat completion
curl -X POST http://localhost:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "gemini-2.5-flash",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'

# List models
curl http://localhost:8765/v1/models
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure `gemini-cli` is properly authenticated first
2. **Port Already in Use**: Change the port using `--port` argument
3. **Tool Access Denied**: Check your security mode and policy configuration

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
gemini-cli-bridge --debug
```

## Contributing

This is an active development project, and we welcome community contributions! Please follow these steps:

1. Fork this repository and make changes in your local environment.
2. Submit a Pull Request describing your changes and their purpose.
3. We will review your request promptly and provide feedback.

Thank you for your participation!

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## Related Projects

- [Gemini CLI](https://github.com/google-gemini/gemini-cli) - The core command-line AI workflow tool
- [Model Context Protocol](https://github.com/modelcontextprotocol/specification) - The protocol for connecting AI models to tools