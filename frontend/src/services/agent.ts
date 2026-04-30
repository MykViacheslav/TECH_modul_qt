import { TechModulAPI, type AgentPreview } from "@/services/api";

export async function parseAgentCommand(text: string, projectId = 1): Promise<AgentPreview> {
  return TechModulAPI.agentCommand(text, projectId);
}
