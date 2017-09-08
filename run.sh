#!/usr/bin/env bash

./clean.sh

python2.7 inspection.py original inspection-pre.json
python2.7 conversion.py -source dir -xml original
#python2.7 conversion.py -source fla -xml -dat original/Grid.fla
python2.7 inspection.py original inspection-post.json
