@CALL clean.bat

copy originals\Grid.fla to_convert

REM python conversion.py -source fla -xml to_convert\Grid.fla
python conversion.py -source fla -xml -dat to_convert\Grid.fla
