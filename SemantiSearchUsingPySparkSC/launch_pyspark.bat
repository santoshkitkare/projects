@echo off
REM === Temporary environment setup for PySpark ===
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17
set SPARK_HOME=E:\Workspace\semantic-search-pyspark-n-sc\projects\SemantiSearchUsingPySparkSC\py311\Lib\site-packages\pyspark
set PATH=%JAVA_HOME%\bin;%SPARK_HOME%\bin;%PATH%

echo JAVA_HOME=%JAVA_HOME%
echo SPARK_HOME=%SPARK_HOME%

echo Running PySpark preprocessing script...
"%SPARK_HOME%\bin\spark-submit.cmd" scripts\preprocess_pyspark.py

pause
