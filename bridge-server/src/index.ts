#!/usr/bin/env node
/**
 * @license
 * Copyright 2025 Intelligent-Internet
 * SPDX-License-Identifier: Apache-2.0
*/
import {
  Config,
  ApprovalMode,
  sessionId,
  loadServerHierarchicalMemory,
  FileDiscoveryService,
  DEFAULT_GEMINI_MODEL,
  DEFAULT_GEMINI_EMBEDDING_MODEL,
  MCPServerConfig,
  AuthType,
} from '@google/gemini-cli-core';
import { loadSettings, type Settings } from './config/settings.js';
import { loadExtensions, type Extension } from './config/extension.js';
import { getCliVersion } from './utils/version.js';
import { loadServerConfig } from './config/config.js';
import { GcliMcpBridge } from './bridge/bridge.js';
import { createOpenAIRouter } from './bridge/openai.js';
import express from 'express';
import { logger } from './utils/logger.js';
import { type SecurityPolicy } from './types.js';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import path from 'path';
import readline from 'readline';

function mergeMcpServers(
  settings: Settings,
  extensions: Extension[],
): Record<string, MCPServerConfig> {
  const mcpServers: Record<string, MCPServerConfig> = {
    ...(settings.mcpServers || {}),
  };
  for (const extension of extensions) {
    Object.entries(extension.config.mcpServers || {}).forEach(
      ([key, server]) => {
        if (mcpServers[key]) {
          logger.warn(
            `Skipping extension MCP config for server with key "${key}" as it already exists.`,
          );
          return;
        }
        mcpServers[key] = server;
      },
    );
  }
  return mcpServers;
}

async function startMcpServer() {
  // --- Yargs-based argument parsing ---
  const argv = await yargs(hideBin(process.argv))
    .option('host', {
      alias: 'h',
      type: 'string',
      description: 'The host address to listen on.',
      default: '127.0.0.1',
    })
    .option('port', {
      alias: 'p',
      type: 'number',
      description: 'The port to listen on. Can also be set via GEMINI_MCP_PORT.',
    })
    .option('target-dir', {
      alias: 'd',
      type: 'string',
      description:
        'The absolute path to the root directory for all file operations. Defaults to the current working directory.',
      default: process.cwd(),
    })
    .option('debug', {
      type: 'boolean',
      description: 'Enable detailed debug logging.',
      default: false,
    })
    .option('use-internal-prompt', {
      type: 'boolean',
      description:
        'Load internal GEMINI.md prompts. If false, server runs in pure OpenAI bridge mode and uses client system prompts.',
      default: false,
    })
    .option('tools-model', {
      type: 'string',
      description:
        'Specify a default model for tool execution (e.g., web search). Can also be set via GEMINI_TOOLS_DEFAULT_MODEL.',
    })
    .option('mode', {
      type: 'string',
      description: "Set the server's security mode.",
      choices: ['read-only', 'edit', 'configured', 'yolo'],
    })
    .option('allow-mcp-proxy', {
      type: 'boolean',
      description:
        "In 'configured' or 'yolo' mode, allows all discovered MCP proxy tools.",
      default: false,
    })
    // 新增：添加 --resolve-redirects 标志
    .option('resolve-redirects', {
      type: 'boolean',
      description: 'Resolve redirect URLs from search results to their final destination.',
      default: false, // 默认关闭
    })
    .option('i-know-what-i-am-doing', {
      type: 'boolean',
      description:
        "Bypass interactive safety confirmations for 'yolo' mode and MCP proxy usage.",
      default: false,
    })
    .help()
    .alias('help', '?').argv;

  // --- Configuration variables from args and environment ---
  const host = argv.host;
  const debugMode = argv.debug;
  const useInternalPrompt = argv['use-internal-prompt'];
  const toolsModel = argv['tools-model'];
  const targetDir = path.resolve(argv['target-dir']);
  const resolveRedirects = argv['resolve-redirects']; // 新增：获取标志的值

  // Priority: CLI arg > env var > default
  const port =
    argv.port ??
    (process.env.GEMINI_MCP_PORT
      ? parseInt(process.env.GEMINI_MCP_PORT, 10)
      : 8765);

  if (isNaN(port)) {
    logger.error(
      'Invalid port number provided. Use --port=<number> or set GEMINI_MCP_PORT environment variable.',
    );
    process.exit(1);
  }

  logger.info('Starting Gemini CLI Bridge (MCP + OPENAI)...');
  if (useInternalPrompt) {
    logger.info(
      'Internal prompt mode enabled (--use-internal-prompt). GEMINI.md will be loaded.',
    );
  } else {
    logger.info(
      'Pure OpenAI bridge mode enabled. GEMINI.md will be ignored. Client system prompts will be used.',
    );
  }

  // Reuse core config loading, but manually construct Config.
  const workspaceRoot = process.cwd();
  const settings = loadSettings(workspaceRoot);
  const extensions = loadExtensions(workspaceRoot);
  const cliVersion = await getCliVersion();

  // Determine the final security mode, with CLI args taking precedence over settings.
  const finalMode =
    (argv.mode as SecurityPolicy['mode']) ||
    settings.merged.securityPolicy?.mode ||
    'read-only';
  const allowMcpProxy = argv['allow-mcp-proxy'];

  // Validate argument combinations.
  if (allowMcpProxy && (finalMode === 'read-only' || finalMode === 'edit')) {
    logger.error(
      `--allow-mcp-proxy can only be used with 'configured' or 'yolo' mode. Current mode is '${finalMode}'.`,
    );
    process.exit(1);
  }

  // Construct the final security policy object.
  const securityPolicy: SecurityPolicy = {
    ...settings.merged.securityPolicy,
    mode: finalMode,
    allowMcpProxy: allowMcpProxy,
  };

  const needsConfirmation =
    (finalMode === 'yolo' || allowMcpProxy) && !argv['i-know-what-i-am-doing'];

  // Display warnings and get confirmation if needed.
  await displaySecurityWarning(finalMode, targetDir, allowMcpProxy);
  if (needsConfirmation) {
    await getInteractiveConfirmation();
  }

  const config = await loadServerConfig(
    settings.merged,
    extensions,
    sessionId,
    debugMode,
    useInternalPrompt,
    toolsModel,
    targetDir,
  );

  // REFACTORED: Authentication logic with improved verbosity and error handling.
  let selectedAuthType = settings.merged.selectedAuthType;
  let authReason = '';

  if (selectedAuthType) {
    authReason = ' (from .gemini/settings.json)';
  } else if (process.env.GEMINI_API_KEY) {
    selectedAuthType = AuthType.USE_GEMINI;
    authReason = ' (fallback to GEMINI_API_KEY environment variable)';
  } else {
    // NEW: More descriptive error message for missing auth.
    logger.error(
      'Authentication missing: Please complete the authentication setup in gemini-cli first, or set the GEMINI_API_KEY environment variable.\n' +
        'This program accesses Gemini services via gemini-cli and does not run standalone.\n' +
        'Check the gemini-cli documentation for setup instructions.',
    );
    process.exit(1);
  }

  // NEW: Pre-authentication logging.
  logger.info(
    `Attempting authentication using "${selectedAuthType}" method${authReason}...`,
  );

  try {
    await config.initialize();
    await config.refreshAuth(selectedAuthType);
    // NEW: Success logging.
    logger.info(`✅ Authentication successful!`);
    // The original debug log is still useful.
    logger.debug(debugMode, `Using authentication method: ${selectedAuthType}`);
  } catch (e) {
    // NEW: Robust error handling and logging.
    logger.error(
      `❌ Authentication failed: ${
        e instanceof Error ? e.message : String(e)
      }`,
    );
    logger.error(
      'Please check your authentication configuration (e.g., API Key validity, OAuth credentials) and try again.',
    );
    process.exit(1);
  }
  // --- End of Refactored Block ---

  // Log the model being used for tools. This is now set in loadServerConfig.
  logger.debug(debugMode, `Using model for tools: ${config.getModel()}`);

  // Initialize and start MCP Bridge and OpenAI services.
  const mcpBridge = new GcliMcpBridge(
    config,
    cliVersion,
    securityPolicy,
    debugMode,
    resolveRedirects, // 新增：将标志传递给 Bridge
  );

  // Log available tools
  const availableTools = await mcpBridge.getAvailableTools();
  logger.info('--- Available Tools ---');
  if (availableTools.length > 0) {
    availableTools.forEach(tool => {
      const description = tool.description?.split('\n')[0] || '';
      logger.info(`- ${tool.name}: ${description}`);
    });
  } else {
    logger.info('No tools are available with the current security policy.');
  }
  logger.info('-----------------------');

  const app = express();
  app.use(express.json({ limit: '50mb' }));

  // Start the MCP service.
  await mcpBridge.start(app);

  // Start OpenAI compatible endpoint.
  const openAIRouter = createOpenAIRouter(config, debugMode);
  app.use('/v1', openAIRouter);

  app.listen(port, host, () => {
    logger.info('Server running', {
      port,
      host,
      mcpUrl: `http://${host}:${port}/mcp`,
      openAIUrl: `http://${host}:${port}/v1`,
    });
  });
}

startMcpServer().catch(error => {
  logger.error('Failed to start Gemini CLI MCP Bridge:', error);
  process.exit(1);
});

const green = (text: string) => `\x1b[32m${text}\x1b[0m`;
const yellow = (text: string) => `\x1b[33m${text}\x1b[0m`;
const red = (text: string) => `\x1b[31m${text}\x1b[0m`;
const bold = (text: string) => `\x1b[1m${text}\x1b[0m`;

async function displaySecurityWarning(
  mode: string,
  targetDir: string,
  allowMcp: boolean,
): Promise<void> {
  console.log('--- Security Mode Initialized ---');
  switch (mode) {
    case 'read-only':
      console.log(green(`${bold('Mode: Read-Only')} (Default & Safest)`));
      console.log(green(`✓ Only read-only tools are enabled.`));
      console.log(green(`✓ File operations are restricted to: ${targetDir}`));
      console.log(
        yellow(`✗ File editing, shell commands, and MCP tools are disabled.`),
      );
      console.log(`Tip: Use '--target-dir' to change the file operation scope.`);
      break;
    case 'edit':
      console.log(yellow(`${bold('Mode: Edit')}`));
      console.log(
        yellow(`✓ All built-in tools are enabled, except 'run_shell_command'.`),
      );
      console.log(
        yellow(`⚠ Model has WRITE PERMISSIONS to files within: ${targetDir}`),
      );
      console.log(yellow(`✗ MCP proxy tools are disabled in this mode.`));
      break;
    case 'configured':
      console.log(yellow(`${bold('Mode: Configured')}`));
      console.log(
        yellow(
          `⚠ Security is managed by your 'securityPolicy' settings in settings.json.`,
        ),
      );
      console.log(
        yellow(
          `  Review your 'allowedTools' and 'shellCommandPolicy' configurations carefully.`,
        ),
      );
      break;
    case 'yolo':
      console.log(red(`${bold('███ MODE: YOLO - EXTREMELY DANGEROUS ███')}`));
      console.log(
        red(
          `⚠ All built-in tools are enabled, including 'run_shell_command' with no restrictions.`,
        ),
      );
      break;
  }

  if (allowMcp) {
    console.log(red(`${bold('\n--- MCP Proxy Enabled ---')}`));
    console.log(red(`⚠ All discovered MCP proxy tools are enabled.`));
    console.log(
      red(
        `⚠ This allows the model to make network requests to third-party services.`,
      ),
    );
  }
  console.log('---------------------------------');
}

async function getInteractiveConfirmation(): Promise<void> {
  console.log(
    red(`${bold('ACTION REQUIRED:')} You have enabled a high-risk mode.`),
  );
  console.log(
    `To confirm you understand the risks, please type ${bold('YES')} and press Enter.`,
  );
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  const answer = await new Promise<string>(resolve => rl.question('> ', resolve));
  rl.close();
  if (answer !== 'YES') {
    console.log('Confirmation failed. Exiting.');
    process.exit(1);
  }
  console.log('Confirmation received. Starting server...');
}
