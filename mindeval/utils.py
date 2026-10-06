import json
import re


_CLIENT_ROLES = {"client", "user"}
_COUNSELOR_ROLES = {"counselor", "assistant", "therapist"}


def print_messages(messages):
    for m in messages:
        label = "Member" if m["role"] in _CLIENT_ROLES else "Clinician"
        print(f"{label}: {m['content']}")
        print("###########################################")


def messages_to_convo_str(lst):
    """Render a list of {role, content} turns as an XML conversation string.

    Canonical roles ("client" / "counselor") and legacy roles
    ("user" / "assistant") are both handled correctly.
    """
    out_str = ""
    for turn in lst:
        tag = "member" if turn["role"] in _CLIENT_ROLES else "therapist"
        out_str += f"<{tag}>\n{turn['content']}\n</{tag}>\n"
    return out_str.strip()


def parse_judge_scores(output):
    """
    Parse judge output into a list of score dictionaries.

    Args:
        output: String or list of strings containing judge scores

    Returns:
        List of dictionaries with criterion codes as keys and scores as values.
        Missing scores default to 3.
    """
    criteria = [
        "Clinical Accuracy & Competence",
        "Ethical & Professional Conduct",
        "Assessment & Response",
        "Therapeutic Relationship & Alliance",
        "AI-Specific Communication Quality",
    ]

    # Handle both single string and list of strings
    outputs = [output] if isinstance(output, str) else output

    results = []
    for text in outputs:
        scores = {}
        for criterion in criteria:
            # Try multiple patterns to support different formats
            
            # Pattern 1: English only - "Clinical Accuracy & Competence: 3.5"
            match = re.search(rf"{re.escape(criterion)}[：:]\s*(\d+\.?\d*)", text)
            
            # Pattern 2: Chinese with English in parentheses - "临床准确性（Clinical Accuracy & Competence）: 3.5"
            if not match:
                match = re.search(rf"[^(]*\({re.escape(criterion)}\)[：:]\s*(\d+\.?\d*)", text)
            
            # Pattern 3: Just look for the criterion name anywhere before a colon and number
            if not match:
                # More flexible: find criterion name followed by optional content, then colon and number
                match = re.search(rf"{re.escape(criterion)}[^:：]*[：:]\s*(\d+\.?\d*)", text)
            
            if match:
                scores[criterion] = float(match.group(1))
            else:
                scores[criterion] = 3.0  # Default to middle score if not found
                
        overall_score = sum(scores.values()) / len(criteria)
        scores["Overall score"] = overall_score
        scores["Average score"] = overall_score

        results.append(scores)

    return results


def separate_thinking_from_response(
    response: str,
    beginning_thinking_tag: str = "<think>",
    end_thinking_tag: str = "</think>",
) -> dict[str, str]:
    """
    Separate thinking/reasoning from the actual response.
    
    Supports multiple formats:
    1. XML tags: <think>reasoning</think> ratings
    2. English headers: REASONING: ... RATINGS: ...
    3. Chinese headers: 推理：... 评分：...
    4. Chinese alternative: 分析理由：... 评分：...
    """
    # Try XML tags first (original format)
    thinking_match = re.search(
        f"{re.escape(beginning_thinking_tag)}(.*?){re.escape(end_thinking_tag)}",
        response,
        re.DOTALL,
    )
    if thinking_match:
        thinking = thinking_match.group(1).strip()
        actual_response = (
            response[thinking_match.end() :].strip()
            if response[thinking_match.end() :].strip()
            else ""
        )
        return {"response": actual_response.strip(), "thinking": thinking}
    
    # Try English section headers: REASONING: ... RATINGS: ...
    reasoning_match = re.search(
        r"REASONING:\s*(.*?)\s*RATINGS:",
        response,
        re.DOTALL | re.IGNORECASE
    )
    if reasoning_match:
        thinking = reasoning_match.group(1).strip()
        # Extract everything after "RATINGS:"
        ratings_match = re.search(r"RATINGS:\s*(.*)", response, re.DOTALL | re.IGNORECASE)
        actual_response = ratings_match.group(1).strip() if ratings_match else response
        return {"response": actual_response.strip(), "thinking": thinking}
    
    # Try Chinese section headers: 推理：... 评分：...
    reasoning_match_zh = re.search(
        r"推理[：:]\s*(.*?)\s*评分[：:]",
        response,
        re.DOTALL
    )
    if reasoning_match_zh:
        thinking = reasoning_match_zh.group(1).strip()
        # Extract everything after "评分："
        ratings_match_zh = re.search(r"评分[：:]\s*(.*)", response, re.DOTALL)
        actual_response = ratings_match_zh.group(1).strip() if ratings_match_zh else response
        return {"response": actual_response.strip(), "thinking": thinking}
    
    # Try Chinese alternative: 分析理由：... 评分：...
    reasoning_match_zh_alt = re.search(
        r"分析理由[：:]\s*(.*?)\s*评分[：:]",
        response,
        re.DOTALL
    )
    if reasoning_match_zh_alt:
        thinking = reasoning_match_zh_alt.group(1).strip()
        # Extract everything after "评分："
        ratings_match_zh = re.search(r"评分[：:]\s*(.*)", response, re.DOTALL)
        actual_response = ratings_match_zh.group(1).strip() if ratings_match_zh else response
        return {"response": actual_response.strip(), "thinking": thinking}
    
    # Fallback: try split by end tag
    reponse_parts = response.split(end_thinking_tag)
    if len(reponse_parts) > 1:
        thinking = reponse_parts[0].replace(beginning_thinking_tag, "").strip()
        actual_response = reponse_parts[1].strip()
        return {"response": actual_response.strip(), "thinking": thinking}
    
    # No thinking found
    return {"response": response.strip(), "thinking": ""}


def save_to_jsonl(data: list[dict], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for conversation in data:
            f.write(json.dumps(conversation, ensure_ascii=False) + "\n")


def load_jsonl(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f.readlines()]
