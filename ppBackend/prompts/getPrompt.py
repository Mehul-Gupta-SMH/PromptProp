

def getPrompt(promptName, promptType):
    """Fetches the content of a prompt file based on the prompt name and type."""
    if promptType == "system":
        with open(f"ppBackend/prompts/systemPrompts/{promptName}.txt", "r") as file:
            return file.read()
    elif promptType == "user":
        with open(f"ppBackend/prompts/userPrompts/{promptName}.txt", "r") as file:
            return file.read()
    else:
        raise ValueError("Invalid prompt type. Must be 'system' or 'user'.")