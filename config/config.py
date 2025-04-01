import glob
from dynaconf import Dynaconf  # type: ignore
from pathlib import Path

ROOT_DIR = Path(__file__).parent


__all__ = ("config", )


# find all files given a filepath pattern
def read_files(filepath: str) -> list:
    return glob.glob(filepath, root_dir=ROOT_DIR)


config = Dynaconf(
    settings_files=read_files("dev/config.toml"),
    core_loaders=["TOML"],  # toml as the config file format
    load_dotenv=True,  # enable loading .env file
    root_path=ROOT_DIR,
)
