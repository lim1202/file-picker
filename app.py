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

        if (
            self.configs is None
            or self.configs.get("source") is None
            or self.configs.get("target") is None
            or self.configs.get("rules") is None
        ):
            self.logger.error("Invalid config file")
            exit(1)

        suffix = self.configs.get("suffix")
        if suffix:
            if suffix.get("excludes"):
                self.logger.info("Exclude suffix: %s", suffix.get("excludes"))
            if suffix.get("includes"):
                self.logger.info("Include suffix: %s", suffix.get("includes"))

        rules = self.configs.get("rules")
        self.logger.info("Matching %d rules:", len(rules))
        for rule in self.configs.get("rules"):
            self.logger.info(
                "- Keyword: '%s' -> Folder: '%s'",
                rule.get("keyword"),
                rule.get("folder"),
            )

    def on_created(self, event):
        super().on_created(event)

        what = "Directory" if event.is_directory else "File"
        self.logger.info("%s created: %s", what, event.src_path)

        if event.is_directory:
            return

        source_path = Path(event.src_path)

        suffix = self.configs.get("suffix")
        if suffix:
            if suffix.get("excludes"):
                for exclude in suffix.get("excludes"):
                    if source_path.suffix.casefold() == str(exclude).casefold():
                        return
            if suffix.get("includes"):
                included = False
                for include in suffix.get("includes"):
                    if source_path.suffix.casefold() == str(include).casefold():
                        included = True
                if not included:
                    return

        target_path = Path(self.configs.get("target")).resolve()

        rules = self.configs.get("rules")
        for rule in rules:
            if rule.get("keyword") is None:
                continue

            if not rule.get("keyword") in source_path.name:
                continue

            rule_target_path = target_path
            if rule.get("folder"):
                rule_target_path = target_path.joinpath(rule.get("folder")).resolve()

            if target_path.is_file():
                self.logger.warning("Target path is a file: %s", rule_target_path)
                continue

            try:
                Path(rule_target_path).mkdir(parents=True, exist_ok=True)
                shutil.move(event.src_path, rule_target_path)
                self.logger.info(
                    "File moved: %s -> %s", event.src_path, rule_target_path
                )
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

    logging.info("Configuration file loaded: %s", config_file)

    event_handler = FileCreatedEventHandler(configs=configs)

    source_path = Path(configs.get("source")).resolve()
    source_path.mkdir(parents=True, exist_ok=True)
    target_path = Path(configs.get("target")).resolve()
    target_path.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(event_handler, source_path)
    observer.start()

    logging.info("Start watching: %s -> %s", source_path, target_path)

    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
