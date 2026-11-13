"""Print ``[[files]]`` manifest entries for the files in a dataset folder.

Run with ``just hash-files <folder>``. Paste the output into the folder's ``dataset.toml``, then mark the
main file ``primary = true``.
"""

import hashlib
import sys
from pathlib import Path


def main(folder: Path) -> None:
    """Print an entry for each file in ``folder`` except the manifest."""
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.name != "dataset.toml":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            print(f'[[files]]\nname = "{path.name}"\nsha256 = "{digest}"\nsize = {path.stat().st_size}\n')


if __name__ == "__main__":
    main(Path(sys.argv[1]))
