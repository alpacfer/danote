from __future__ import annotations


def single_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {"translation": {"type": "STRING", "nullable": True}},
            "required": ["translation"],
        },
        temperature=0,
        max_output_tokens=64,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def batch_response_config(genai_types, *, item_count: int) -> object:
    max_output_tokens = min(2048, max(128, item_count * 48))
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "translation": {"type": "STRING", "nullable": True},
                        },
                        "required": ["id", "translation"],
                    },
                }
            },
            "required": ["items"],
        },
        temperature=0,
        max_output_tokens=max_output_tokens,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def meaning_section_selection_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {"meaning_section_id": {"type": "INTEGER", "nullable": True}},
            "required": ["meaning_section_id"],
        },
        temperature=0,
        max_output_tokens=64,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def batch_meaning_section_selection_response_config(genai_types, *, item_count: int) -> object:
    max_output_tokens = min(2048, max(128, item_count * 32))
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "meaning_section_id": {"type": "INTEGER", "nullable": True},
                        },
                        "required": ["id", "meaning_section_id"],
                    },
                }
            },
            "required": ["items"],
        },
        temperature=0,
        max_output_tokens=max_output_tokens,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def alternative_translations_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "primary_translation": {"type": "STRING", "nullable": True},
                "alternative_translations": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["primary_translation", "alternative_translations"],
        },
        temperature=0,
        max_output_tokens=128,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def example_sentence_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "source_text": {"type": "STRING"},
                "english_translation": {"type": "STRING"},
            },
            "required": ["source_text", "english_translation"],
        },
        temperature=0.7,
        max_output_tokens=160,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def non_cor_word_generation_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0,
        max_output_tokens=256,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def batch_non_cor_word_generation_response_config(genai_types, *, item_count: int) -> object:
    del item_count
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0,
        max_output_tokens=1024,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def non_cor_variations_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0,
        max_output_tokens=512,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )
