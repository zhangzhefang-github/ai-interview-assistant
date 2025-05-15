import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def extract_capability_assessment_json(report_text: str) -> Optional[dict]:
    """Extracts the CANDIDATE_CAPABILITY_ASSESSMENT_JSON block from the report text, 
       even if wrapped in markdown json code blocks or with minor formatting issues."""
    if not report_text:
        logger.warning("extract_capability_assessment_json called with empty report_text.")
        return None
    
    json_string_to_parse = None
    try:
        # 1. Try to find it within a markdown ```json ... ``` block
        # This regex captures the content between the outermost curly braces of the target JSON structure.
        # It looks for the specific key "CANDIDATE_CAPABILITY_ASSESSMENT_JSON"
        # and ensures it's part of a larger JSON object within the markdown block.
        # The captured group (group 1) should be the complete JSON string like: '{ "CANDIDATE_CAPABILITY_ASSESSMENT_JSON": { ... } }'
        match = re.search(r'```json\s*({(?:[^{}]|{[^{}]*})*?"CANDIDATE_CAPABILITY_ASSESSMENT_JSON"(?:[^{}]|{[^{}]*})*?})\s*```', report_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            json_string_to_parse = match.group(1).strip()
            logger.debug(f"Method 1 (Markdown Block): Successfully extracted JSON string: {json_string_to_parse[:200]}...")
        else:
            logger.debug("Method 1 (Markdown Block): No match found. Trying fallback methods.")
            # Fallback 2: Try to find the JSON object directly if not in markdown
            # This looks for '{ "CANDIDATE_CAPABILITY_ASSESSMENT_JSON": ... }' structure
            # It tries to be robust to some leading/trailing non-JSON content around the specific block
            # by looking for the start of the JSON structure containing the key.
            
            # Correctly find the start of the JSON object that contains our key
            # The key itself might be nested, but the structure we expect from the prompt is
            # { "CANDIDATE_CAPABILITY_ASSESSMENT_JSON": { <ratings> } }
            # So we look for the start of this entire object.
            
            # Regex to find the start of '{"CANDIDATE_CAPABILITY_ASSESSMENT_JSON":' possibly with some whitespace
            # then try to match the full object based on brace counting.
            # This is a simplified version of brace matching; a full parser would be more robust here.
            
            outer_json_match = re.search(r'({\s*"CANDIDATE_CAPABILITY_ASSESSMENT_JSON"\s*:\s*{.*?}\s*})', report_text, re.DOTALL | re.IGNORECASE)
            if outer_json_match:
                json_string_to_parse = outer_json_match.group(1).strip()
                logger.debug(f"Method 2 (Direct Regex on Object): Successfully extracted JSON string: {json_string_to_parse[:200]}...")
            else:
                logger.debug("Method 2 (Direct Regex on Object): No match. Trying simpler key-based search with brace counting.")
                # Fallback 3: Simpler key-based search + brace counting (original fallback logic)
                key_marker = '"CANDIDATE_CAPABILITY_ASSESSMENT_JSON":' # Case sensitive as it's a JSON key
                key_start_index = report_text.find(key_marker)
                if key_start_index != -1:
                    # Search backwards for the opening brace of the object containing this key
                    json_object_start_index = report_text.rfind('{', 0, key_start_index)
                    if json_object_start_index != -1:
                        open_braces = 0
                        json_content_buffer = []
                        found_object = False
                        for char in report_text[json_object_start_index:]:
                            json_content_buffer.append(char)
                            if char == '{':
                                open_braces += 1
                            elif char == '}':
                                open_braces -= 1
                                if open_braces == 0:
                                    json_string_to_parse = "".join(json_content_buffer)
                                    logger.debug(f"Method 3 (Key + Brace Counting): Successfully extracted JSON string: {json_string_to_parse[:200]}...")
                                    found_object = True
                                    break
                        if not found_object:
                             logger.warning("Method 3 (Key + Brace Counting): Found key but failed to balance braces.")       
                    else:
                        logger.warning(f"Method 3 (Key + Brace Counting): Found key '{key_marker}' but no preceding '{{'.")
                else:
                    logger.info("All methods failed: CANDIDATE_CAPABILITY_ASSESSMENT_JSON key marker not found in report.")

        if json_string_to_parse:
            # Sanitize before parsing: e.g. remove trailing commas if any (though a good LLM shouldn't produce them in strict JSON)
            # For now, assume json.loads can handle it or the prompt ensures good JSON.
            parsed_data = json.loads(json_string_to_parse) 
            
            # The prompt requests the structure: { "CANDIDATE_CAPABILITY_ASSESSMENT_JSON": { ...ratings... } }
            # So, we directly return the inner dictionary containing the ratings.
            if isinstance(parsed_data, dict) and "CANDIDATE_CAPABILITY_ASSESSMENT_JSON" in parsed_data and isinstance(parsed_data["CANDIDATE_CAPABILITY_ASSESSMENT_JSON"], dict):
                logger.info("Successfully parsed and extracted CANDIDATE_CAPABILITY_ASSESSMENT_JSON block.")
                return parsed_data.get("CANDIDATE_CAPABILITY_ASSESSMENT_JSON")
            else:
                logger.warning(
                    f"Parsed JSON, but it does not match the expected structure. "
                    f"Expected a dict with key 'CANDIDATE_CAPABILITY_ASSESSMENT_JSON' whose value is also a dict. "
                    f"Got: {type(parsed_data)}, Keys (if dict): {list(parsed_data.keys()) if isinstance(parsed_data, dict) else 'N/A'}"
                )
                return None 
        else:
            logger.info("CANDIDATE_CAPABILITY_ASSESSMENT_JSON content string not successfully extracted from report.")
            return None

    except json.JSONDecodeError as e:
        json_snippet = json_string_to_parse[:200] + "..." if json_string_to_parse else "N/A"
        logger.error(f"JSONDecodeError: Failed to parse JSON from report - {e}. Extracted string snippet: '{json_snippet}'", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error during JSON extraction: {e}", exc_info=True)
        return None 