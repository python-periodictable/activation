#!/bin/bash

TARGET_DIR=${TARGET_DIR:-/var/www/html/resources/activation}

# First, get the latest pyodide files and the specific periodictable wheel we need:
./activation/get_pyodide.sh

# Now copy all the necessary files to the target directory for deployment:
mkdir -p $TARGET_DIR
cp activation/jquery* $TARGET_DIR/
cp activation/*.js $TARGET_DIR/
cp activation/webworker.js $TARGET_DIR/
cp activation/favicon.ico $TARGET_DIR/
cp activation/periodictable_wheel_name.txt $TARGET_DIR/
cp cgi-bin/nact.py $TARGET_DIR/
cp activation/resonance.html $TARGET_DIR/
cp -r activation/pyodide/. $TARGET_DIR/pyodide
cp -r activation/css/. $TARGET_DIR/css

# generate the HTML table and write it to the target folder
python3 util/scattering_table_html.py $TARGET_DIR

# Get the version of periodictable from the wheel file name and write it to a text file for use in the workflow
PERIODICTABLE_VERSION=$(python3 -c "import periodictable; print(periodictable.__version__)")

# Write replacements in template
API_SUB="s@{{ api_script }}@api_webworker.js@g"
VER_SUB="s@{{ periodictable_version }}@$PERIODICTABLE_VERSION@g"
sed -e "$API_SUB;$VER_SUB" activation/index_template.html > "$TARGET_DIR/index.html"
