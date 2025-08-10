class StreamToLogger:
    """
    Classe pour rediriger stdout et stderr vers un logger.
    """

    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.in_write = False  # Prévenir les boucles

    def write(self, message):
        if message.strip() and not self.in_write:
            try:
                self.in_write = True  # Empêche la récursion dans write
                self.logger.log(self.log_level, message.strip())
            finally:
                self.in_write = False

    def flush(self):
        pass  # Nécessaire pour la compatibilité avec sys.stdout et sys.stderr
