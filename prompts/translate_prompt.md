Translate the provided note title and content into the requested target language.
Preserve the original meaning, tone, and useful formatting. Do not add commentary,
explanations, or information that is not present in the source.

Return only one valid JSON object with exactly these two string fields:
{"title":"translated title","content":"translated content"}

Do not wrap the JSON in Markdown fences. Escape quotation marks and other special
characters as required by JSON. If a source field is empty, keep its translated
field empty.