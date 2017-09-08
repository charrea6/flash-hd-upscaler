@CALL clean.bat

copy originals\*.* to_convert

REM python conversion.py -source fla -xml to_convert\Grid.fla
python conversion.py -source dir -xml -dat to_convert
