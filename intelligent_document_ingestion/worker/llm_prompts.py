def build_metadata_prompt(doc_type: str, text: str, page_count: int | None) -> str:
    base = f"Document type: {doc_type}\nPage count: {page_count}\n\n"
    base += "You must return ONLY valid JSON, no explanation.\n"

    if doc_type == "Question Paper":
        return base + """
Extract the following fields as JSON for a question paper:

{
  "documentType": "Question Paper",
  "examName": "<string or null>",
  "subject": "<string or null>",
  "gradeOrClass": "<string or null>",
  "totalMarks": "<number or null>",
  "duration": "<string or null>",
  "numQuestions": "<number or null>",
  "topics": ["<string>", "..."],
  "instructionsSummary": "<short summary string>",
  "language": "<e.g. English, Hindi>",
  "shortSummary": "<2-3 sentence summary>"
}

Use null when you are unsure.
Here is the document text (partial or full):
\"\"\"""" + text[:8000] + "\"\"\""

    if doc_type == "Research Paper":
        return base + """
Extract the following fields as JSON for a research paper:

{
  "documentType": "Research Paper",
  "title": "<string or null>",
  "authors": ["<string>", "..."],
  "affiliations": ["<string>", "..."],
  "publicationVenue": "<journal/conference or null>",
  "year": "<number or null>",
  "abstract": "<string or null>",
  "keywords": ["<string>", "..."],
  "domain": "<e.g. Physics, AI, Biology>",
  "conclusionSummary": "<short summary>",
  "shortSummary": "<2-3 sentence summary>"
}

Use null when unsure.
Text:
\"\"\"""" + text[:8000] + "\"\"\""

    if doc_type == "Invoice":
        return base + """
Extract the following fields as JSON for an invoice:

{
  "documentType": "Invoice",
  "invoiceNumber": "<string or null>",
  "invoiceDate": "<string or null>",
  "dueDate": "<string or null>",
  "supplierName": "<string or null>",
  "supplierAddress": "<string or null>",
  "customerName": "<string or null>",
  "customerAddress": "<string or null>",
  "currency": "<string or null>",
  "totalAmount": "<number or null>",
  "taxAmount": "<number or null>",
  "lineItems": [
    {
      "description": "<string or null>",
      "quantity": "<number or null>",
      "unitPrice": "<number or null>",
      "lineTotal": "<number or null>"
    }
  ],
  "shortSummary": "<1-2 sentence summary>"
}

Use null when unsure. Do not guess amounts wildly.
Text:
\"\"\"""" + text[:8000] + "\"\"\""

    if doc_type == "Information Document":
        return base + """
Extract the following fields as JSON for an informational document (article, note, report, etc.):

{
  "documentType": "Information Document",
  "title": "<string or null>",
  "authorOrSource": "<string or null>",
  "category": "<e.g. Article, Report, Policy, Manual>",
  "mainTopics": ["<string>", "..."],
  "shortSummary": "<3-4 sentence summary>",
  "keyPoints": ["<bullet point strings>", "..."],
  "namedEntities": {
    "people": ["<string>", "..."],
    "organizations": ["<string>", "..."],
    "locations": ["<string>", "..."]
  }
}

Use null or [] when unsure.
Text:
\"\"\"""" + text[:8000] + "\"\"\""

    # Fallback
    return base + """
Return this JSON:

{
  "documentType": "To be supported",
  "shortSummary": "Document type not yet supported.",
  "rawTextPreview": "<first 500 characters of text>"
}

Text:
\"\"\"""" + text[:8000] + "\"\"\""
