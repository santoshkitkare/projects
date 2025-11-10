from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, trim

import os
from pyspark.sql import SparkSession

os.environ["HADOOP_HOME"] = "C:\\hadoop"
os.environ["hadoop.home.dir"] = "C:\\hadoop"
os.environ["SPARK_HOME"] = "C:\\Users\\santo\\Downloads\\spark-4.0.1-bin-hadoop3"
os.environ["JAVA_HOME"] = "C:\\Program Files\\Eclipse Adoptium\\jdk-17"
os.environ["HADOOP_OPTIONAL_TOOLS"] = "hadoop-aws"  # optional if using S3 later
os.environ["HADOOP_OPTS"] = "-Djava.library.path="

# 🔧 Disable native Hadoop library load
os.environ["HADOOP_COMMON_LIB_NATIVE_DIR"] = ""
os.environ["HADOOP_OPTS"] = "-Djava.library.path= -Dio.native.lib.available=false"

spark = (
    SparkSession.builder
    .master("local[*]")
    .appName("SemanticSearchPreprocess")
    .config("spark.hadoop.io.native.lib.available", "false")
    .config("spark.sql.execution.arrow.pyspark.enabled", "true")
    .getOrCreate()
)


# spark = SparkSession.builder.appName("ComplaintPreprocessing").getOrCreate()

# Load CSV
df = spark.read.csv("data/complaints.csv", header=True, inferSchema=True)

# Clean text
df_clean = df.withColumn("complaint_text", trim(lower(col("complaint_text"))))
df_clean = df_clean.filter(col("complaint_text").isNotNull())

# Save cleaned data
df_clean.write.mode("overwrite").parquet("data/cleaned_complaints.parquet")

spark.stop()
print("✅ Cleaned complaints saved at data/cleaned_complaints.parquet")
