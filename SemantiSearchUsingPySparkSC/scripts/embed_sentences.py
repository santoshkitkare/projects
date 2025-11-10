from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, FloatType
from sentence_transformers import SentenceTransformer

spark = SparkSession.builder.appName("ComplaintEmbeddings").getOrCreate()
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text):
    return model.encode(text).tolist()

embed_udf = udf(embed_text, ArrayType(FloatType()))

df = spark.read.parquet("data/cleaned_complaints.parquet")
df_emb = df.withColumn("embedding", embed_udf(df["complaint_text"]))

df_emb.write.mode("overwrite").parquet("data/embedded_complaints.parquet")
spark.stop()

print("✅ Embeddings generated and saved at data/embedded_complaints.parquet")
