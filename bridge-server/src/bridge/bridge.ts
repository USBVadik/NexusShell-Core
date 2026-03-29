import express, { Request, Response, NextFunction, Application } from 'express';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { z } from 'zod';
import {
  type Config,
  type Tool as GcliTool,
  type ToolResult,
  GeminiChat,
  WebFetchTool,
  WebSearchTool,
  DiscoveredMCPTool,
} from '@google/gemini-cli-core';
import {
  type CallToolResult,
  isInitializeRequest,
} from '@modelcontextprotocol/sdk/types.js';
import {
  type PartUnion,
  type Tool,
  type GenerateContentConfig,
  type Content,
} from '@google/genai';
import { randomUUID } from 'node:crypto';
import { fetch } from 'undici'; // 显式导入 undici 的 fetch
import { logger } from '../utils/logger.js';
import { type SecurityPolicy } from '../types.js';

class SecurityPolicyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SecurityPolicyError';
  }
}

export class GcliMcpBridge {
  private readonly config: Config;
  private readonly cliVersion: string;
  private readonly securityPolicy: SecurityPolicy; // NEW: 存储安全策略
  private readonly debugMode: boolean;
  private readonly resolveRedirects: boolean; // 新增：存储重定向解析标志
  private readonly sessions: Record<
    string,
    { mcpServer: McpServer; transport: StreamableHTTPServerTransport }
  > = {};

  constructor(
    config: Config,
    cliVersion: string,
    securityPolicy: SecurityPolicy,
    debugMode = false,
    resolveRedirects = false, // 新增
  ) {
    this.config = config;
    this.cliVersion = cliVersion;
    this.securityPolicy = securityPolicy;
    this.debugMode = debugMode;
    this.resolveRedirects = resolveRedirects; // 新增
    // 新增：启动时打印日志，确认模式是否开启
    logger.info(
      `Redirect resolution mode: ${
        this.resolveRedirects ? 'ENABLED' : 'DISABLED'
      }`,
    );
  }

  public async getAvailableTools(): Promise<GcliTool[]> {
    const toolRegistry = await this.config.getToolRegistry();
    const allTools = toolRegistry.getAllTools();
    let toolsToRegister: GcliTool[] = [];

    const isMcpTool = (tool: GcliTool): boolean =>
      tool instanceof DiscoveredMCPTool;
    const isLocalTool = (tool: GcliTool): boolean => !isMcpTool(tool);

    switch (this.securityPolicy.mode) {
      case 'read-only':
        toolsToRegister = allTools.filter(
          tool => isLocalTool(tool) && this.isReadOnlyTool(tool.name),
        );
        break;

      case 'edit':
        toolsToRegister = allTools.filter(
          tool => isLocalTool(tool) && tool.name !== 'run_shell_command',
        );
        break;

      case 'configured':
        const allowedSet = new Set(this.securityPolicy.allowedTools || []);
        toolsToRegister = allTools.filter(tool => allowedSet.has(tool.name));

        if (this.securityPolicy.allowMcpProxy) {
          const mcpTools = allTools.filter(isMcpTool);
          toolsToRegister.push(...mcpTools);
          // 去重，以防用户在 allowedTools 中也定义了 MCP 工具
          toolsToRegister = [...new Set(toolsToRegister)];
        }
        break;

      case 'yolo':
        // 启用所有本地工具
        toolsToRegister = allTools.filter(isLocalTool);
        // 如果明确允许，则添加所有 MCP 工具
        if (this.securityPolicy.allowMcpProxy) {
          toolsToRegister.push(...allTools.filter(isMcpTool));
        }
        break;
    }

    return toolsToRegister;
  }

  private async createNewMcpServer(): Promise<McpServer> {
    const server = new McpServer(
      {
        name: 'gemini-cli-bridge-server',
        version: this.cliVersion,
      },
      {
        capabilities: {
          logging: {},
          // NEW: 在 server/info 中声明安全策略
          geminiCliSecurityPolicy: this.securityPolicy,
        },
      },
    );
    await this.registerAllGcliTools(server);
    return server;
  }

  public async start(app: Application) {
    app.all('/mcp', async (req: Request, res: Response) => {
      const sessionId = req.headers['mcp-session-id'] as string | undefined;

      let session = sessionId ? this.sessions[sessionId] : undefined;

      if (!session) {
        if (isInitializeRequest(req.body)) {
          logger.debug(
            this.debugMode,
            'Creating new session and transport for initialize request',
          );

          try {
            const newMcpServer = await this.createNewMcpServer();
            const newTransport = new StreamableHTTPServerTransport({
              sessionIdGenerator: () => randomUUID(),
              onsessioninitialized: newSessionId => {
                logger.debug(
                  this.debugMode,
                  `Session initialized: ${newSessionId}`,
                );
                this.sessions[newSessionId] = {
                  mcpServer: newMcpServer,
                  transport: newTransport,
                };
              },
            });

            newTransport.onclose = () => {
              const sid = newTransport.sessionId;
              if (sid && this.sessions[sid]) {
                logger.debug(
                  this.debugMode,
                  `Session ${sid} closed, removing session object.`,
                );
                delete this.sessions[sid];
              }
            };

            await newMcpServer.connect(newTransport);

            session = { mcpServer: newMcpServer, transport: newTransport };
          } catch (e) {
            // Handle errors during server creation
            logger.error('Error creating new MCP session:', e);
            if (!res.headersSent) {
              res.status(500).json({ error: 'Failed to create session' });
            }
            return;
          }
        } else {
          logger.error(
            'Bad Request: Missing session ID for non-initialize request.',
          );
          res.status(400).json({
            jsonrpc: '2.0',
            error: {
              code: -32000,
              message: 'Bad Request: Mcp-Session-Id header is required',
            },
            id: null,
          });
          return;
        }
      } else {
        logger.debug(
          this.debugMode,
          `Reusing transport and server for session: ${sessionId}`,
        );
      }

      try {
        await session.transport.handleRequest(req, res, req.body);
      } catch (e) {
        logger.error('Error handling request:', e);
        if (!res.headersSent) {
          res.status(500).end();
        }
      }
    });
  }

  private async registerAllGcliTools(mcpServer: McpServer) {
    const toolRegistry = await this.config.getToolRegistry();
    const allTools = toolRegistry.getAllTools();
    let toolsToRegister: GcliTool[] = [];

    const isMcpTool = (tool: GcliTool): boolean =>
      tool instanceof DiscoveredMCPTool;
    const isLocalTool = (tool: GcliTool): boolean => !isMcpTool(tool);

    switch (this.securityPolicy.mode) {
      case 'read-only':
        toolsToRegister = allTools.filter(
          tool => isLocalTool(tool) && this.isReadOnlyTool(tool.name),
        );
        break;

      case 'edit':
        toolsToRegister = allTools.filter(
          tool => isLocalTool(tool) && tool.name !== 'run_shell_command',
        );
        break;

      case 'configured':
        const allowedSet = new Set(this.securityPolicy.allowedTools || []);
        toolsToRegister = allTools.filter(tool => allowedSet.has(tool.name));

        if (this.securityPolicy.allowMcpProxy) {
          const mcpTools = allTools.filter(isMcpTool);
          toolsToRegister.push(...mcpTools);
          // 去重，以防用户在 allowedTools 中也定义了 MCP 工具
          toolsToRegister = [...new Set(toolsToRegister)];
        }
        break;

      case 'yolo':
        // 启用所有本地工具
        toolsToRegister = allTools.filter(isLocalTool);
        // 如果明确允许，则添加所有 MCP 工具
        if (this.securityPolicy.allowMcpProxy) {
          toolsToRegister.push(...allTools.filter(isMcpTool));
        }
        break;
    }

    logger.info(
      `Operating in '${this.securityPolicy.mode}' mode. Enabled tools:`,
      toolsToRegister.length > 0
        ? toolsToRegister.map(t => t.name).join(', ')
        : 'None',
    );

    for (const tool of toolsToRegister) {
      this.registerGcliTool(tool, mcpServer);
    }
  }

  // 新增：解析重定向链接的辅助函数
  private async resolveRedirectUrl(url: string): Promise<string> {
    if (!url.includes('vertexaisearch.cloud.google.com')) {
      return url;
    }
    try {
      logger.debug(this.debugMode, `Resolving redirect for: ${url}`);
      // 使用 undici 的 fetch，它默认跟随重定向
      const response = await fetch(url, {
        method: 'HEAD', // 使用 HEAD 请求更高效
        redirect: 'follow',
      });
      logger.debug(this.debugMode, `Resolved to: ${response.url}`);
      return response.url;
    } catch (error) {
      logger.warn(
        `Failed to resolve redirect for ${url}: ${
          error instanceof Error ? error.message : String(error)
        }`,
      );
      return url; // 解析失败则返回原始 URL
    }
  }

  // NEW: 辅助方法，用于判断工具是否为只读
  private isReadOnlyTool(toolName: string): boolean {
    const readOnlyTools = [
      'read_file',
      'list_directory',
      'glob',
      'search_file_content',
      'google_web_search',
      'web_fetch',
    ];
    return readOnlyTools.includes(toolName);
  }

  // NEW: 辅助方法，用于检查 shell 命令是否被允许
  private isShellCommandAllowed(command: string): boolean {
    if (this.securityPolicy.mode === 'yolo') {
      return true;
    }
    if (!this.securityPolicy.shellCommandPolicy) {
      // 在 restricted 模式下，如果没有定义 shell 策略，则默认拒绝
      return false;
    }

    const { allow, deny } = this.securityPolicy.shellCommandPolicy;
    const normalizedCommand = command.trim().replace(/\s+/g, ' ');

    // 检查黑名单
    if (deny?.some(deniedCmd => normalizedCommand.startsWith(deniedCmd))) {
      return false;
    }

    // 如果定义了白名单，则必须匹配
    if (allow && allow.length > 0) {
      return allow.some(allowedCmd =>
        normalizedCommand.startsWith(allowedCmd),
      );
    }

    // 如果没有定义白名单，但有黑名单，则只要不匹配黑名单就允许
    if (deny) {
      return true;
    }

    // 默认拒绝
    return false;
  }

  private registerGcliTool(tool: GcliTool, mcpServer: McpServer) {
    let toolInstanceForExecution = tool;
    let finalDescription = tool.description;

    // For web tools, check if a custom model is specified via environment variable.
    // If so, create a new tool instance with a proxied config to use that model.
    if (tool.name === 'google_web_search' || tool.name === 'web_fetch') {
      const toolModel = process.env.GEMINI_TOOLS_DEFAULT_MODEL;

      if (toolModel) {
        logger.debug(
          this.debugMode,
          `Using custom model "${toolModel}" for tool "${tool.name}"`,
        );

        // Create a proxy for this.config to override getModel.
        const proxyConfig = new Proxy(this.config, {
          get: (target, prop, receiver) => {
            if (prop === 'getModel') {
              return () => toolModel;
            }
            return Reflect.get(target, prop, receiver);
          },
        }) as Config;

        // Create a new tool instance with the proxied config.
        if (tool.name === 'google_web_search') {
          toolInstanceForExecution = new WebSearchTool(proxyConfig);
        } else {
          toolInstanceForExecution = new WebFetchTool(proxyConfig);
        }
      }
    }

    // NEW: 动态修改 run_shell_command 的描述
    if (
      tool.name === 'run_shell_command' &&
      this.securityPolicy.mode !== 'yolo' &&
      this.securityPolicy.shellCommandPolicy
    ) {
      const { allow, deny } = this.securityPolicy.shellCommandPolicy;
      let policyDescription = '\n\n**Security Policy Note:**';
      if (allow && allow.length > 0) {
        policyDescription += `\n- Only the following command prefixes are allowed: \`${allow.join(
          '`, `',
        )}\`.`;
      } else {
        policyDescription += `\n- All shell commands are denied unless explicitly allowed. No commands are currently allowed.`;
      }
      if (deny && deny.length > 0) {
        policyDescription += `\n- The following command prefixes are explicitly denied: \`${deny.join(
          '`, `',
        )}\`.`;
      }
      finalDescription += policyDescription;
    }

    mcpServer.registerTool(
      tool.name,
      {
        title: tool.displayName,
        description: finalDescription,
        inputSchema: this.convertJsonSchemaToZod(tool.schema.parameters),
      },
      async (
        args: Record<string, unknown>,
        extra: { signal: AbortSignal },
      ) => {
        // NEW: 在执行前进行安全检查
        if (tool.name === 'run_shell_command') {
          const commandToRun = (args as { command: string }).command;
          if (!this.isShellCommandAllowed(commandToRun)) {
            throw new SecurityPolicyError(
              `Command "${commandToRun}" is denied by the security policy.`,
            );
          }
        }

        const startTime = Date.now();
        logger.info('MCP tool call started', { toolName: tool.name, args });
        try {
          // toolInstanceForExecution is either the original tool or a new instance with a custom model config.
          const result = await toolInstanceForExecution.execute(
            args,
            extra.signal,
          );
          const durationMs = Date.now() - startTime;
          logger.info('MCP tool call finished', {
            toolName: tool.name,
            status: 'success',
            durationMs,
          });

          // 新增：重定向解析逻辑
          if (
            tool.name === 'google_web_search' &&
            this.resolveRedirects &&
            typeof result.llmContent === 'string'
          ) {
            logger.debug(
              this.debugMode,
              'Resolving redirect URLs in web search result...',
            );

            const urlPattern =
              /\((https:\/\/vertexaisearch\.cloud\.google\.com\/grounding-api-redirect\/[^\s)]+)\)/g;
            const redirectUrls = [
              ...result.llmContent.matchAll(urlPattern),
            ].map(match => match[1]);

            if (redirectUrls.length > 0) {
              logger.debug(
                this.debugMode,
                `Found ${redirectUrls.length} redirect URLs to resolve.`,
              );
              const finalUrls = await Promise.all(
                redirectUrls.map(url => this.resolveRedirectUrl(url)),
              );

              let modifiedContent = result.llmContent;
              redirectUrls.forEach((originalUrl, index) => {
                const finalUrl = finalUrls[index];
                if (originalUrl !== finalUrl) {
                  logger.debug(
                    this.debugMode,
                    `Replacing ${originalUrl} with ${finalUrl}`,
                  );
                  modifiedContent = modifiedContent.replace(
                    originalUrl,
                    finalUrl,
                  );
                }
              });
              result.llmContent = modifiedContent;
            } else {
              logger.debug(
                this.debugMode,
                'No redirect URLs found in the result.',
              );
            }
          }

          return this.convertGcliResultToMcpResult(result);
        } catch (e) {
          const durationMs = Date.now() - startTime;
          logger.error('MCP tool call failed', e as Error, {
            toolName: tool.name,
            durationMs,
          });
          // Re-throw the error to be handled by the MCP SDK.
          throw e;
        }
      },
    );
  }


  private convertJsonSchemaToZod(jsonSchema: any): any {
    // Helper to convert a single JSON schema property to a Zod type.
    // This is defined as an inner arrow function to recursively call itself for arrays
    // and to call the outer function for nested objects via `this`.
    const convertProperty = (prop: any): z.ZodTypeAny => {
      if (!prop || !prop.type) {
        return z.any();
      }

      switch (prop.type) {
        case 'string':
          return z.string().describe(prop.description || '');
        case 'number':
          return z.number().describe(prop.description || '');
        case 'boolean':
          return z.boolean().describe(prop.description || '');
        case 'array':
          // Recursively call the converter for `items`.
          if (!prop.items) {
            // A valid array schema MUST have `items`. Fallback to `any` if missing.
            return z.array(z.any()).describe(prop.description || '');
          }
          return z
            .array(convertProperty(prop.items))
            .describe(prop.description || '');
        case 'object':
          // For nested objects, recursively call the main function to get the shape.
          return z
            .object(this.convertJsonSchemaToZod(prop))
            .passthrough()
            .describe(prop.description || '');
        default:
          return z.any();
      }
    };

    if (!jsonSchema || !jsonSchema.properties) {
      return {};
    }

    const shape: any = {};
    for (const [key, prop] of Object.entries(jsonSchema.properties)) {
      let fieldSchema = convertProperty(prop as any);

      if (!jsonSchema.required || !jsonSchema.required.includes(key)) {
        fieldSchema = fieldSchema.optional();
      }
      shape[key] = fieldSchema;
    }
    return shape;
  }

  private convertGcliResultToMcpResult(
    gcliResult: ToolResult,
  ): CallToolResult {
    if (typeof gcliResult.llmContent === 'string') {
      return { content: [{ type: 'text', text: gcliResult.llmContent }] };
    }

    const parts = Array.isArray(gcliResult.llmContent)
      ? gcliResult.llmContent
      : [gcliResult.llmContent];

    const contentBlocks = parts.map((part: PartUnion) => {
      // case 1: part is a simple string
      if (typeof part === 'string') {
        return { type: 'text' as const, text: part };
      }
      // case 2: part is a TextPart { text: '...' }
      if ('text' in part && part.text) {
        return { type: 'text' as const, text: part.text };
      }
      // *** 新增的修复逻辑 ***
      // case 3: part is a FunctionResponsePart { functionResponse: ... }
      if ('functionResponse' in part && part.functionResponse) {
        // Stringify the response content to make it displayable as text.
        // This is robust and captures all details from the external tool.
        const responseContent = JSON.stringify(
          part.functionResponse.response,
          null,
          2,
        );
        return { type: 'text' as const, text: responseContent };
      }
      // Default fallback for any other unexpected part types
      return { type: 'text' as const, text: '[Unsupported Part Type]' };
    });

    return { content: contentBlocks };
  }
}
