"""OpenClaw skill bootstrap for compras-divididas."""


def handle_command(command_text: str) -> str:
    """Handle a skill command with a bootstrap response."""
    normalized_command = command_text.strip()
    if not normalized_command:
        return "Provide a command to start a monthly closure."
    return f"compras-divididas skill received: {normalized_command}"
