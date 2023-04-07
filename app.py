from ast import Try
import logging
import shutil
import time
import yaml
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ConfigHandler(FileSystemEventHandler):
    """Reload observer after config file modified."""

    def __init__(self, observer, filename: str = "config.yaml"):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.app_path = Path(__file__).parent.resolve()

        self.observer = observer
        self.filename = filename
        self.load_config()

    def on_modified(self, event):
        if event.src_path.endswith(self.filename):
            self.logger.info("Config file modified, reloading configs...")
            # Reload configuration
            self.load_config()
            self.reload_observer()

    def load_config(self):
        config_file = self.app_path.joinpath(self.filename)
        stream = open(config_file, "r")
        configs = yaml.load(stream, Loader=yaml.FullLoader)

        if (
            configs is None
            or configs.get("source") is None
            or configs.get("target") is None
            or configs.get("rules") is None
        ):
            self.logger.error("Invalid config file")
            exit(1)

        self.configs = configs
        self.logger.info("Config file loaded: %s", config_file)

    def start_observer(self):
        source_path = Path(self.configs.get("source")).resolve()
        source_path.mkdir(parents=True, exist_ok=True)
        target_path = Path(self.configs.get("target")).resolve()
        target_path.mkdir(parents=True, exist_ok=True)

        event_handler = FileCreatedEventHandler(configs=self.configs)

        self.observer.schedule(self, self.app_path)
        self.observer.schedule(event_handler, source_path)
        self.observer.start()
        logging.info("Observer start watching: %s -> %s", source_path, target_path)

    def reload_observer(self):
        self.observer.unschedule_all()

        source_path = Path(self.configs.get("source")).resolve()
        target_path = Path(self.configs.get("target")).resolve()

        event_handler = FileCreatedEventHandler(configs=self.configs)

        self.observer.schedule(self, self.app_path)
        self.observer.schedule(event_handler, source_path)
        logging.info("Observer reloaded, watching: %s -> %s", source_path, target_path)


class FileCreatedEventHandler(FileSystemEventHandler):
    """Move new files by rules."""

    def __init__(self, configs: dict):
        super().__init__()

        self.logger = logging.getLogger(__name__)

        if (
            configs is None
            or configs.get("source") is None
            or configs.get("target") is None
            or configs.get("rules") is None
        ):
            self.logger.error("Invalid config file")
            exit(1)

        self.configs = configs
        self.source = self.configs.get("source") or "source"
        self.target = self.configs.get("target") or "target"
        self.rules = rules = self.configs.get("rules") or []
        self.suffix = suffix = self.configs.get("suffix")

        if suffix:
            if suffix.get("excludes"):
                self.logger.info("Exclude suffix: %s", suffix.get("excludes"))
            if suffix.get("includes"):
                self.logger.info("Include suffix: %s", suffix.get("includes"))

        self.logger.info("Matching %d rules:", len(rules))
        for rule in rules:
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

        suffix = self.suffix
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

        target_path = Path(self.target).resolve()

        for rule in self.rules:
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

    observer = Observer()
    config_handler = ConfigHandler(observer)
    config_handler.start_observer()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()
