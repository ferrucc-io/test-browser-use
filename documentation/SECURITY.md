# Security

> Below is a comprehensive security audit of your Browser-Use + MCP project using all the prior conversations and standard best practices for security. This is not an exhaustive penetration test but a systematic review of the major scripts and common pitfalls. We also provide suggestions for how to mitigate identified risks.

1. Project Structure & High-Level Summary

The code layout is:

 1. Main server code server.py that runs an async event loop (loop = asyncio.new_event_loop()) within __main__):
    - Runs a FastMCP (Model Context Protocol) server.
    - Exposes a tool endpoint to run a single “browser agent.”
 2. Custom Agent under the agent directory and Related Classes:
    - custom_agent.py: Inherits from a base Agent and implements logic to parse LLM output, execute browser actions, handle vision, and create history GIFs.
    - custom_massage_manager.py: Handles LLM output parsing and conversion to browser actions.
    - custom_prompts.py: Contains system-level instructions for the LLM to produce a structured JSON output.
    - custom_views.py: Data classes (CustomAgentStepInfo, CustomAgentBrain) are used to store the agent’s state and output schema.
 3. Custom Browser Components under the browser directory:
    - config.py: Holds dataclasses for configuring Chrome (persistent sessions, debugging port).
    - custom_browser.py: Subclass of Browser that handles launching or connecting to Chrome over a debugging port. It may disable some security flags or run headless.
    - custom_context.py: Subclass of BrowserContext that can reuse an existing context or create new ones, load cookies, start traces, etc.
 4. Controllers & Actions:
    - custom_controller.py: Registers custom actions (copy/paste from clipboard).
 5. Utilities:
    - agent_state.py: Tracks a stop_requested event (via asyncio.Event) and optional “last valid state.” Implemented as a singleton (only one agent at a time).
    - utils.py: offers a get_llm_model function to create different LLM clients (OpenAI, Anthropic, Azure, etc.), as well as image encoding and file-tracking utilities.

The project runs a single agent simultaneously, hooking an LLM to actual browser actions. Let’s go through significant security aspects.

2. Identified Security Risks & Recommendations

Below are the main areas of concern based on the code we’ve seen and typical usage patterns.

2.1 Disabling Browser Security & Remote Debug Port

Where

- custom_browser.py:
- Allows launching Chrome with flags like --disable-web-security.
- Launches Chrome with --remote-debugging-port=9222.

Risks

 1. Cross-Origin Attacks: Disabling web security (--disable-web-security, --disable-features=IsolateOrigins) allows malicious pages to read cross-origin data in the same browser instance. If the agent visits untrusted websites, it could inadvertently exfiltrate data from other open tabs or sessions.
 2. Debug Port Exposure: A remote debugging port on 9222 (if bound to 0.0.0.0 or otherwise accessible externally) gives anyone who can connect full control of the browser. If not behind a firewall, an attacker can hijack the session.

Recommendations

 1. Limit the usage of disable-web-security and related flags. Restrict this to internal/test scenarios or run it inside a hardened container or ephemeral environment.
 2. Restrict Access to Port 9222:

- Bind to 127.0.0.1 only (--remote-debugging-address=127.0.0.1) so external hosts cannot connect.
- Use a firewall or security group to block external access.
- If remote access is required, use SSH tunneling rather than publicly exposing the port.

 3. If you must open untrusted pages, create separate browser instances. This means not reusing the same “user data dir” or disabling security for critical tasks.

2.2 Global Singleton AgentState

Where

- agent_state.py implements a singleton that shares_stop_requested and last_valid_state across all agent references.

Risks

 1. Concurrent Agents: If you (in the future) attempt to run multiple agents, the single AgentState object might cause cross-talk or unpredictable behavior (e.g., one agent’s stop request stops another).
 2. Potential Race Conditions: If the code evolves to multi-thread or multi-process, the concurrency might not behave as expected.

Recommendations

 1. Ensure Only One Agent: If that’s your design (a single agent at a time), the singleton is acceptable. Document it.
 2. Remove Singleton for multi-agent scenarios. Each agent can have its state object.

2.3 Clipboard Actions

Where

- custom_controller.py registers actions like “Copy text to clipboard” and “Paste from clipboard.”

Risks

 1. System Clipboard: Copy/paste using the OS-level clipboard (pyperclip). This can leak sensitive data if other apps or remote sessions see the same clipboard.
 2. Overwrite: The agent can overwrite a user’s clipboard or read from it unexpectedly.

Recommendations

 1. Run in a Controlled Environment: It may be okay if you only do local development or a dedicated environment.
 2. Use an In-Memory Clipboard: Instead of the actual system clipboard, implement a local memory store for copying and pasting within the agent’s session. This prevents overwriting the user’s system clipboard.
 3. Disable or Restrict these actions if you run in multi-user or production mode.

2.4 Logging Sensitive Data

Where

- Various scripts log LLM responses or user tasks.
- utils.py and other files read environment variables for API keys.

Risks

 1. API Keys in Logs: If you ever log environment variables, they might contain secrets (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY).
 2. Conversation Logs: LLM or browser actions might contain personal info or private data from pages the agent visits.

Recommendations

 1. Scrub Sensitive Info: Use partial redaction to log environment variables or user data.
 2. Control Log Levels: Keep debug logs for local dev; avoid them in production or store them in a secure location.
 3. Never commit or print raw API keys or user credentials.

2.5 Environment Variables for API Keys

Where

- utils.py reads OPENAI_API_KEY, ANTHROPIC_API_KEY, AZURE_OPENAI_API_KEY, etc.

Risks

 1. Credentials Leak: Others might read if environment variables are insecurely stored or the machine is multi-tenant.
 2. Rotation & Auditing: It is harder to rotate if you embed them in environment variables in multiple places.

Recommendations

 1. Use a Secret Manager: For production, store keys in Vault, AWS Secrets Manager, or a similar service, injecting them at runtime with minimal exposure.
 2. Lock Down or Mask your environment variables in logs.

2.6 Handling of Cookies & Persisted Sessions

Where

- custom_context.py loads cookies from a file and reuses them if cookies_file is set.

Risks

 1. Cookie Theft: Cookies containing session tokens can be used to impersonate or access accounts.
 2. Insecure Storage: If cookies_file is not locked down or is in a publicly accessible directory, attackers could read it.

Recommendations

 1. Encrypt or Secure the cookie file if it’s sensitive.
 2. Use ephemeral sessions if you don’t need persistence (this mitigates the risk of session hijacking).
 3. Handle JSON Errors gracefully. The code might crash if the cookie file is corrupted or maliciously edited. Currently, you catch some exceptions, but be sure they are robust.

2.7 LLM Output Execution

Where

- custom_agent.py uses the LLM output to determine subsequent actions in the browser. This is effectively arbitrary remote code controlling the browser if the LLM’s output is invalid.

Risks

 1. Prompt Injection or Malicious LLM Output: If an attacker can manipulate the prompt or the LLM’s instructions, they might cause harmful browsing actions (e.g., navigating to malicious pages, downloading malicious content, or exfiltrating data).
 2. Excessive Trust: The agent automatically performs actions the LLM says. If the LLM is compromised or intentionally producing malicious JSON, your system might become an attack vector.

Recommendations

 1. Policy Layer: Before executing each action, you can add checks to ensure it’s within a set of “allowed” domains or “allowed action types.”
 2. Safe Browsing: You could block navigation to known malicious or undesired domains.
 3. Sandboxes: Run the browser in a locked-down Docker container or VM so the environment is contained even if the LLM instructs to visit a malicious link.

2.8 Untrusted Web Content & Vision

Where

- The agent uses optional “vision-based element detection” or page screenshots.

Risks

 1. Malicious Images: If the agent processes images from untrusted sources, ensure it’s safe from typical image library exploits (PIL is relatively safe, but keep it updated).
 2. Screenshot capturing: If you store or send screenshots, you risk inadvertently capturing personal data or content.

Recommendations

 1. Use the Latest Libraries: Keep PIL (pillow) updated to avoid known vulnerabilities in image parsing.
 2. Handle Storage: If you store screenshots, do so in secure, short-lived storage with restricted access.

 3. Summary of Key Security Practices

Based on the potential issues above, here’s a short checklist to ensure your system remains secure:

 1. Networking & Ports:

- Bind remote debugging to 127.0.0.1 only.
- Use firewalls or SSH tunnels if remote access is necessary.

 2. Sandboxing:

- Use Docker or a VM for your automation environment.
- Avoid --disable-web-security in production, or keep it in an isolated environment if you must use it.

 3. Logging & Secrets:

- Never log API keys or raw environment variables.
- Redact sensitive info in logs.
- Use a secret manager to store credentials.

 4. Clipboard & Persistence:

- Limit usage of system clipboard actions or implement an in-memory approach.
- If session data/cookies are reused, ensure the file and directory permissions are locked down.

 5. LLM Output Validation:

- Consider a “policy layer” that checks which actions are allowed before executing them.
- Consider domain safelisting or an interactive approval step in critical scenarios.

 6. Error Handling:
 •  - Gracefully handle invalid JSON, cookies, or environment variables.

- Decide if you want to continue or fail fast with an error message.

 7. Document your single-agent approach:

- The singleton approach is fine if you never plan multiple concurrent agents.
- Otherwise, remove it or ensure concurrency safety.

 4. Verifying Project Structure

From a structural standpoint:

 1. Modular & Readable: Your project is decently modular: custom_agent, custom_browser, custom_context, custom_controller, custom_prompts, etc.
 2. Dependencies: You rely on Playwright. async_api, pyperclip, requests, and custom browser_use and langchain _* modules. Ensure they are pinned to known-safe versions (e.g., in a requirements.txt) and kept updated.
 3. Single vs. Multi Agent: In your README or main docs, clarify that you run only one agent at a time or concurrency is in scope.
 4. Deployment: If you distribute or deploy this server, outline the usage of environment variables, the required ports, and the recommended containerization approach.

 5. Conclusion

Your codebase is well-organized and functionally robust. The main security concerns revolve around:

- Remote Debugging & Disabling Security** in Chrome.
- Clipboard & Cookie usage.
- LLM output leading to potentially dangerous actions if not validated.
- Logging & environment variables containing sensitive data.

You can mitigate most of these risks by containerizing or VM-isolating your environment, restricting your debugging port to localhost, carefully handling credentials and logs, and implementing a minimal policy layer for LLM-driven actions.

The project is in good shape, but you should document these security measures and carefully configure them, especially in environments other than internal development.

Next Steps:

- Implement or strengthen the recommended mitigation steps above.
- Periodically review dependencies for security patches.
- If this is a production-grade service, consider formal penetration testing or a threat model exercise to identify additional risks.
- Keep documentation clear about the single-agent design and environment variables, and recommend using a container or ephemeral environment to prevent lateral movement or data exfiltration.
