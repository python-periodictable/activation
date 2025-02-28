#!/bin/sh
#ROOT=https://www-nds.iaea.org/public/download-endf/ENDF-B-VII.1/n
#DATA=ENDF-B-VII.1
ROOT=https://www-nds.iaea.org/public/download-endf/ENDF-B-VIII.1/n/
DATA=ENDF-B-VIII.1
test ! -d $DATA && mkdir $DATA
for f in `cat isotopes_$DATA.txt`; do
    echo "++ $f";
    curl $ROOT/$f > $DATA/$f;
done
