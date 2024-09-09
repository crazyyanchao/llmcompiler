

def get_custom_or_default(custom_prompts: dict[str, str], key: str, default_value: str) -> str:
    """Helper function to return custom prompt if available, otherwise default."""
    return custom_prompts[key] if custom_prompts and key in custom_prompts else default_value
