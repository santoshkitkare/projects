import faiss
from sentence_transformers import SentenceTransformer


def init_models_n_faise_index():
    # Setup Sentence Transformer model
    sc_model = SentenceTransformer("all-MiniLM-L6-v2")
    sc_model_dim = sc_model.get_sentence_embedding_dimension()

    # Faiss index and Sentence transformer model
    index = faiss.IndexFlatL2(sc_model_dim)
    return sc_model, index


def embed_docs(sc_model, docs, f_index, documents_list, metadata_list):
    for _index, doc in enumerate(docs):
        # Get embedding
        embed = sc_model.encode([doc]).astype("float32")
        f_index.add(embed)

        documents_list.append(doc)
        metadata_list.append({
            "index": _index,
            "length": len(doc),
            "topic": doc.split()[0]
        })

    return f_index, documents_list, metadata_list


def get_matching_documents(query, sc_model, f_index, documents, metadata):
    query_embed = sc_model.encode([query]).astype("float32")
    distance, idx = f_index.search(query_embed, 3)
    results = []
    for rank, index in enumerate(idx[0]):
        result = {
            "rank": rank,
            "index": index,
            "score": distance[0][rank],
            "doc" : documents[index],
            "metadata" : metadata[index],
        }
        results.append(result)

    return results


if __name__ == "__main__":
    # Local storage for document and metadata
    documents = []
    metadata = []

    docs = [
        "AWS CloudWatch enables centralized logging, metrics, and observability pipelines for distributed workloads.",
        "Amazon DynamoDB is a fully managed NoSQL key-value database with millisecond-level performance at scale.",
        "Amazon API Gateway provides secure and scalable API endpoints with built-in throttling, caching, and authorization.",
        "AWS CloudFormation automates infrastructure provisioning using declarative templates for repeatability.",
        "Amazon ElastiCache delivers in-memory caching using Redis or Memcached to accelerate application performance.",
        "AWS VPC enables logically isolated network environments with subnets, routing, and security controls.",
        "Route 53 is a highly available DNS and traffic routing service with health checks and geo-routing.",
        "Amazon ECR is a fully managed Docker image registry optimized for ECS, EKS, and CI/CD pipelines.",
        "AWS KMS provides encrypted key management with fine-grained access control and auditing.",
        "AWS Step Functions orchestrate serverless workflows with state machines and error-handling logic."
    ]

    sc_model, faiss_index = init_models_n_faise_index()

    f_index, documents, metadata = embed_docs(sc_model, docs, faiss_index, documents, metadata)

    query = "What is AWS Cloudformation?"
    results = get_matching_documents(query, sc_model, f_index, documents, metadata)

    print("Matching documents are:")
    for _ind, data in enumerate(results):
        print(f'=========== Rank: {_ind} =============')
        print(f'Rank : {data["rank"]}')
        print(f'Score : {data["score"]}')
        print(f'Document index: {data["index"]}')
        print(f'Document: {data["doc"]}')
        print(f'Metadata: {data["metadata"]}')
