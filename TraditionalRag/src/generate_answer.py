from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from retrieve_faiss import load_faiss_index, load_metadata, retrieve_similar_chunks

def generate_answer(query, top_k=3):
    """
    Retrieves relevant chunks and generates a final answer.
    """
    # Load FAISS index and metadata
    index = load_faiss_index()
    text_chunks = load_metadata()

    # Retrieve top relevant chunks
    context_chunks = retrieve_similar_chunks(query, index, text_chunks, top_k=top_k)
    context = "\n\n".join(context_chunks)

    # Load open-source LLM
    print("Loading LLM...")
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    # Load tokenizer and model, using a device map for efficient loading
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")

    # Build the prompt
    prompt = f"""
    Context:
    {context}
    Question:
    {query}
    Answer:
    """

    # Generate output
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    # Use the correct input for model generation
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=200, pad_token_id=tokenizer.eos_token_id)
    
    # Decode and clean up the answer, removing the original prompt
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Simple way to remove the prompt part from the output
    answer = full_text.split("Answer:")[1].strip() if "Answer:" in full_text else full_text.strip()
    
    print("\nFinal Answer:")
    print(answer)