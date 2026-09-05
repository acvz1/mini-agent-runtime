class AgentError(Exception):
    """Base error for the mini agent runtime."""


class MaxTurnsExceeded(AgentError):
    """Loop hit the configured max turn limit without a final answer."""


class ParseError(AgentError):
    """LLM output could not be interpreted."""


class LLMError(AgentError):
    """LLM API call failed."""


class UnknownToolError(AgentError):
    """Requested tool is not registered."""
