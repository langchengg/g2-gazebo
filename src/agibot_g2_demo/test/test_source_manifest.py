"""Release inputs must remain source-only even when accidental assets appear."""
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / 'scripts'
sys.path.insert(0, str(SCRIPTS if SCRIPTS.exists() else Path('/opt/demo/scripts')))
from source_manifest import manifest


@pytest.mark.parametrize('name', ['mesh.obj', 'robot.usdc', 'secret.pem', '.env.production'])
def test_release_rejects_accidental_model_or_secret(tmp_path, name):
    directory = tmp_path / 'src'
    directory.mkdir()
    (directory / name).write_text('not a release input')
    with pytest.raises(ValueError, match='cannot be delivered'):
        manifest(tmp_path, 'delivery')
