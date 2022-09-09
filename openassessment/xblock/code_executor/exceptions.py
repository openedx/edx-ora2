class CodeCompilationError(Exception):
    def __init__(self, message: str = None, *args: object) -> None:
        super().__init__(*args)
        self.message = message


class WorkingDirectoryNotInitializedException(Exception):
    def __init__(self, message: str = None, *args: object) -> None:
        super().__init__(*args)
        self.message = message
