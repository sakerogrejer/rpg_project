# Template class for logging functionality
import os
import time


class Logger:

    def __init__(self):
        self.datetime = time.strftime("%d/%m/%Y %H:%M:%S")
        # log file path log/{datetime}_log.txt
        folder = "logs/"
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass

        self.logfile = f"logs/{time.strftime('%Y%m%d_%H%M%S')}_log.txt"


    def log(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def error(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def info(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def warning(self, message: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def logfile(self, message: str) -> None:
        # Write to file, if file doesn't exist, create it
        with open(self.logfile, 'a') as f:
            f.write(f"{time.strftime('%H%M%S')}" + message + "\n")


class ClientLogger(Logger):

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Client - {message}"
        Logger.logfile(self, message)
        print(message)

    def error(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Client - ERROR: {message}"
        Logger.logfile(self, message)
        print(message)

    def info(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Client - INFO: {message}"
        Logger.logfile(self, message)
        print(message)

    def warning(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Client - WARNING: {message}"
        Logger.logfile(self, message)
        print(message)


class ServerLogger(Logger):
    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Server - {message}"
        Logger.logfile(self, message)
        print(message)

    def error(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Server - ERROR: {message}"
        Logger.logfile(self, message)
        print(message)

    def info(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Server - INFO: {message}"
        Logger.logfile(self, message)
        print(message)

    def warning(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        message = f"{timestamp} -> Server - WARNING: {message}"
        Logger.logfile(self, message)
        print(message)