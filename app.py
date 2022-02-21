from ast import Try
import logging
import shutil
import yaml
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class FileCreatedEventHandler(FileSystemEventHandler):
    """Move new files by rules."""

    def __init__(self, logger=None, configs=None):
        super().__init__()

        self.logger = logger or logging.root
        self.configs = configs

    def on_created(self, event):
        super().on_created(event)

        what = "Directory" if event.is_directory else "File"
        self.logger.info("%s created: %s", what, event.src_path)

        if event.is_directory:
            return

        if self.configs is None:
            return

        source_path = Path(event.src_path)
        default_target_path = Path(self.configs.get("target")).resolve()

        suffix = self.configs.get("suffix")
        if suffix is not None and suffix.get("exclude") is None:
            for exclude in suffix.get("excludes"):
                if source_path.suffix.casefold() == str(exclude).casefold():
                    return

        rules = self.configs.get("rules")
        for rule in rules:
            if rule.get("keyword") is None:
                continue

            if not rule.get("keyword") in source_path.name:
                continue

            if rule.get("target"):
                target_path = Path(rule.get("target")).resolve()
            else:
                target_path = default_target_path

            if target_path.is_file():
                self.logger.warning("Target path is a file: %s", target_path)
                continue

            try:
                Path(target_path).mkdir(parents=True, exist_ok=True)
                shutil.move(event.src_path, target_path)
                self.logger.info("File moved: %s -> %s", event.src_path, target_path)
            except Exception as e:
                self.logger.error(e)

            return


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config_file = Path(__file__).parent.joinpath("config.yaml")
    stream = open(config_file, "r")
    configs = yaml.load(stream, Loader=yaml.FullLoader)

    if (
        configs is None
        or configs.get("source") is None
        or configs.get("target") is None
        or configs.get("rules") is None
    ):
        logging.error("Invalid config file")
        exit(1)

    source_path = Path(configs.get("source")).resolve()
    source_path.mkdir(parents=True, exist_ok=True)

    event_handler = FileCreatedEventHandler(configs=configs)
    observer = Observer()
    observer.schedule(event_handler, source_path, recursive=False)
    observer.start()
    logging.info("Watching: %s", source_path)

    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
