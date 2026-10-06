"""
WAI Evaluator — Detailed Guidelines + CoT (English prompts, S3 setting)
=======================================================================

Reproduces the best-performing setup from Li et al. (2024),
"Understanding the Therapeutic Relationship between Counselors and Clients
in Online Text-based Counseling using LLMs" (Findings of EMNLP 2024,
arXiv:2402.11958), Section 5 + Figure 5 + Appendix A.3.

Pipeline (matches Table 5 of the paper):

    For each conversation:
        For each Qi in Q1..Q12:
            Call LLM `n_runs` times (default 3, temperature 1.0)
            score_Qi = mean(individual scores)
        Goal           = mean(score_Q1, score_Q2, score_Q3, score_Q4)
        Approach       = mean(score_Q5, score_Q6, score_Q7, score_Q8)
        Affective_Bond = mean(score_Q9, score_Q10, score_Q11, score_Q12)
        Total          = mean(Goal, Approach, Affective_Bond)

Batch mode (default, batch=True):
    All 12 questions are sent in ONE LLM call per run → 3 calls/dialogue
    instead of 36.  Saves ~70 % input tokens while keeping the same CoT
    (evidence → analysis → score) for every question.

Per-question mode (batch=False):
    Original Li et al. approach: one call per question per run → 36 calls.
    Use when you need maximum isolation between questions.

Usage
-----
    See mindeval/scripts/generate_wai_judgments.py for the main entry point.
"""

from __future__ import annotations

import json
import re
import statistics
import time
from typing import Any

# ---------------------------------------------------------------------------
# Question wording — Table 1 (positive WAI-O-S framing)
# ---------------------------------------------------------------------------
QUESTIONS: dict[str, str] = {
    "Q1":  "There is mutual understanding about what participants are trying to accomplish in therapy.",
    "Q2":  "The client and counselor are working on mutually agreed upon goals.",
    "Q3":  "The client and counselor have same ideas about what the client's real problems are.",
    "Q4":  "The client and counselor have established a good understanding of the changes that would be good for the client.",
    "Q5":  "There is agreement about the steps taken to help improve the client's situation.",
    "Q6":  "There is agreement about the usefulness of the current activity in therapy (i.e., the client is seeing new ways to look at his/her problem).",
    "Q7":  "There is agreement on what is important for the client to work on.",
    "Q8":  "The client believes that the way they are working with his/her problem is correct.",
    "Q9":  "There is a mutual liking between the client and counselor.",
    "Q10": "The client feels confident in the counselor's ability to help the client.",
    "Q11": "The client feels that the counselor appreciates him/her as a person.",
    "Q12": "There is mutual trust between the client and counselor.",
}

DIMENSIONS: dict[str, list[str]] = {
    "Goal":           ["Q1",  "Q2",  "Q3",  "Q4"],
    "Approach":       ["Q5",  "Q6",  "Q7",  "Q8"],
    "Affective Bond": ["Q9", "Q10", "Q11", "Q12"],
}


# ---------------------------------------------------------------------------
# Aggregation helper — single shared implementation of the WAI run math.
# ---------------------------------------------------------------------------
def _aggregate_runs(all_run_results: list[dict[str, dict[str, Any]]],
                    n_runs: int) -> dict[str, Any]:
    """Aggregate completed WAI run results into a Judgment_Record structure.

    Mirrors ``evaluate_dialogue_batch``'s aggregation exactly so the parallel
    Sync_Path and the existing batch path produce byte-for-byte identical
    structures:

      * per-question score  = mean of that question's available run scores
                              (``None`` if no run produced a score)
      * per-dimension score = mean of its available constituent question scores
      * total               = mean of the available dimension scores

    Args:
        all_run_results: One entry per completed run, each a mapping
                         ``{qid -> {evidence, analysis, score}}``. Runs that
                         failed contribute no entry (they are simply absent).
        n_runs:          The configured number of runs (echoed into the record).

    Returns:
        ``{n_runs, questions, dimensions, total}`` where each ``questions[qid]``
        entry contains ``qid``, ``question``, ``score``, ``individual_scores``,
        and ``runs``.
    """
    # Aggregate per question
    per_q: dict[str, Any] = {}
    for qid in QUESTIONS:
        run_scores = [r[qid]["score"] for r in all_run_results if qid in r]
        mean_score = statistics.mean(run_scores) if run_scores else None
        per_q[qid] = {
            "qid": qid,
            "question": QUESTIONS[qid],
            "score": mean_score,
            "individual_scores": run_scores,
            "runs": [r.get(qid, {}) for r in all_run_results],
        }

    # Aggregate per dimension
    dim_scores: dict[str, float | None] = {}
    for dim, qids in DIMENSIONS.items():
        scs = [per_q[q]["score"] for q in qids if per_q[q]["score"] is not None]
        dim_scores[dim] = statistics.mean(scs) if scs else None

    valid_dims = [v for v in dim_scores.values() if v is not None]
    total = statistics.mean(valid_dims) if valid_dims else None

    return {
        "n_runs": n_runs,
        "questions": per_q,
        "dimensions": dim_scores,
        "total": total,
    }

# ---------------------------------------------------------------------------
# Detailed scoring guidelines — verbatim from Appendix A.3 of the paper.
# ---------------------------------------------------------------------------
DETAILED_GUIDELINES: dict[str, str] = {

    # ===== Goal =====

    "Q1": """\
1 = The counselor and the client have clearly identified different goals, and there are disagreements in the order of issues and solutions in therapy. This inconsistency may lead the client to express strong dissatisfaction with the overall counseling process and goals, possibly mentioning the reasons for participating in therapy. This could further trigger a negative reaction from the counselor. At this stage, it seems challenging for both parties to find common ground, making the therapeutic process difficult.

2 = There is disagreement between the counselor and the client regarding counseling goals. While there may be some communication between both parties, the counselor's specific tasks or interventions may be questioned or resisted by the client. The counseling may need to be paused multiple times to adjust the goals. The client may express overall dissatisfaction with the counseling. At this stage, the counselor may take on an "expert" role, sometimes overlooking the client's opinions or therapeutic ideas, and instances where the counselor guides but the client is not engaged may occur. The client may become less emotionally invested.

3 = There is no evidence to suggest that the counselor and the client have established consistent counseling goals, or there is an equal level of confusion and understanding regarding the goals.

4 = The counselor and the client do not explicitly mention the goals but are working towards a common objective. The counselor addresses the client's concerns immediately and adjusts the therapeutic process to meet the client's needs. The client is satisfied with the progress made.

5 = The counselor or the client explicitly mentions the counseling goals and works around the established objectives, such as understanding information related to the goals and methods to achieve them. The relevance of the dialogue to the goals is evident for both the counselor and the client. They may discuss the goals to acknowledge or comment on the usefulness of the therapeutic process.""",

    "Q2": """\
1 = The shift of topics often occurs abruptly, usually without mutual agreement from both parties. This frequent topic shift may result from one party interrupting or disregarding the other's statements. At this stage, significant conflicts exist between the counselor and the client regarding the appropriateness, definition, and boundaries of the goals, leading to confusion in the rhythm and content of the conversation.

2 = Topics may shift before resolution or conclusion, but the transition typically moves from one relevant topic to another related or less related one. This shift can be initiated by either the counselor or the client. At this stage, both parties may express dissatisfaction with the frequent shift of topics or the overall pace of therapy, but friction is relatively minor and has not escalated into apparent conflict.

3 = There may be some ambiguity or uncertainty between the counselor and the client regarding session goals. The current stage of communication lacks clear evidence that both parties have reached a common understanding or collaboration, but there is also no explicit conflict or disagreement. Further communication and discussion may be necessary to clarify expectations and goals to ensure the effectiveness of therapy.

4 = The counselor and the client have made some progress through discussing relevant topics, but there may still be a small amount of disagreement or areas that need further exploration. At this stage, although both parties generally agree on the current direction and topics of therapy, more communication and consensus may be needed to ensure the achievement of goals.

5 = The counselor and the client have achieved complete agreement on goals through in-depth, targeted discussions, and have had highly productive discussions on multiple related topics. At this stage, both parties almost always reach consensus on the current topic identified by the client as a goal and then smoothly transition to another relevant topic. The overall session and communication are very smooth and efficient.""",

    "Q3": """\
1 = There is evident conflict and disagreement between the counselor and the client in defining and addressing the client's issues. The client may strongly oppose the counselor's viewpoints, and the counselor may shift topics, frequently interrupt, and express disagreement with the client's perspectives. At this stage, there may be clear confrontations in the interaction between both parties, leading to a compromised effectiveness of the session.

2 = There is some disagreement between the counselor and the client regarding the client's issues. This disagreement may manifest as controversy in response to certain topics or differences in the relevance of counseling goals. At this stage, although there may be occasional confrontations in the interaction between the two, it has not escalated to strong opposition or sustained conflict.

3 = In the communication between the counselor and the client regarding the client's issues, there is no clear evidence of agreement or disagreement. In the current interaction, there may be neither a clear consensus nor explicit conflict in opinions and feelings on both sides. Further communication and discussion may be needed to clarify the positions and expectations of both parties.

4 = The counselor and the client have a certain level of consensus on the client's issues and goals. While not fully synchronized like level 5, both parties are making efforts to understand each other and demonstrate open and cooperative attitudes in discussions. This indicates that they are working towards establishing a common therapeutic direction and goals.

5 = The counselor and the client have a very clear and consistent understanding of the client's issues and goals. At this stage, there is a strong consensus on problem resolution, with both parties often identifying the same issues and considering therapy sessions highly effective. This indicates that they have formed a close collaborative relationship in the session.""",

    "Q4": """\
1 = There are clear misunderstandings and disagreements between the counselor and the client in the process of change. The client may express concerns or doubts about the direction of their change, the expected outcomes of the change, or the methods of change suggested by the counselor. At this stage, more communication and guidance may be needed to build trust and understanding.

2 = The client may have doubts or uncertainties in the process of change. Although they may be taking some actions or practices, it is not clear how to achieve the expected change or the actual effectiveness of these practices. The counselor and the client need to further explore and clarify the path and expectations of change.

3 = The counselor and the client have a neutral attitude towards the process and goals of change in the conversation. Both parties may not have explicitly expressed their understanding or misunderstanding of the change. Expectations and methods of change are neither emphasized nor overlooked in the discussion, resulting in an overall lack of clear consensus or disagreement on the goals and process of counseling.

4 = Both the counselor and the client in the conversation are aware of changes that would benefit the client. This understanding may be reflected in the client's compromise on counseling goals, expressions, or discussions about the client's current situation and future expectations. Both parties are working to clarify the path and direction of change.

5 = In the counseling process, there is strong consistency and clarity between the counselor and the client regarding the client's goals and how to achieve them. They not only discuss these goals frequently and explicitly during the session but also summarize and confirm the progress and outcomes achieved at the end. The interaction and discussion at this stage align completely with the therapeutic plan.""",

    # ===== Approach =====

    "Q5": """\
1 = The client directly expresses that the tasks and goals are inappropriate and generally disagrees with homework or tasks during the session. There is a disagreement between the client and the counselor regarding the approach to be taken. The client refuses to engage in tasks.

2 = The client hesitates to explore and does not follow the counselor's guidance in the change process. The client withdraws from the counselor, seeming to just "go through the motions," not engaging or focusing on the counselor or tasks. Even after some clarification by the counselor, the client still seems uncertain about the relevance of the tasks to their goals. The client appears conflicted or indifferent towards tasks in therapy and passively resists them (e.g., limited participation).

3 = There is no clear consensus or disagreement between the counselor and the client regarding therapy tasks. Both may have vague views on the significance and purpose of tasks, resulting in a neutral attitude towards participation and involvement in tasks during the session.

4 = The client shows a clear interest and involvement in therapy tasks. Whether occasional clarification is needed or not, the client participates and follows the exploration process. There is an unspoken understanding behind the tasks, leading the client to gradually acknowledge and engage in the tasks.

5 = The counselor and the client show strong agreement about the steps or tasks used to improve the client's situation. The counselor clearly connects the steps to the client's concerns and goals, while the client actively engages, accepts, and may help shape these steps. Both parties appear to understand why the chosen approach is useful, and the conversation shows smooth, collaborative progress toward the client's improvement.""",

    "Q6": """\
1 = The client repeatedly argues against tasks. The client refuses to participate, claiming that it is pointless for their goals. Tension exists in the relationship between the counselor and the client, and issues are not explored.

2 = The client does not actively engage in the session tasks, although he/she may not openly question the usefulness of the tasks. The client fails to openly discuss the issues. The client may hesitate to participate in tasks but eventually engages in them. The counselor accurately conveys the reasons behind the tasks, enabling the client to understand the relevance of the tasks to their current concerns.

3 = There is no clear evidence in the communication between the counselor and the client about whether they have reached an agreement or disagreement on the client's issues. In the current interaction, there is neither a clear consensus nor an explicit conflict in opinions and feelings. Further communication and discussion may be needed to clarify their positions and expectations.

4 = The client actively participates in and is committed to therapy tasks, showing no skepticism about their effectiveness. Regardless of occasional resistance, the client engages and follows the exploration process. Both parties share a common understanding of the tasks' principles, allowing the client to gradually accept and participate in the tasks.

5 = In the counseling process, the counselor and the client have a strong and clear agreement on the client's goals and how to achieve them. They not only frequently and explicitly discuss these goals during the session but also summarize and confirm the progress and achievements at the end. The interaction and discussion at this stage align completely with the therapeutic plan.""",

    "Q7": """\
1 = There is a clear disagreement and opposition between the counselor and the client regarding the current focus. This difference may manifest as the counselor not allowing the client to shift to different topics or the client showing strong opposition during the therapy process. Their views on the direction and outcomes of therapy are entirely different.

2 = The counselor and the client have some disagreement about the content and direction of therapy, differing in the themes and time allocation to focus on during therapy.

3 = There are no clear signs of agreement or disagreement in the interaction between the counselor and the client regarding the themes or issues of therapy. Although they may engage in some exploration and communication, it is challenging to determine whether they share views on therapy themes or issues. Their reactions seem neither particularly synchronized nor explicitly conflicting.

4 = The client and the counselor respond to each other's focus and needs to some extent. They explore and accept each other's views and intentions to some degree. Although there may be some differences, they both strive to seek a common understanding and progress the therapy process.

5 = The counselor and the client are highly actively engaged in the therapy process, thoroughly exploring each other's issues and responding explicitly and continuously to each other's views and intentions. They approach therapy themes and issues with an open mindset, working together, reflecting flexibility, and demonstrating a cooperative spirit.""",

    "Q8": """\
1 = The client holds evident doubts and aversions towards the counseling process, frequently engaging in arguments with the counselor. Progress between the counselor and the client is very limited, and the time spent arguing may exceed the time dedicated to therapy. This inconsistency and questioning impact the overall therapy process.

2 = The counselor and the client sometimes have conflicting opinions, but they seem to cooperate in certain parts of the therapy process. The client expresses doubts about the therapy process or occasionally expresses concerns about certain techniques, finding other things to do during most of the counseling time.

3 = The client maintains a neutral stance toward the therapy process and methods. He/she neither explicitly expresses satisfaction nor dissatisfaction with therapy, nor does he/she clearly indicate agreement or disagreement with the therapeutic methods. During the therapy process, the client may comply at certain moments and show reservations at other times, without providing a clear evaluation of the therapy's effectiveness. This neutral attitude may stem from the client's ongoing assessment of therapy effectiveness or uncertainty about how to evaluate therapy progress.

4 = The client partially agrees with certain aspects of therapy tasks, although this agreement may not always be explicitly expressed. His/her level of involvement in the therapy process falls between simple compliance and actively providing suggestions. The client shows a certain level of agreement with the collaboration with the counselor, possibly being more actively involved in certain aspects of therapy.

5 = The client is satisfied and excited about the counselor's methods and approach to problem-solving. His/her performance in therapy is highly positive, possibly suggesting suggestions to further advance therapy tasks. Overall, the client is content with therapy work, and their interaction demonstrates a high level of cooperation and enthusiasm.""",

    # ===== Affective Bond =====

    "Q9": """\
1 = There is evident animosity, hostility, or indifference between the counselor and the client. This may manifest in arguments, derogatory comments, or open hostility. The counselor fails to demonstrate concern for the client and may either forget important details of their life or completely disregard the client.

2 = Although there is no direct hostility between both parties, there is noticeable tension and distance in the relationship. The counselor appears indifferent or mechanical in response to the client, lacking enthusiasm. While there may not be explicit negative language, there is a lack of positive feedback and reinforcement in their interactions.

3 = There are no clear signs of warmth or coldness in the relationship between the counselor and the client. Communication lacks strong emotional feedback, and both parties seem to maintain a neutral stance. Despite engaging in communication, there is no clear expression or implication of liking or disliking each other. The relationship appears balanced without significant signs of warmth or indifference.

4 = In the majority of the sessions, the counselor and the client have positive interactions. The counselor shows enthusiasm and care for the client, frequently communicating with empathy and encouragement, exploring and understanding important details of the client's life.

5 = Throughout the therapy process, the counselor and the client consistently demonstrate a deep care for each other and provide positive feedback. The counselor not only encourages and reinforces the client's healthy behaviors but also deeply understands and cares about various aspects of the client's life, including their interests and hobbies. This profound care may lead to the client explicitly expressing gratitude and trust in the counselor. The client may also show appreciation for the counselor's care.""",

    "Q10": """\
1 = The client expresses minimal or no hope for the therapy outcomes. The client significantly questions the therapist's capabilities and may directly challenge the therapist's qualifications or understanding of the client's experiences. The client resists the therapist's suggestions, attempts at assistance, or expresses discouragement and pessimism.

2 = The client harbors doubts about the therapist, the therapy process, or the anticipated outcomes. The client may question whether the therapist truly understands their issues or doubt the interventions/homework provided during the problem-solving stages. These doubts do not come with strong opposition or hostility but noticeably impact the progress of the therapy process.

3 = The client holds a neutral stance regarding the therapist's capabilities. Throughout the therapy process, there is no clear evidence suggesting that the client has high confidence in the therapist, nor is there evidence indicating skepticism about the therapist's abilities. The client's responses and comments neither explicitly appreciate nor question the therapist's skills and capabilities.

4 = The client expresses a certain level of confidence in the therapist's abilities. This confidence may be reflected in the client's in-depth discussions on therapy topics, positive responses to the therapist's guidance, or an optimistic attitude towards resolving current counseling issues. Additionally, the client has substantial trust in the therapist's competency, possibly expressing appreciation for the effectiveness of the therapy or the therapist's abilities.

5 = The client consistently agrees with the therapist's reflections and interventions/guidance, expressing high satisfaction and appreciation for certain aspects of the therapy process or the therapist themselves. There may be multiple discussions during the therapy process highlighting the strengths of the therapy and/or the therapist.""",

    "Q11": """\
1 = The client feels that the therapist is indifferent, inattentive, and unconcerned about his/her issues. This is expressed through explicit accusations, disdain, or other negative reactions, indicating a sense of being disregarded or misunderstood by the therapist.

2 = The client harbors some doubts about whether the therapist genuinely cares. These doubts might be indirectly expressed, such as subtle mentions or manifestations of emotions like withdrawal, displeasure, or frustration.

3 = Throughout the therapy process, there is no clear evidence of strong positive or negative reactions from the client regarding the therapist's care and support. The client neither explicitly appreciates nor expresses dissatisfaction or disregard for the therapist's sensitivity and empathetic abilities. The emotional tone of the relationship is neutral, with no apparent strong connection or distance.

4 = The therapist demonstrates a level of acceptance, warmth, and empathy towards the client, and the client perceives and responds to this caring attitude. During the therapy process, the client acknowledges to some extent the therapist's warmth and understanding.

5 = The client strongly senses the therapist's care and support, expressing gratitude for the relationship. They may praise the therapist's sensitivity and empathetic abilities, feeling comfortable and at ease for most of the therapy process.""",

    "Q12": """\
1 = The client has significant mistrust towards the therapist, demonstrated by avoiding discussions on critical issues or directly expressing distrust. This mistrust hinders open communication, and the therapist may also show concerns and discomfort about the therapeutic process.

2 = There is a moderate level of mistrust between both parties, though not as intense as in the first category. The client may hesitate to share private content, and the therapist may feel a sense of uncertainty or slight discomfort regarding the therapeutic situation.

3 = There are no clear signs of trust between the therapist and client, but there are also no apparent behaviors indicating mistrust. There is a balance between trust and mistrust in their interactions, with no explicit demonstration of reliance on each other, nor clear signs of doubt or guardedness.

4 = The client is willing to disclose some personal concerns, and the therapist accepts the client's surface statements. The therapist does not overturn or interrupt the client's thoughts and maintains focus.

5 = The trust between both parties is deep enough that the client not only willingly shares deeper layers of privacy and issues but also accepts and responds to the therapist's feedback and suggestions. This level of trust enhances the overall smoothness and efficiency of the therapeutic process.""",
}

assert set(DETAILED_GUIDELINES) == set(QUESTIONS) == {f"Q{i}" for i in range(1, 13)}, \
    "QUESTIONS and DETAILED_GUIDELINES must cover Q1..Q12 exactly."

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# ── Per-question prompt (original Li et al. approach) ──────────────────────
PROMPT_TEMPLATE = """\
Below is a psychological counseling dialogue between a counselor and a client. \
As a third party, please read the conversation and score the following question \
from 1 to 5 based on the detailed guidelines provided.

Before assigning the final score, you must FIRST list the corresponding evidence \
found in the dialogue and then provide your analysis mapping that evidence to the \
guideline tiers. This evidence-then-analysis-then-score reasoning is required \
(Chain-of-Thought).

The 1-to-5 scale is anchored as follows:
  1 = substantial evidence against the item
  2 = some evidence against the item
  3 = absence of evidence for or against the item
  4 = some evidence for the item
  5 = substantial evidence for the item

=== Conversation ===
{conversation}

=== Question ===
{question}

=== Detailed Guideline ===
{guideline}

=== Output ===
Respond with ONLY a single valid JSON object in this exact schema, with no other text:
{{
  "evidence": "<concrete quotes or paraphrased excerpts from the dialogue that bear on this question>",
  "analysis": "<your reasoning, explicitly mapping the evidence to the guideline tiers>",
  "score": <integer 1, 2, 3, 4, or 5>
}}
"""

# ── Batch prompt (all 12 questions in one call) ────────────────────────────
PROMPT_TEMPLATE_BATCH = """\
Below is a psychological counseling dialogue between a counselor and a client. \
As a third party, please read the conversation and score ALL 12 questions below \
from 1 to 5 based on the detailed guidelines provided for each.

For EACH question, you must FIRST list the corresponding evidence found in the \
dialogue, then provide your analysis mapping that evidence to the guideline tiers. \
This evidence-then-analysis-then-score reasoning is required (Chain-of-Thought).

The 1-to-5 scale is anchored as follows:
  1 = substantial evidence against the item
  2 = some evidence against the item
  3 = absence of evidence for or against the item
  4 = some evidence for the item
  5 = substantial evidence for the item

=== Conversation ===
{conversation}

=== Questions and Guidelines ===
{questions_and_guidelines}

=== Output ===
Respond with ONLY a valid JSON array of exactly 12 objects in this exact schema, \
with no other text before or after:
[
  {{"qid": "Q1",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q2",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q3",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q4",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q5",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q6",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q7",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q8",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q9",  "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q10", "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q11", "evidence": "...", "analysis": "...", "score": <1-5>}},
  {{"qid": "Q12", "evidence": "...", "analysis": "...", "score": <1-5>}}
]
"""


def _build_questions_block() -> str:
    """Build the formatted block of all 12 questions + guidelines for the batch prompt."""
    lines: list[str] = []
    for qid, question in QUESTIONS.items():
        lines.append(f"--- {qid} ---")
        lines.append(f"Question: {question}")
        lines.append(f"Guideline:\n{DETAILED_GUIDELINES[qid].strip()}")
        lines.append("")
    return "\n".join(lines)


# Pre-build once at import time (constant across all calls).
_QUESTIONS_BLOCK = _build_questions_block()


def build_prompt(qid: str, conversation: str) -> str:
    """Construct the per-question CoT prompt."""
    return PROMPT_TEMPLATE.format(
        conversation=conversation.strip(),
        question=QUESTIONS[qid],
        guideline=DETAILED_GUIDELINES[qid].strip(),
    )


def build_prompt_batch(conversation: str) -> str:
    """Construct the batch prompt for all 12 questions in one call."""
    return PROMPT_TEMPLATE_BATCH.format(
        conversation=conversation.strip(),
        questions_and_guidelines=_QUESTIONS_BLOCK,
    )


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------
_JSON_RE = re.compile(r"\{[\s\S]*\}")
_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


def call_llm_with_engine(prompt: str,
                         inference_engine: Any,
                         max_retries: int = 3) -> dict[str, Any]:
    """Single LLM call for one question. Returns dict with evidence, analysis, score."""
    for attempt in range(max_retries):
        try:
            messages = [[{"role": "user", "content": prompt}]]
            responses = inference_engine.batch_generate(messages)
            raw = responses[0] if responses else ""

            m = _JSON_RE.search(raw)
            if m is None:
                raise ValueError(f"No JSON object found in output:\n{raw}")
            data = json.loads(m.group(0))
            score = int(data["score"])
            if score not in (1, 2, 3, 4, 5):
                raise ValueError(f"Score out of range: {score}")
            data["score"] = score
            return data

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e

    raise RuntimeError(f"Failed after {max_retries} attempts")


def parse_batch_response(raw: str) -> dict[str, dict[str, Any]] | None:
    """Parse and validate a single raw batch WAI response.

    Performs **no** LLM call. Extracts the JSON array from ``raw`` and validates
    it against the expected batch schema, returning the
    ``{qid -> {evidence, analysis, score}}`` mapping on success.

    Validation requires:
      * a JSON array is present in ``raw`` (via ``_JSON_ARRAY_RE``),
      * it parses to a ``list`` of exactly 12 items,
      * each item's ``qid`` is one of the 12 known questions, and
      * each item's ``score`` is an integer in ``1..5``.

    On any failure (no JSON array found, JSON decode error, wrong length, bad
    qid, or out-of-range score) this returns ``None`` rather than raising, so a
    failed run simply contributes no scores.
    """
    try:
        m = _JSON_ARRAY_RE.search(raw)
        if m is None:
            return None
        data = json.loads(m.group(0))

        if not isinstance(data, list):
            return None
        if len(data) != 12:
            return None

        results: dict[str, dict[str, Any]] = {}
        for item in data:
            qid = str(item.get("qid", "")).strip()
            if qid not in QUESTIONS:
                return None
            score = int(item["score"])
            if score not in (1, 2, 3, 4, 5):
                return None
            results[qid] = {
                "evidence": item.get("evidence", ""),
                "analysis": item.get("analysis", ""),
                "score": score,
            }
        return results
    except Exception:
        return None


def call_llm_batch(prompt: str,
                   inference_engine: Any,
                   max_retries: int = 3) -> dict[str, dict[str, Any]]:
    """
    Single LLM call for all 12 questions at once.

    Returns dict mapping qid → {evidence, analysis, score}.
    """
    for attempt in range(max_retries):
        try:
            messages = [[{"role": "user", "content": prompt}]]
            responses = inference_engine.batch_generate(messages)
            raw = responses[0] if responses else ""

            results = parse_batch_response(raw)
            if results is None:
                raise ValueError(f"Failed to parse batch response:\n{raw[:500]}")
            return results

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e

    raise RuntimeError(f"Batch call failed after {max_retries} attempts")


# ---------------------------------------------------------------------------
# Evaluation pipeline — per-question (original)
# ---------------------------------------------------------------------------
def evaluate_question(conversation: str,
                      qid: str,
                      inference_engine: Any,
                      n_runs: int = 3,
                      verbose: bool = True) -> dict[str, Any]:
    """Run the prompt for one question `n_runs` times and average the scores."""
    prompt = build_prompt(qid, conversation)
    runs: list[dict[str, Any]] = []
    individual_scores: list[int] = []

    for i in range(n_runs):
        try:
            result = call_llm_with_engine(prompt, inference_engine)
            runs.append(result)
            individual_scores.append(result["score"])
            if verbose:
                print(f"    [{qid}] run {i + 1}/{n_runs}: score={result['score']}")
        except Exception as e:
            if verbose:
                print(f"    [{qid}] run {i + 1}/{n_runs} FAILED: {e}")

    mean_score = statistics.mean(individual_scores) if individual_scores else None
    return {
        "qid": qid,
        "question": QUESTIONS[qid],
        "score": mean_score,
        "individual_scores": individual_scores,
        "runs": runs,
    }


# ---------------------------------------------------------------------------
# Evaluation pipeline — batch (default, token-efficient)
# ---------------------------------------------------------------------------
def evaluate_dialogue_batch(conversation: str,
                             inference_engine: Any,
                             n_runs: int = 3,
                             verbose: bool = True) -> dict[str, Any]:
    """
    Evaluate all 12 questions using n_runs batch calls (one call per run).

    Token savings vs per-question: ~70 % — the conversation is sent only
    n_runs times instead of 12 × n_runs times.
    """
    prompt = build_prompt_batch(conversation)

    # all_run_results[i] = {qid -> {evidence, analysis, score}} for run i
    all_run_results: list[dict[str, dict[str, Any]]] = []

    for i in range(n_runs):
        try:
            run_result = call_llm_batch(prompt, inference_engine)
            all_run_results.append(run_result)
            if verbose:
                scores_str = " ".join(
                    f"{q}={run_result[q]['score']}" for q in QUESTIONS if q in run_result
                )
                print(f"  run {i + 1}/{n_runs}: {scores_str}")
        except Exception as e:
            print(f"  run {i + 1}/{n_runs} FAILED: {e}")

    return _aggregate_runs(all_run_results, n_runs)


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------
def evaluate_dialogue(conversation: str,
                      inference_engine: Any,
                      n_runs: int = 3,
                      verbose: bool = True,
                      batch: bool = True) -> dict[str, Any]:
    """
    Evaluate a dialogue with WAI-O-S (12 questions, 3 dimensions).

    Args:
        conversation    : The dialogue text (counselor/client turns).
        inference_engine: InferenceEngine instance.
        n_runs          : LLM calls per run (default 3, per Li et al. 2024).
        verbose         : Print per-run progress.
        batch           : If True (default), send all 12 questions in ONE call
                          per run → n_runs total calls, ~70 % token savings.
                          If False, use original per-question mode → 12×n_runs calls.
    """
    if batch:
        return evaluate_dialogue_batch(conversation, inference_engine,
                                       n_runs=n_runs, verbose=verbose)

    # ── Per-question mode (original) ──────────────────────────────────────
    if verbose:
        print(f"Evaluating dialogue (per-question mode), n_runs={n_runs}")

    per_q: dict[str, Any] = {}
    for qid in QUESTIONS:
        if verbose:
            print(f"  {qid}: {QUESTIONS[qid][:70]}...")
        per_q[qid] = evaluate_question(conversation, qid,
                                       inference_engine=inference_engine,
                                       n_runs=n_runs,
                                       verbose=verbose)

    dim_scores: dict[str, float | None] = {}
    for dim, qids in DIMENSIONS.items():
        scs = [per_q[q]["score"] for q in qids if per_q[q]["score"] is not None]
        dim_scores[dim] = statistics.mean(scs) if scs else None

    valid_dims = [v for v in dim_scores.values() if v is not None]
    total = statistics.mean(valid_dims) if valid_dims else None

    return {
        "n_runs": n_runs,
        "questions": per_q,
        "dimensions": dim_scores,
        "total": total,
    }
