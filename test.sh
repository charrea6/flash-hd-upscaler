#!/usr/bin/env bash

./clean.sh

cp -R originals/Grid.fla to_convert

python2.7 conversion.py -source fla -xml to_convert/Grid.fla

