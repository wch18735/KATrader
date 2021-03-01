@ECHO ON
title Kiwoom Start

cd D:\github\KATrader

call C:/Users/wch18/Anaconda3/Scripts/activate.bat
call conda activate SmallHTS
python __init__.py

cmd.exe