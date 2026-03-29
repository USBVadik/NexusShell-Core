/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

export interface MessageContentPart {
  type: 'text' | 'image_url';
  text?: string;
  image_url?: {
    url: string;
    detail?: 'low' | 'high' | 'auto';
  };
}

export interface OpenAIToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    /** A JSON string of arguments. */
    arguments: string;
  };
}

export interface OpenAIMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  /** Can be null when tool_calls are present. */
  content: string | null | MessageContentPart[];
  tool_calls?: OpenAIToolCall[];
  tool_call_id?: string;
}

export interface OpenAIFunction {
  name: string;
  description?: string;
  /** JSON Schema object */
  parameters: Record<string, unknown>;
}

export interface OpenAITool {
  type: 'function';
  function: OpenAIFunction;
}

export interface OpenAIChatCompletionRequest {
  model: string;
  messages: OpenAIMessage[];
  stream?: boolean;
  /** Corresponds to Gemini's Tool[] */
  tools?: OpenAITool[];
  /** Corresponds to Gemini's ToolConfig */
  tool_choice?: any;
}

export interface ReasoningData {
  reasoning: string;
}

export type StreamChunk =
  | { type: 'text'; data: string }
  | { type: 'reasoning'; data: ReasoningData }
  | { type: 'tool_code'; data: { name: string; args: Record<string, unknown> } };

/**
 * Defines the structure of an OpenAI API-compatible error object.
 */
export interface OpenAIError {
  message: string;
  type:
    | 'invalid_request_error'
    | 'api_error'
    | 'authentication_error'
    | 'server_error';
  param: string | null;
  code: string | null;
}

/**
 * Defines the complete OpenAI API error response structure.
 */
export interface OpenAIErrorResponse {
  error: OpenAIError;
}

export interface SecurityPolicy {
  mode?: 'read-only' | 'edit' | 'configured' | 'yolo';
  allowedTools?: string[];
  shellCommandPolicy?: {
    allow?: string[];
    deny?: string[];
  };
  allowMcpProxy?: boolean;
}

// 定义非流式响应中的 message 对象
export interface OpenAIChatCompletionMessage {
  role: 'assistant';
  content: string | null;
  tool_calls?: OpenAIToolCall[];
}

// 定义非流式响应中的 choice 对象
export interface OpenAIChatCompletionChoice {
  index: number;
  message: OpenAIChatCompletionMessage;
  finish_reason:
    | 'stop'
    | 'length'
    | 'tool_calls'
    | 'content_filter'
    | 'function_call';
}

// 定义完整的非流式响应体
export interface OpenAIChatCompletion {
  id: string;
  object: 'chat.completion';
  created: number;
  model: string;
  choices: OpenAIChatCompletionChoice[];
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
