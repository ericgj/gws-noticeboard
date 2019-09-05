class UnknownCommandError(Exception):
    def __init__(self, command):
        self.command_type = (command.__class__.__name__,)
        self.command = (
            command.to_json() if hasattr(command, "to_json") else str(command)
        )

    def __str__(self):
        return "Unknown command: '%s'" % (self.command_type,)
