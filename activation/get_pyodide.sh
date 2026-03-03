# !/bin/bash

# Run in the activation directory (where this script lives)
cd "$(dirname "$0")"

# Default version of pyodide to download if not set via environment variable
PYODIDE_VERSION=${PYODIDE_VERSION:-0.29.3}

rm -rf pyodide
mkdir pyodide

# Get the core pyodide files first (this is smaller and faster to download than the full version)
curl -L https://github.com/pyodide/pyodide/releases/download/${PYODIDE_VERSION}/pyodide-core-${PYODIDE_VERSION}.tar.bz2 -o pyodide.tar.bz2
          tar -xjf pyodide.tar.bz2 -C ./pyodide --strip-components=1

# Download the full version to get the specific wheels we need (numpy, pytz, micropip)
curl -L https://github.com/pyodide/pyodide/releases/download/${PYODIDE_VERSION}/pyodide-${PYODIDE_VERSION}.tar.bz2 -o pyodide_full.tar.bz2

# Extract only the core runtime + our specific wheels
TAR_OPTIONS="--wildcards" tar -xjf pyodide_full.tar.bz2 "*micropip-*.whl" "*numpy-*.whl" "*pytz-*.whl" "*pyparsing-*.whl"

# Download the latest periodictable wheel from PyPI
pip3 download periodictable --no-deps --only-binary :all: -d ./pyodide/

# Write out the full wheel file name to a text file for use in the workflow
ls pyodide/periodictable-*.whl > periodictable_wheel_name.txt

# Cleanup
rm -f pyodide.tar.bz2
rm -f pyodide_full.tar.bz2
