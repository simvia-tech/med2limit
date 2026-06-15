## Quick start

```bash
git clone <url> med2limit
cd med2limit
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python examples/01_shell_basic.py
```

The example converts `examples/data/exemple_01.rmed` to LIMIT format.
Outputs are written to `examples/data/example_01.linp` and `.lui`.