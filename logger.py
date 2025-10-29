# Template class for logging functionality
class Logger:
    def log(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def error(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def info(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def warning(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")


class ClientLogger(Logger):
    def log(self, message: str) -> None:
        print(f"Client - {message}")

    def error(self, message: str) -> None:
        print(f"Client - ERROR: {message}")

    def info(self, message: str) -> None:
        print(f"Client - INFO: {message}")

    def warning(self, message: str) -> None:
        print(f"Client - WARNING: {message}")


class ServerLogger(Logger):
    def log(self, message: str) -> None:
        print(f"Server - {message}")

    def error(self, message: str) -> None:
        print(f"Server - ERROR: {message}")

    def info(self, message: str) -> None:
        print(f"Server - INFO: {message}")

    def warning(self, message: str) -> None:
        print(f"Server - WARNING: {message}")