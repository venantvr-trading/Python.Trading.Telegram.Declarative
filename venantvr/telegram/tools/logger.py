import logging
import os
import sys
from logging.handlers import WatchedFileHandler

from venantvr.telegram.tools.stream import StreamToLogger


def setup_logging(log_level=logging.INFO):
    # Configuration du logger principal
    log = logging.getLogger("runtime")
    log.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Création de StreamHandler pour la sortie console
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    # Rediriger stdout et stderr vers le logger
    sys.stdout = StreamToLogger(log, logging.INFO)
    sys.stderr = StreamToLogger(log, logging.ERROR)

    return log


# Fonction pour récupérer le formatter d'un handler spécifique
def get_formatter(runtime_logger, handler_type):
    for handler in runtime_logger.handlers:
        if isinstance(handler, handler_type):
            return handler.formatter  # Retourne le formatter du handler trouvé
    return None  # Retourne None si aucun handler du type spécifié n'est trouvé


def configure_stream(runtime_logger, log_file: str):
    # Vérifier que le log_file n'est pas vide
    if not log_file:
        raise ValueError("Le chemin du fichier de log ne peut pas être vide")

    # Créer l'arborescence du répertoire si elle n'existe pas
    log_directory = os.path.dirname(log_file)
    os.makedirs(log_directory, exist_ok=True)

    watched_handler = WatchedFileHandler(log_file)
    watched_handler.setLevel(logging.INFO)
    formatter = get_formatter(logger, logging.StreamHandler)
    watched_handler.setFormatter(formatter)

    # Supprimer les anciens handlers de fichier pour éviter les doublons
    runtime_logger.handlers = [h for h in runtime_logger.handlers if not isinstance(h, WatchedFileHandler)]

    # Ajouter le nouveau handler de fichier
    runtime_logger.addHandler(watched_handler)


logger = setup_logging()
