import json
import os
import subprocess
import sys


def test_cli_subprocess(tmp_path):
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = dict(os.environ, PYTHONPATH=os.path.join(root, "src"))
    output = tmp_path / "output.json"
    result = subprocess.run([sys.executable, "-m", "axiom", "run", "--seed", "1",
                             "--candidates", "12", "--domain", "polynomial", "--db", str(tmp_path / "temp.db"),
                             "--report", str(output)], capture_output=True, text=True, env=env, check=True)
    stdout = json.loads(result.stdout)
    assert stdout["progress"]["complete"]
    assert json.loads(output.read_text())["campaign_id"] == stdout["campaign_id"]
