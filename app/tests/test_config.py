from pathlib import Path

from app.core.config import Settings


def test_settings_load_environment_from_backend_directory():
    assert Settings.model_config["env_file"] == Path(__file__).resolve().parents[2] / ".env"
