# Kế hoạch: Chuẩn hóa 6 dataset, phân tích ảnh hưởng ngôn ngữ, và Ranking thế mạnh

> Trạng thái: **Phase 8 đang chạy — Dim-C UED pilot N=20 xong cho 7 dataset; Dim-B WAI S1 đang chạy cho 11 dataset**.
> Kết quả Dim-A: `data/_analysis/mind_eval/` | Kết quả Dim-B: `data/_analysis/wai/` | Kết quả Dim-C: `data/_analysis/dim_c/`.
> Mục tiêu cuối: xếp hạng (ranking) dataset xem mỗi dataset mạnh ở tiêu chí nào, qua 3 dimension.

---

## 0. Quy ước tên (chốt để không nhầm lẫn)

**Dimension** = tiêu chí đánh giá:
- **Dim-A** = MindEval, 5 metric, thang 1–6.
- **Dim-B** = WAI-O-S, 3 metric (Goal, Approach, Affective Bond), thang 1–5.
- **Dim-C** = UED Emotional Trajectory (NRC-VAD v2.1) — **ĐÃ CÓ CODE** (xem §17 và §18). Framework Hipson & Mohammad (2021), protocol "Feel the Difference" (Wang et al., EMNLP 2025).

**Setting** = cấu hình ngôn ngữ (đổi tên từ option a/b/c để khỏi trùng Dim-A/B/C):
- **S1 = EN↔EN**: dịch hội thoại sang tiếng Anh + prompt judge tiếng Anh. *(option "a" cũ)*
- **S2 = NL↔NL**: giữ hội thoại ngôn ngữ gốc + prompt judge dịch sang ngôn ngữ gốc. *(option "b" cũ)*
- **S3 = NL→EN**: giữ hội thoại gốc + prompt judge tiếng Anh. *(option "c" cũ)*

NL = Native Language.

---

## 1. Hiện trạng (đã kiểm tra trong code)

### 1.1 Pipeline đánh giá yêu cầu MỘT format thống nhất
`mindeval/scripts/generate_judgments.py` đọc mỗi dòng và bắt buộc:
- `record["member_profile"]` — dict có các key cố định (dùng `.substitute(**profile)`); **thiếu key → crash**.
- `record["interaction"]` — list `{role, content}`; được render bởi `messages_to_convo_str`:
  - **Chỉ `role == "user"` → `<member>`; mọi role khác → `<therapist>`** → đây là **bẫy gán nhầm vai**.

### 1.2 Tình trạng từng dataset
| Dataset | Ngôn ngữ | File test hiện có | Đã ở format judge? |
|---|---|---|---|
| Psy-Insight | en | `interactions_200.jsonl` (key `dialog`, role `Supporter/Seeker`) | Chưa |
| cactus | en | `interactions_200_unique.jsonl` (role `counselor/client`, có `client_info`) | Chưa |
| simpsydial | zh | `interactions_200.jsonl` + `option_a/b/c_*.jsonl` | Một phần (xem 1.3) |
| PsyDial | zh | `interactions_200.jsonl` (role `user/assistant`) | Chưa |
| SoulChat | zh | `interactions_200.jsonl` (role `user/assistant`) | Chưa |
| KMI | ko (đã có `utterance_en`) | `interactions_200.jsonl` + `option_a/b/c_*.jsonl` | Một phần |

### 1.3 Vấn đề nhất quán cần khóa lại
- **3 quy ước role song song**: `Supporter/Seeker` (Psy-Insight), `counselor/client` (cactus, simpsydial), `Therapist/Client` (KMI), `user/assistant` (PsyDial, SoulChat). Kết hợp với `messages_to_convo_str` (chỉ nhận `"user"`) ⇒ **rủi ro vai bị gộp/đảo sai mà không báo lỗi** → mọi điểm số có thể vô nghĩa nếu không sửa.
- File `option_a` của simpsydial vẫn lưu `client/counselor` (không phải `user/assistant`) → cần thống nhất.
- **KMI raw đã có `utterance_en`** ⇒ S1 của KMI = tái dùng tiếng Anh có sẵn, KHÔNG cần dịch lại.
- Hàm dịch `translate_chinese_counseling_to_target_language` là **ZH→EN chuyên biệt** (glossary tiếng Trung) → cần khái quát hóa nếu muốn dịch ngôn ngữ khác.

### 1.4 Cấu hình model (đã có)
`config.json` có sẵn 3 mục: `translation`, `judge`, `profile_extraction` (mỗi mục: `model`, `api_key`, `api_base`, `temperature`, `timeout`, `max_retries`) + `google_translate`. `mindeval/config.py` đọc qua `get_translation_config()` / `get_judge_config()`.

---

## 2. Mục tiêu & nguyên tắc

1. Đưa cả 6 dataset về **canonical schema** đúng để judge chạy được & công bằng (BẮT BUỘC).
2. Chạy **Dim-A + Dim-B** (Dim-C gác lại) trên **6 dataset × 3 setting (S1/S2/S3)**.
3. **Phân tích ảnh hưởng ngôn ngữ**: ngôn ngữ/bản dịch có làm thay đổi điểm & ranking không? Nếu có, setting nào đáng tin nhất?
4. Dùng setting tốt nhất (về mặt phương pháp: S1 hoặc S3) làm **trục ranking chéo 6 dataset**.
5. **Thí nghiệm dịch quy mô nhỏ** (5, 10, ... record) trên `interactions_200`, thử **nhiều LLM dịch** (trước mắt GPT), có chỗ config đổi model dễ dàng.
6. Độ dài hội thoại xử lý như **covariate** (không cắt dữ liệu).

---

## 3. Phương pháp luận phân tích ảnh hưởng ngôn ngữ (Điểm 1)

### 3.1 Phân rã hiệu ứng (cốt lõi)
Với cùng một hội thoại non-EN, so sánh từng cặp setting để **tách 2 nguồn ảnh hưởng**:
- **S3 vs S2** (cùng hội thoại gốc, khác ngôn ngữ judge) ⇒ **hiệu ứng ngôn ngữ của JUDGE**.
- **S1 vs S3** (cùng judge EN, khác việc dịch hội thoại) ⇒ **hiệu ứng BẢN DỊCH**.
- **S1 vs S2** (khác cả hai) ⇒ hiệu ứng kết hợp.

Phân tích **within-dataset** (3 điều kiện trên cùng tập hội thoại), sau đó tổng hợp xu hướng across datasets. Với dataset tiếng Anh (Psy-Insight, cactus): **S1 = S3** (EN dialogue + EN judge = không có gì thay đổi), **S2 = N/A** (không có NL judge khác EN). Chỉ chạy S1, copy S1→S3; dùng làm "anchor" cho ranking chéo.

### 3.2 Tiêu chí xác định "setting tốt nhất" (không có ground truth tuyệt đối)
Báo cáo đồng thời, không dựa vào 1 chỉ số:
1. **Độ tin cậy (reliability)**: phương sai điểm giữa các lần chạy (Dim-B có `n_runs`); thấp = tốt.
2. **Sức phân biệt (discriminative power)**: độ trải điểm giữa 6 dataset; setting làm điểm "dẹt" như nhau thì kém hữu ích.
3. **Độ ổn định ranking**: Spearman/Kendall giữa thứ hạng của các setting; nếu trùng cao ⇒ ngôn ngữ ít ảnh hưởng (kết luận mạnh).
4. **Trung thực bản dịch (chỉ S1)**: back-translation + cosine similarity (embedding), tỉ lệ độ dài, mức tuân thủ thuật ngữ lâm sàng.
5. **Tham chiếu bản ngữ**: coi S2 là "fidelity reference" cho ngữ nghĩa gốc; đo S1/S3 lệch khỏi S2 bao nhiêu.
6. *(tùy chọn)* Đối chiếu human annotation nếu áp dụng được (`data/human_annotations.jsonl`).

### 3.3 Quy tắc chọn trục ranking (quan trọng về phương pháp)
- Ranking chéo 6 dataset cần **một mặt bằng judge chung**. Chỉ **S1** và **S3** dùng judge tiếng Anh cho mọi dataset ⇒ **chỉ S1 hoặc S3 hợp lệ làm trục ranking chéo**.
- **S2** dùng judge ở các ngôn ngữ khác nhau giữa dataset ⇒ điểm **không cùng thang** ⇒ **không** dùng để xếp hạng chéo; chỉ dùng phân tích trong-ngôn-ngữ & làm tham chiếu trung thực.
- Quyết định cuối:
  - Nếu **S1 ≈ S3** (Spearman cao, chênh điểm nhỏ): chọn **S3** (rẻ hơn, tránh artifact dịch) HOẶC S1 — ghi rõ lý do.
  - Nếu **S1 ≠ S3**: chọn setting **validity cao hơn** theo §3.2; nêu rõ ngôn ngữ/bản dịch có ảnh hưởng và ảnh hưởng thế nào.

---

## 4. Tầng 0 — Canonical schema (BẮT BUỘC)

### 4.0 Quyết định chốt về label & role

| Quy ước cũ (trong file gốc) | Canonical (thống nhất) |
|---|---|
| `"dialog"` (Psy-Insight, cactus, KMI raw) | `"interaction"` |
| `"dialogue"` (simpsydial, PsyDial, SoulChat) | `"interaction"` |
| `Supporter` / `Seeker` (Psy-Insight) | `"counselor"` / `"client"` |
| `counselor` / `client` (cactus, simpsydial) | `"counselor"` / `"client"` ✅ |
| `Therapist` / `Client` (KMI) | `"counselor"` / `"client"` |
| `user` / `assistant` (PsyDial, SoulChat) | `"counselor"` / `"client"` |

> **Lý do**: "interaction" là danh từ trung lập hơn "dialogue/dialog"; role "client/counselor" phù hợp với domain tâm lý học hơn "user/assistant".

---

### 4.1 Quyết định về profile — bỏ hoàn toàn khỏi judge

**Kiểm tra thực tế:** Chỉ **cactus** có profile thực (`client_info`, 12 trường). 5 dataset còn lại không có. Các script convert cũ đang dùng `DEFAULT_PROFILE` toàn `"Unknown"` → judge thực tế **không nhận được thông tin hữu ích từ profile** ở bất kỳ dataset nào.

**Vấn đề bổ sung:** `judge_prompts.py` (2880 dòng) có ~10 few-shot example, tất cả đều có `<member_details>` đầy đủ (Joseph, Amy, v.v.). Nếu chỉ bỏ profile ở instance mới nhưng giữ ở few-shot → prompt không nhất quán.

**Quyết định cuối: Bỏ `member_profile` hoàn toàn** — khỏi canonical schema VÀ khỏi judge template:
- `member_profile` không còn là field trong canonical schema
- `<member_details>` bị xóa khỏi toàn bộ judge template (cả few-shot examples lẫn instance mới)
- `generate_judgments.py` không đọc profile, `Template.substitute()` chỉ nhận `conversation_str`
- `client_info` của cactus được giữ nguyên trong `extra` (theo cấu trúc gốc của dataset, không chuẩn hóa)

**Lợi ích**: công bằng cross-dataset, pipeline đơn giản hơn, không có profile-induced bias.

---

### 4.2 Canonical schema (6 dataset)

```json
{
  "interaction_id": "cactus_42",
  "interaction": [
    {"role": "client", "content": "..."},
    {"role": "counselor", "content": "..."}
  ],
  "metadata": {
    "source": "cactus|Psy-Insight|simpsydial|PsyDial|SoulChat|KMI",
    "language": "en|zh|ko",
    "turn_count": 0,
    "origin_type": "human|simulated|single_turn",
    "original_id": "...",
    "length_bucket": "short|medium|long|very_long"
  },
  "extra": { }
}
```

**`interaction_id`**: format `<source>_<original_id>` (ví dụ: `cactus_42`, `kmi_225`, `psyinsight_000820`).

**`metadata.length_bucket`**: giữ nếu đã có (simpsydial, PsyDial); bổ sung cho các dataset còn lại dựa trên `turn_count` (ngưỡng: short ≤10, medium ≤30, long ≤70, very_long >70).

---

### 4.3 Extra fields theo từng dataset

`extra` là dict sparse — chỉ điền key nào có dữ liệu thực tế, còn lại bỏ qua (không điền `null`):

| Key trong `extra` | Dataset nguồn | Ghi chú |
|---|---|---|
| `psychotherapy_type` | Psy-Insight | VD: "Solution-Focused Brief Therapy" |
| `topic` | Psy-Insight, SoulChat | VD: "Substance Abuse", "情绪" |
| `category` | KMI | Từ `category_en` |
| `background` | Psy-Insight | Context tóm tắt case |
| `theme` | Psy-Insight | |
| `summary` | Psy-Insight | Tóm tắt session |
| `cbt_technique` | cactus | VD: "Behavior Experiment" |
| `cbt_plan` | cactus | Counseling plan text |
| `cbt_patterns` | cactus | List cognitive distortion patterns (từ `patterns`) |
| `thought` | cactus | Automatic thought của client |
| `attitude` | cactus | `"positive"` / `"neutral"` / `"negative"` |
| `client_info` | cactus | Giữ nguyên dict gốc 12 trường — không chuẩn hóa key |
| `emotional_label` | Psy-Insight (utterance-level) | List nhãn cảm xúc — dành Dim-C |
| `strategy` | Psy-Insight (utterance-level) | List chiến lược trị liệu |
| `mi_label` | KMI (utterance-level) | List MI labels (Open Question, Affirm, ...) |

> **Quy tắc**: toàn bộ `extra` **KHÔNG** đưa vào judge prompt. Mục đích: tránh rò rỉ annotation, đảm bảo judge nhìn cùng loại thông tin trên mọi dataset.

---

### 4.4 Thay đổi judge template

Xóa hoàn toàn `<member_details>...</member_details>` khỏi:
- `judge_prompts.py`: template instance + ~10 few-shot examples
- `judge_prompts_zh.py`: template instance
- `judge_prompts_ko.py`: template instance

`generate_judgments.py`: bỏ đọc `member_profile`, đơn giản hóa thành:
```python
user_prompt = judge_prompt_template.substitute(conversation_str=convo_str)
```

---

### 4.5 Tóm tắt output mỗi dataset

Đầu ra canonical cho mỗi dataset: `data/<dataset>/test/interactions_200_canonical.jsonl`
Đầu ra theo setting: `*_S1_en.jsonl`, `*_S2_nl.jsonl`, `*_S3_nl.jsonl`

Đăng ký 3 dataset thiếu (cactus, PsyDial, Psy-Insight) vào registry của `evaluate.py`.

---

## 5. Tầng 1 — Ngôn ngữ (cần gì cho từng setting)

| Setting | Hội thoại | Judge prompt | Việc cần cho non-EN |
|---|---|---|---|
| S1 (EN↔EN) | dịch sang EN | `v0_1` (EN) | Dịch ZH (simpsydial, PsyDial, SoulChat). KMI tái dùng `utterance_en`. |
| S2 (NL↔NL) | gốc | `judge_prompts_zh.py` (ZH), `judge_prompts_ko.py` (KO), `v0_1` (EN) | Không dịch hội thoại |
| S3 (NL→EN) | gốc | `v0_1` (EN) | Không dịch hội thoại |

Dim-B (WAI) truyền `wai_language` tương ứng từng setting.

---

## 6. Thí nghiệm dịch (Điểm 2) — thiết kế chi tiết

### 6.1 Mục tiêu
- Pilot dịch **N record nhỏ** (N = 5, 10, ...) lấy từ `data/<dataset>/test/interactions_200*.jsonl`.
- Thử **nhiều LLM dịch**; trước mắt **GPT**; có chỗ config để đổi model dễ dàng.
- So sánh chất lượng & chi phí giữa các translator → chọn translator cho S1 chính thức.

### 6.2 Mở rộng config: nhiều translator có tên
Thêm vào `config.json` (giữ tương thích ngược với mục `translation` cũ):

```json
{
  "translators": {
    "gpt":    { "model": "gpt-5.1",          "api_key": "...", "api_base": "https://api.openai.com/v1", "temperature": 0.3 },
    "claude": { "model": "claude-sonnet-4",  "api_key": "...", "api_base": "https://api.anthropic.com", "temperature": 0.3 },
    "qwen":   { "model": "qwen-max",          "api_key": "...", "api_base": "https://...",               "temperature": 0.3 }
  },
  "default_translator": "gpt"
}
```
- `mindeval/config.py`: thêm `get_translator_config(name)` đọc từ `translators[name]`, fallback về mục `translation` cũ nếu không có.
- Script dịch nhận cờ `--translator <name>` và `--limit <N>`.

### 6.3 Khái quát hóa hàm dịch
- Hàm hiện tại ZH→EN chuyên biệt. Cần phiên bản nhận `source_language` (zh/ko) để dùng glossary/hướng dẫn phù hợp, hoặc tách prompt theo ngôn ngữ. (Thực tế chỉ cần ZH cho pilot; KMI đã có EN.)

### 6.4 Đầu ra pilot & tổ chức file
- `data/<dataset>/test/_pilot/translate_<translator>_<N>.jsonl` (kèm cột `source`, `translation`, `back_translation`).
- Một bảng tổng hợp `data/_translation_pilot/summary.csv`.

### 6.5 Tiêu chí so sánh translator (QA)
1. **Back-translation similarity**: dịch ngược EN→NL rồi cosine similarity với gốc (embedding) — cao = giữ nghĩa.
2. **Tỉ lệ độ dài** (token EN / token gốc) — phát hiện cắt xén / phình.
3. **Tuân thủ thuật ngữ lâm sàng**: checklist thuật ngữ (vd các mục trong glossary ZH→EN sẵn có).
4. **Chấm tay nhanh** vài mẫu (1–5) theo rubric: trung thực / tự nhiên / giữ sắc thái cảm xúc / không thêm-bớt.
5. **Tác động hạ nguồn** *(tùy chọn, mạnh nhất)*: dịch cùng N record bằng 2 translator → chạy Dim-A → xem điểm có lệch theo translator không (nếu lệch lớn ⇒ chọn translator cẩn thận).
6. **Chi phí/tốc độ** (token, thời gian).

---

### 6.6 Thí nghiệm dịch riêng cho KMI — KO→EN so sánh với `utterance_en`

#### Động lực

Phân tích pilot (§13.3) cho thấy **KMI là dataset duy nhất** có sự khác biệt có ý nghĩa thống kê (p<0.05) giữa S1 và S2/S3 (Δ ≈ −0.27). S1 của KMI đang dùng `utterance_en` — bản EN có sẵn trong dataset gốc, được cung cấp bởi tác giả dataset. Giả thuyết: bản EN gốc này "phẳng" về mặt cảm xúc và ngôn ngữ hơn bản KO, khiến judge (EN) chấm thấp hơn so với khi judge đọc trực tiếp bản KO (S2/S3). Đây là **artifact bản dịch của dataset**, không phải artifact của pipeline đánh giá.

Để kiểm chứng: **dịch bản KO gốc** bằng GPT-5.1 rồi chạy judge trên bản dịch mới, so sánh với `utterance_en`.

#### Thiết kế

| Điều kiện | Nguồn văn bản | Bản EN dùng để judge | Ký hiệu |
|---|---|---|---|
| S1 hiện tại | `interactions_200_S1_en.jsonl` | `utterance_en` (có sẵn trong dataset) | **S1-utt** |
| S1 mới (thí nghiệm) | `interactions_200_S1_ko_translated_en.jsonl` | GPT-5.1 dịch từ `canonical_ko.jsonl` | **S1-llm** |

So sánh **S1-utt vs S1-llm** (cùng judge EN, khác nguồn EN) → tách biệt **artifact của `utterance_en`** khỏi artifact của pipeline.

#### Implementation (đã code)

- `translate_to_en.py` — thêm entry `"kmi_ko"` vào `DATASET_CONFIGS`:
  - `src`: `data/KMI/test/interactions_200_canonical_ko.jsonl` (text KO gốc)
  - `dst`: `data/KMI/test/interactions_200_S1_ko_translated_en.jsonl` (bản GPT-5.1 dịch)
  - `source_lang: "ko"` → dùng `_SYSTEM_KO_EN` prompt (đã có sẵn)
- Metadata `translation_variant` được ghi vào mỗi record để phân biệt:
  - `"utterance_en"` — bản EN gốc của dataset (file `S1_en.jsonl`)
  - `"llm_translated"` — bản GPT-5.1 dịch từ KO (file `S1_ko_translated_en.jsonl`)
- Flag `--translator <name>` thêm vào script để đổi model dịch dễ dàng (theo §6.2).

#### Lệnh chạy

```powershell
# Pilot N=5
python -m mindeval.scripts.translate_to_en --datasets kmi_ko --limit 5

# Pilot N=20 (đủ để chạy judge + so sánh thống kê)
python -m mindeval.scripts.translate_to_en --datasets kmi_ko --limit 20

# Full 200 (sau khi pilot xác nhận)
python -m mindeval.scripts.translate_to_en --datasets kmi_ko
```

#### Phân tích so sánh (sau khi dịch + judge xong)

1. **Δ điểm judge**: `mean(S1-llm) − mean(S1-utt)` theo từng metric (Clinical, Ethics, Assessment, Alliance, AI-Comm). Nếu S1-llm gần S2 hơn → xác nhận `utterance_en` là nguồn bias.
2. **Spearman(S1-llm, S2)** và **Spearman(S1-utt, S2)**: setting nào ranking sát với bản ngữ (S2) hơn?
3. **Chất lượng bản dịch** (§6.5): back-translation similarity, tỉ lệ độ dài, chấm tay nhanh.
4. **Kết luận phương pháp**: nếu `utterance_en` bị bias → trong paper cần ghi rõ KMI S1 dùng bản EN nào và tác động của nó; nếu không bias → giữ nguyên `utterance_en` cho S1 (rẻ hơn, không cần gọi thêm API).

#### Output files

```
data/KMI/test/
  interactions_200_S1_en.jsonl                ← S1-utt: utterance_en có sẵn (đã có)
  interactions_200_S1_ko_translated_en.jsonl  ← S1-llm: GPT-5.1 dịch từ KO (thí nghiệm)

data/KMI/results/mind_eval/
  S1_judgments.jsonl                          ← kết quả judge S1-utt (đã có, N=20)
  S1_ko_translated_judgments.jsonl            ← kết quả judge S1-llm (đã chạy, N=20)
```

#### Kết quả pilot N=20 (đã chạy)

| Metric | S1-utt | S1-llm | S2-ko | Δ(llm−utt) | Δ(llm−S2) |
|---|---|---|---|---|---|
| Clinical | 2.700 | 2.962 | 2.625 | **+0.262** | +0.337 |
| Ethics | 3.625 | 3.987 | 3.950 | **+0.362** | +0.037 |
| Assess | 2.400 | 2.812 | 2.837 | **+0.413** | −0.025 |
| Alliance | 2.513 | 2.925 | 2.913 | **+0.412** | +0.012 |
| AI-Comm | 2.125 | 2.500 | 2.413 | **+0.375** | +0.087 |
| **Overall** | **2.672** | **3.038** | **2.948** | **+0.365** | **+0.090** |

**Kết luận sơ bộ (N=20):**
- **S1-llm > S1-utt** trên tất cả 5 metric (Δ Overall = +0.365) → **xác nhận giả thuyết**: `utterance_en` của KMI có sẵn "phẳng" về mặt ngôn ngữ/cảm xúc, khiến judge chấm thấp hơn đáng kể so với GPT-5.1 translation.
- **S1-llm ≈ S2-ko** (Δ Overall = +0.090, rất nhỏ, đặc biệt Ethics +0.037, Assess −0.025, Alliance +0.012) → bản GPT-5.1 giữ được sắc thái gần với bản gốc Hàn, trong khi `utterance_en` bị mất đi đáng kể.
- **Hệ quả với ranking S1**: KMI từ vị trí cuối (mean-rank 5.6 với S1-utt) sẽ cải thiện đáng kể nếu dùng S1-llm → cần báo cáo rõ trong paper rằng KMI S1 cũ dùng `utterance_en` và đây là nguồn bias định lượng được.
- **Khuyến nghị**: dùng **S1-llm** (`interactions_200_S1_ko_translated_en.jsonl`) làm S1 chính thức của KMI; cập nhật lại `evaluate.py` và `run_eval_matrix.py` tương ứng.

---

## 7. Tầng 2 — Khử confound

- **Profile**: **Bỏ hoàn toàn** khỏi judge prompt trên cả 6 dataset. Judge chỉ nhìn vào nội dung hội thoại — công bằng tuyệt đối. `client_info` cactus được bảo toàn trong `extra` cho mục đích phân tích khác.
- **Độ dài = covariate** (không cắt):
  - Báo cáo phân bố `turn_count` mỗi dataset.
  - Chia **length-bucket** (short/medium/long/very_long; KMI/PsyDial đã có nhãn).
  - Khi ranking: báo cáo tương quan điểm↔độ dài + so trong cùng bucket / partial correlation, để tránh kết luận "mạnh" do hội thoại dài hơn.

---

## 8. Tầng 3 — Chuẩn hóa điểm & Ranking

Chạy riêng cho từng setting; với mỗi metric/dataset xuất 3 lớp:
1. **Raw mean** — chất lượng tuyệt đối (trong cùng setting).
2. **Z-score theo từng metric across 6 dataset** — "**hồ sơ thế mạnh**" (dataset nào nổi trội ở metric/dimension nào). *Đây là output chính cho mục tiêu ranking.*
3. **Mean-rank** (hạng trung bình) — robust, dùng gộp chéo Dim-A↔Dim-B dù khác thang.

Quy tắc: **so chéo dimension chỉ trên điểm đã normalize** (vì Dim-A 1–6, Dim-B 1–5 khác thang). Sản phẩm: bảng ranking theo từng dimension + tổng hợp normalize, kèm strength-profile mỗi dataset; lặp cho trục ranking đã chọn (S1 hoặc S3), đối chiếu với S3/S1 và S2.

---

## 9. Ma trận chạy & ghi chú chi phí

- **EN datasets (Psy-Insight, cactus)**: chỉ chạy **S1** (1 lần). Sau đó `copy_en_results()` copy S1→S3 (vì S3=S1 với EN datasets). **S2 không tồn tại** — không có "NL judge" khác EN.
  - ⚠️ **Bug đã fix**: phiên bản cũ chạy S1 và S3 riêng biệt → LLM sampling noise (temperature>0) gây S1≠S3 trên 18/20 records (lệch 0.1–0.5) dù cùng input. Đây là noise, không phải tín hiệu. Fix: chỉ chạy S1, copy S1→S3.
  - ⚠️ **Bug đã fix**: phiên bản cũ còn copy S1→S2 nhầm. Fix: S2 không được tạo cho EN datasets.
- **ZH datasets (simpsydial, PsyDial, SoulChat)**: 3 setting khác nhau → 3 lần.
- **KMI (ko)**: S1 dùng `utterance_en`; S2 judge KO; S3 judge EN trên text KO.
- Tái dùng kết quả đã có (simpsydial/KMI option_* nếu hợp lệ sau khi khóa role) để tiết kiệm token.
- Dim-B (WAI) tốn token gấp nhiều lần Dim-A (36 call/dialogue) → cân nhắc `--max_dialogues` khi thử.

---

## 10. Caveat bắt buộc trong báo cáo

Chuẩn hóa format/ngôn ngữ/profile/độ dài **không khử được confound nguồn gốc** (human transcript vs LLM-simulated vs single-turn empathy). Ranking phải diễn giải là **"hồ sơ thế mạnh tương đối"**, không phải "chất lượng tuyệt đối hơn/kém".

---

## 11. CHECKLIST CÁC VIỆC CẦN LÀM (theo thứ tự)

### Phase 0 — Chuẩn bị
- [ ] Xác nhận `origin_type` cho từng dataset (human/simulated/single_turn).
- [ ] Chốt trục ranking dự kiến (S1 hay S3) — sẽ finalize sau phân tích §3.

### Phase 1 — Canonical schema (Tầng 0)
- [x] **Chốt**: Bỏ `member_profile` hoàn toàn — khỏi schema VÀ khỏi judge (§4.1).
- [x] **Chốt**: label `"interaction"` thay `"dialog"/"dialogue"` trên toàn bộ 6 dataset (§4.0).
- [x] **Chốt**: role `"client"/"counselor"` thống nhất, map từ mọi convention gốc (§4.0).
- [x] **Chốt**: `client_info` cactus giữ nguyên trong `extra` (không chuẩn hóa key).
- [x] **Chốt**: `extra` sparse — 15 key cụ thể theo dataset, không đưa vào judge prompt (§4.3).
- [x] **Chốt**: Xóa `<member_details>` khỏi toàn bộ judge templates (§4.4).
- [x] **Code**: Xóa `<member_details>` khỏi `judge_prompts.py` (template + 10 few-shot examples).
- [x] **Code**: Xóa `<member_details>` khỏi `judge_prompts_zh.py` và `judge_prompts_ko.py`.
- [x] **Code**: Cập nhật `generate_judgments.py` — bỏ `all_profiles`, đơn giản hóa `substitute()`.
- [x] **Code**: Viết `convert_to_canonical.py` — converter chung 6 dataset → `interactions_200_canonical.jsonl`.
- [x] **Code**: Sửa bẫy role trong `utils.py` (`messages_to_convo_str` nhận cả `client/user` → `<member>`).
- [x] **Code**: Tách annotation sang `extra` (strategy, emotional_label, mi_label, client_info, …).
- [x] **Code**: Đăng ký cactus, PsyDial, Psy-Insight vào registry `evaluate.py`; đổi tên option a/b/c → S1/S2/S3.
- [x] **Bỏ qua**: File `option_*` cũ (simpsydial/KMI) đã xóa — không cần điều chỉnh.

### Phase 2 — Thí nghiệm dịch (Điểm 2)
- [x] **Code**: Viết `translate_to_en.py` — batch translate (1 LLM call/record thay vì N calls/turns).
  - Prompt tối ưu: system message cố định (terminology ZH→EN) + user message chứa toàn bộ dialogue dưới dạng JSON.
  - Tiết kiệm ~17× token so với turn-by-turn (simpsydial 30 turns: 4.2K vs 75K tokens/dialogue).
  - Hỗ trợ `--limit N`, `--max_workers`, `skip_existing` (resumable).
- [x] **Chạy pilot N=5**: simpsydial (30–54 turns), PsyDial (68–142 turns), SoulChat (10–14 turns) — 0 lỗi.
- [x] **KMI S1-utt**: đã có EN sẵn (`utterance_en`) — fix `language: "ko"` → `"en"` trong canonical; copy sang `S1_en.jsonl`.
- [x] **Code**: Thêm `"kmi_ko"` vào `DATASET_CONFIGS` — dịch KO→EN bằng GPT-5.1, output `S1_ko_translated_en.jsonl`; thêm `--translator` flag; ghi `translation_variant` vào metadata (xem §6.6).
- [x] **Chạy pilot N=20 KMI KO→EN**: `python -m mindeval.scripts.translate_to_en --datasets kmi_ko --limit 20`
- [x] **Judge S1-llm**: chạy Dim-A trên `S1_ko_translated_en.jsonl` → `S1_ko_translated_judgments.jsonl` (N=20, ~30s).
- [x] **So sánh S1-utt vs S1-llm**: Δ Overall = +0.365; S1-llm ≈ S2-ko (Δ=+0.090) — xác nhận artifact `utterance_en` (xem §6.6 kết quả pilot).
- [ ] **Cập nhật `evaluate.py`**: đổi KMI S1 trỏ sang `interactions_200_S1_ko_translated_en.jsonl` thay `utterance_en`.
- [ ] QA bản dịch ZH: back-translation similarity, tỉ lệ độ dài, chấm tay (sau khi chạy đánh giá xong).
- [ ] Chọn translator chính thức (hiện tại: GPT-5.1 — chờ kết quả hạ nguồn).

### Phase 3 — Sinh dữ liệu 3 setting (Tầng 1)
- [x] **S1 (pilot 5 records)**: `*_S1_en.jsonl` — simpsydial, PsyDial, SoulChat đã dịch.
- [x] **S1 (full 200)**: KMI, cactus, Psy-Insight — copy từ canonical / `utterance_en`.
- [x] **S2/S3 ZH**: dùng `interactions_200_canonical.jsonl` + judge ZH (`judge_prompts_zh.py`).
- [x] **S2/S3 KMI**: dùng `interactions_200_canonical_ko.jsonl` (KO text) — cùng 200 `interaction_id` với EN.
- [x] **Judge ZH/KO**: rubric + 5 few-shot dịch từ EN `v0_1`; output format có tên tiêu chí EN (parser OK).
- [x] **Code**: `--max_dialogues` trong `generate_judgments.py` + `evaluate.py`.
- [x] **Code**: `run_eval_matrix.py` — chạy ma trận S1/S2/S3 (pilot hoặc full).
- [ ] S1 full 200 records cho 3 dataset ZH (chờ sau khi phân tích pilot).

### Phase 4 — Chạy đánh giá

#### 4.0 Chuẩn bị (chạy 1 lần)

```powershell
cd H:\Vy\Paper\Empathy\Code\mind-eval\mind-eval

# Kiểm tra file input + registry
python evaluate.py --list

# Xem trước lệnh sẽ chạy (không gọi API)
python -m mindeval.scripts.run_eval_matrix --dry_run --eval mind-eval
```

Yêu cầu: `config.json` có section `judge` (Dim-A) và cùng API key cho WAI nếu chạy Dim-B.

#### 4.1 Ma trận chạy (pilot N=20 — khuyến nghị hiện tại)

| Dataset | S1 | S2 | S3 | Ghi chú |
|---|---|---|---|---|
| simpsydial | EN dialogue + EN judge | ZH + ZH judge | ZH + EN judge | S1: dịch ZH→EN |
| psydial | EN + EN | ZH + ZH | ZH + EN | S1: dịch ZH→EN |
| soulchat | EN + EN | ZH + ZH | ZH + EN | S1: dịch ZH→EN |
| kmi | EN + EN | **KO + KO judge** | **KO + EN judge** | S2/S3 dùng `canonical_ko` |
| cactus | EN + EN | `-` (N/A) | =S1 (copy) | EN dataset: chỉ chạy S1, `copy_en_results()` tạo S3 |
| psy_insight | EN + EN | `-` (N/A) | =S1 (copy) | EN dataset: chỉ chạy S1, `copy_en_results()` tạo S3 |

> **Lưu ý**: EN datasets không có S2 — chạy judge thêm lần với cùng input chỉ thêm LLM sampling noise, không phải tín hiệu thực. `run_eval_matrix` chỉ submit 14 jobs (không phải 16).

**Bước 0 — Dịch S1 (chỉ 3 dataset ZH; resumable — bỏ qua 5 record đã dịch):**

```powershell
# Dịch thêm record 6–20 (skip_existing theo interaction_id)
python -m mindeval.scripts.translate_to_en --datasets simpsydial psydial soulchat --limit 20
```

**Dim-A (MindEval — 5 metric, 1 call/dialogue):**

```powershell
# Chạy toàn bộ ma trận pilot N=20 (14 jobs; EN datasets chỉ chạy S1 rồi copy → S3)
# skip_existing → chỉ judge các record chưa có
python -m mindeval.scripts.run_eval_matrix --pilot --pilot_n 20 --eval mind-eval --max_workers 3
```

**Dim-B (WAI — S3 only, batch mode, pilot N=20):**

```powershell
# Chạy S3 cho tất cả 6 dataset, n_runs=1 (batch: 1 call/record thay vì 36)
python -m mindeval.scripts.run_eval_matrix --pilot --pilot_n 20 --eval wai --settings S3 --judge_name gpt --wai_n_runs 1

# Hoặc từng dataset (có thể resume nếu bị gián đoạn)
python evaluate.py --dataset simpsydial --option S3 --eval wai --max_dialogues 20 --judge_name gpt --wai_n_runs 1
```

> **Lưu ý WAI**: WAI dùng **batch mode** (mặc định) — 12 câu hỏi gộp vào 1 LLM call/run → tiết kiệm ~70% token. Với `n_runs=1`: 1 call/record thay vì 36. Dùng `--wai_n_runs 3` cho kết quả chính thức.

**Dim-A + Dim-B cùng lúc:**

```powershell
python -m mindeval.scripts.run_eval_matrix --pilot --pilot_n 20 --eval both --settings S3 --judge_name gpt --wai_n_runs 1
```

#### 4.2 Chạy từng dataset / setting (lệnh đơn)

```powershell
# Ví dụ: KMI S2 (KO dialogue + KO judge), 20 dialogue đầu
python evaluate.py --dataset kmi --option S2 --eval mind-eval --max_dialogues 20

# Ví dụ: simpsydial S3 (ZH + EN judge)
python evaluate.py --dataset simpsydial --option S3 --eval mind-eval --max_dialogues 20

# Ví dụ: cactus S1 (EN)
python evaluate.py --dataset cactus --option S1 --eval mind-eval --max_dialogues 20
```

#### 4.3 Output (cấu trúc chuẩn)

```
data/<dataset>/results/
  mind_eval/
    S1_gpt_judgments.jsonl      # tất cả 6 dataset — judge GPT
    S2_gpt_judgments.jsonl      # chỉ non-EN: simpsydial, PsyDial, SoulChat, KMI
    S3_gpt_judgments.jsonl      # tất cả 6 dataset (EN: copy từ S1)
    S1_claude_judgments.jsonl   # tất cả 6 dataset — judge Claude
    S2_claude_judgments.jsonl   # chỉ non-EN
    S3_claude_judgments.jsonl   # tất cả 6 dataset (EN: copy từ S1)
  wai/
    S3_gpt_wai_judgments.jsonl  # tất cả 6 dataset, setting S3 (NL→EN, EN prompt)
```

Mỗi dòng Dim-A: **`interaction_id`**, `parsed_judgment`, `unparsed_judgment`, `thinking_trace`, `judge_name`, `judge_model`.
Script mặc định **skip existing** (ID-based) — chạy lại từ đầu thêm `--no_skip`.

> ⚠️ **Bug đã fix (generate_judgments.py)**:
> - **Trước fix**: output không chứa `interaction_id`; `skip_existing` dùng đếm vị trí (`n_existing`) thay vì ID → nếu có record lỗi/retry giữa chừng, các judgment sau đó bị gán nhầm sang record khác một cách **im lặng** (không crash, không cảnh báo).
> - **Sau fix**: mỗi dòng kết quả ghi thêm `interaction_id`; `skip_existing` đọc tập ID đã có và skip theo ID — an toàn với retry/gap. File cũ (trước fix, không có `interaction_id`) fallback về positional skip kèm cảnh báo rõ ràng.
> - **analyze_results.py**: `build_long_df()` nay dùng `interaction_id` làm key chính; fallback về `record_idx` cho file cũ.
> - **Hệ quả với pilot N=20 đã chạy**: 20 record đã chạy theo thứ tự đúng từ đầu (không có retry), nên kết quả pilot vẫn hợp lệ. Tuy nhiên cần chạy lại nếu muốn có `interaction_id` trong file để join chính xác.

#### 4.4 Full run (200 records — sau khi phân tích pilot)

```powershell
# Bước 1: dịch full S1 cho 3 dataset ZH + KMI KO→EN
python -m mindeval.scripts.translate_to_en --datasets simpsydial psydial soulchat
python -m mindeval.scripts.translate_to_en --datasets kmi_ko

# Bước 2: chạy full ma trận — judge GPT
python -m mindeval.scripts.run_eval_matrix --full --judge_name gpt --eval mind-eval --max_workers 5

# Bước 3: chạy full ma trận — judge Claude (rate limit → max_workers=1, batch_delay=5)
python -m mindeval.scripts.run_eval_matrix --full --judge_name claude --eval mind-eval --max_workers 1 --batch_delay 5
```

#### 4.5 Checklist Phase 4 — GPT judge
- [x] Chạy Dim-A pilot (14 jobs, N=20) — `run_eval_matrix --pilot --pilot_n 20 --eval mind-eval`
  - 16/16 jobs OK (4 ZH×3 setting + KMI×3 + cactus S1 + psy_insight S1 → copy S3)
  - `copy_en_results()` đã tạo S3 từ S1 cho cactus, Psy-Insight
- [x] **Bug fix**: `generate_judgments.py` — thêm `interaction_id` + `judge_name` + `judge_model` vào output; đổi `skip_existing` sang ID-based.
- [x] **Bug fix**: rename output files → `S{1,2,3}_gpt_judgments.jsonl` (convention `{setting}_{judge}_judgments.jsonl`).
- [x] **Bug fix**: `analyze_results.py` — `build_long_df()` dùng `interaction_id` làm key; fallback `record_idx` cho file cũ.
- [x] Kiểm tra output: mỗi file có đủ 20 dòng, `parsed_judgment` hợp lệ ✓
- [x] **Chạy Dim-B pilot** — xem §11 Phase 7 + §16 WAI
- [ ] (Sau) Dim-A full 200 — sau khi dịch S1 full + phân tích pilot
- [x] **Dim-C pilot N=20** — xem §17 và §18 (7 dataset, EN lexicon)

#### 4.6 Checklist Phase 4 — Claude judge (so sánh với GPT)

Model: `anthropic/claude-sonnet-4-6` | max_workers=1 | batch_delay=5 (rate limit Anthropic)

```powershell
python -m mindeval.scripts.run_eval_matrix --pilot --pilot_n 20 --judge_name claude --eval mind-eval --max_workers 1 --batch_delay 5
```

| Dataset | S1 | S2 | S3 | Ghi chú |
|---|---|---|---|---|
| simpsydial | [x] DONE | [x] DONE | [x] DONE | — |
| PsyDial | [x] DONE | [x] DONE | [x] DONE | — |
| SoulChat | [x] DONE | [ ] PARTIAL 5/20 | [ ] TODO | hết credit → resume sau khi nạp |
| KMI | [ ] TODO | [ ] TODO | [ ] TODO | — |
| cactus | [ ] TODO | N/A | =S1 (copy) | — |
| Psy-Insight | [ ] TODO | N/A | =S1 (copy) | — |

> **Resume SoulChat S2**: `skip_existing` tự skip 5 ID đã có khi chạy lại lệnh trên.

### Phase 5 — Phân tích ngôn ngữ (§3) & chọn trục ranking
- [x] **Code**: `analyze_results.py` — phân tích toàn diện Phase 5+6 (xem §13).
  - Fix: EN datasets (cactus, Psy-Insight) bị loại khỏi language_effect analysis (S1=S3, không có hiệu ứng ngôn ngữ thực).
  - Fix: `build_long_df()` dùng S1 cho cả S1 và S3 với EN datasets; S2 = không tồn tại.
  - Fix: report dùng `-` cho S2 của EN datasets; heatmap hiển thị `-` trên ô N/A.
- [x] Phân rã S3 vs S2 (judge-language), S1 vs S3 (translation), S1 vs S2 (kết hợp) — **12 cặp**, chỉ non-EN.
- [x] Tính discriminative power (std of dataset means) per metric per setting.
- [x] Tính Spearman/Kendall/Pearson correlation + MAD + paired t-test giữa các cặp setting.
- [x] **Kết luận**: S1 có discriminative power cao nhất (std Overall = 0.311 vs S3=0.254, S2=0.159 trên 4ds).
  Spearman S1↔S3 = 0.503 (thấp → bản dịch ảnh hưởng đến ranking cá thể).
  KMI là dataset duy nhất có **sự khác biệt có ý nghĩa thống kê** (p<0.05) giữa S1 và S2/S3.
- [x] **Chọn trục ranking**: **S1** (sức phân biệt tốt nhất, judge EN đồng nhất). Đối chiếu với S3.

**Lệnh phân tích:**
```powershell
# Phân tích GPT judge (mặc định) — Chart 1–12 + report.md
python -m mindeval.scripts.analyze_results

# Phân tích kèm so sánh Claude vs GPT — thêm Chart 13 + Section 9 vào report.md
python -m mindeval.scripts.analyze_results --judge_name claude

# Lưu kết quả vào thư mục khác (tùy chọn)
python -m mindeval.scripts.analyze_results --judge_name claude --output_dir data/_analysis/mind_eval_claude
```

### Phase 6 — Ranking & báo cáo Dim-A (Tầng 2+3)
- [x] Script chuẩn hóa: raw mean + z-score per-metric + mean-rank → `ranking_S1.csv`, `ranking_S3.csv`.
- [x] Bảng ranking theo từng metric + tổng hợp normalize + strength-profile mỗi dataset.
- [x] 11 biểu đồ (heatmap×3 settings, scatter, boxplot, radar, bar, Spearman, triple comparison) → `data/_analysis/mind_eval/charts/`.
- [x] Báo cáo tổng hợp markdown → `data/_analysis/mind_eval/report.md`.
- [ ] Length-bucket + partial correlation (covariate) — chờ full 200 records.
- [ ] Viết caveat provenance vào paper.

### Phase 7 — Dim-B WAI-O-S (S3, N=20 pilot)

#### 7.1 Thiết kế & code
- [x] **Code**: `mindeval/wai/wai_evaluator.py` — EN prompt template, 12 Q + detailed guidelines (Li et al. 2024).
- [x] **Code**: **Batch mode** (`PROMPT_TEMPLATE_BATCH`) — gộp 12 câu hỏi vào 1 LLM call/run → giảm từ 36 xuống còn `n_runs` calls/dialogue (~70% token savings). Mặc định `batch=True`.
- [x] **Code**: `generate_wai_judgments.py` — ID-based `skip_existing`, ghi `interaction_id` + `judge_name` + `judge_model` vào output.
- [x] **Code**: `analyze_wai_results.py` — 6 charts + 3 tables + report.md.
- [x] **Chốt setting**: WAI chỉ chạy **S3** (dataset gốc + EN prompt) — không cần S1/S2. Lý do: WAI đánh giá liên minh trị liệu từ nội dung hội thoại, không phụ thuộc ngôn ngữ judge như Dim-A.
- [x] **Chốt**: Xóa `wai_prompts_zh.py` (không cần), bỏ `language` parameter khỏi toàn bộ WAI pipeline.
- [x] **MATRIX update**: Thêm S3 vào EN datasets (cactus, psy_insight) trong `run_eval_matrix.py` → `--settings S3` cover đủ 6 dataset.

#### 7.2 Rubric fix — Q1 & Q3
- [x] **Phát hiện**: Q1 và Q3 có level 2 ↔ 4 đảo ngữ nghĩa trong rubric gốc Li et al. (2024) Appendix A.3. Level 2 mô tả hành vi liên minh TỐT ("không nói rõ mục tiêu nhưng cùng nỗ lực, client hài lòng") nhưng được chấm điểm thấp; level 4 mô tả liên minh XẤU nhưng được chấm điểm cao. → Gây artifact: hội thoại tốt bị phạt về 2 điểm.
- [x] **Fix**: Hoán đổi nội dung level 2 ↔ 4 trong Q1 và Q3 (`wai_evaluator.py`). Thang điểm trở về monotonic (1=xấu → 5=tốt).
- [x] **Kiểm chứng**: Sau fix, Q1 mean tăng từ **2.87 → 4.20** (simpsydial pilot), Goal dimension nhất quán với Approach và Affective Bond.

#### 7.3 Chạy pilot N=20
- [x] **simpsydial** S3: 20 records, n_runs=1 ✓ → `data/simpsydial/results/wai/S3_gpt_wai_judgments.jsonl`
- [x] **PsyDial** S3: 20 records, n_runs=1 ✓ → `data/PsyDial/results/wai/S3_gpt_wai_judgments.jsonl`
- [x] **SoulChat** S3: 20 records, n_runs=1 ✓ → `data/SoulChat/results/wai/S3_gpt_wai_judgments.jsonl`
- [x] **KMI** S3: 20 records, n_runs=1 ✓ → `data/KMI/results/wai/S3_gpt_wai_judgments.jsonl`
- [x] **cactus** S3: 20 records, n_runs=1 ✓ → `data/cactus/results/wai/S3_gpt_wai_judgments.jsonl`
- [x] **Psy-Insight** S3: 20 records, n_runs=1 ✓ → `data/Psy-Insight/results/wai/S3_gpt_wai_judgments.jsonl`

#### 7.4 Phân tích kết quả
- [x] **Code + chạy**: `analyze_wai_results.py` → `data/_analysis/wai/` (6 charts + 3 tables + report.md).
- [ ] So sánh ranking Dim-A vs Dim-B — xem §16.3.
- [ ] Full 200 records với n_runs=3 (kết quả chính thức).

**Lệnh chạy:**
```powershell
# Pilot (resume-able — skip theo interaction_id)
python evaluate.py --dataset <ds> --option S3 --eval wai --max_dialogues 20 --judge_name gpt --wai_n_runs 1

# Phân tích
python -m mindeval.scripts.analyze_wai_results
```

---

## 13. Kết quả phân tích pilot (N=20) — Dim-A MindEval

> Script: `python -m mindeval.scripts.analyze_results`
> Output: `data/_analysis/mind_eval/` | Thang điểm 1–6

### 13.1 Ranking tổng hợp theo S1 (EN↔EN) — trục chính

| Dataset | Clinical | Ethics | Assessment | Alliance | AI-Comm | **Mean-Rank** |
|---|---|---|---|---|---|---|
| cactus | +1.68 | +1.44 | +1.34 | +1.31 | +1.14 | **1.0** 🥇 |
| simpsydial | +0.36 | +0.60 | +0.71 | +0.53 | +0.78 | **2.5** |
| Psy-Insight | +0.52 | +0.60 | +0.32 | −0.10 | +0.37 | **2.9** |
| PsyDial | −0.22 | −0.96 | +0.28 | +0.58 | −0.24 | **4.0** |
| SoulChat | −1.13 | −1.51 | −1.14 | −0.49 | −0.07 | **5.0** |
| KMI | −1.21 | −0.18 | −1.50 | −1.85 | −1.98 | **5.6** |

*Z-score: (+) = trên trung bình. Mean-rank: thấp = tốt hơn (1 = tốt nhất).*

### 13.2 Điểm raw Overall score trung bình

| Dataset | Lang | Origin | S1 (EN↔EN) | S2 (NL↔NL) | S3 (NL→EN) |
|---|---|---|---|---|---|
| cactus | en | simulated | **3.51** | `-` | =S1 (3.51) |
| Psy-Insight | en | human | 3.19 | `-` | =S1 (3.19) |
| simpsydial | zh | simulated | 3.26 | 3.22 | 3.29 |
| PsyDial | zh | human | 3.02 | 2.94 | 3.01 |
| SoulChat | zh | simulated | 2.79 | 2.85 | 2.82 |
| KMI | ko | human | 2.67 | **2.95** | 2.93 |

*(Dải điểm thực tế: 2.67–3.51 trên thang 1–6 → toàn bộ dataset nằm quanh mức "cơ bản đến vừa")*

### 13.3 Phân tích ảnh hưởng ngôn ngữ

**Discriminative Power (std of dataset-means — cao = phân biệt tốt hơn):**

| Setting | Clinical | Ethics | Assessment | Alliance | AI-Comm | **Overall** | n datasets |
|---|---|---|---|---|---|---|---|
| S1 (EN↔EN) | 0.332 | 0.423 | 0.348 | 0.282 | 0.339 | **0.311** ← tốt nhất | 6 |
| S3 (NL→EN) | 0.292 | 0.389 | 0.269 | 0.185 | 0.296 | 0.254 | 6 |
| S2 (NL↔NL) | 0.232 | 0.350 | 0.136 | 0.087 | 0.184 | 0.159 | 4 (non-EN only) |

> S2 chỉ có 4 dataset (simpsydial, PsyDial, SoulChat, KMI) — EN datasets không có S2. So sánh discriminative power giữa settings cần xét điểm này.

**Spearman correlation trung bình (non-EN datasets: simpsydial, PsyDial, SoulChat, KMI):**

| | S1 | S2 | S3 |
|---|---|---|---|
| S1 | 1.000 | 0.510 | 0.503 |
| S2 | 0.510 | 1.000 | 0.501 |
| S3 | 0.503 | 0.501 | 1.000 |

**Kết luận ảnh hưởng ngôn ngữ (12 cặp so sánh, chỉ non-EN datasets):**
- Spearman S1↔S3 = **0.503** (thấp) → bản dịch ảnh hưởng đến ranking thứ hạng cá thể từng record.
- **KMI** là dataset duy nhất có sự khác biệt **có ý nghĩa thống kê** (p<0.05) giữa S1 vs S2 (Δ=−0.275) và S1 vs S3 (Δ=−0.255) → S1 (dùng `utterance_en` có sẵn) cho điểm thấp hơn đáng kể, có thể do văn bản EN gốc ít diễn đạt cảm xúc hơn bản KO.
  - ⚠️ **Giả thuyết cần kiểm chứng**: `utterance_en` của KMI là bản dịch có sẵn do tác giả dataset cung cấp, có thể "phẳng" về mặt cảm xúc và thiếu sắc thái ngôn ngữ so với bản KO gốc. **Thí nghiệm §6.6** sẽ kiểm chứng bằng cách dịch lại KO→EN qua GPT-5.1 (`S1-llm`) và so sánh với `utterance_en` (`S1-utt`).
  - Nếu **S1-llm ≈ S2** (điểm gần nhau, Spearman cao): xác nhận `utterance_en` là nguồn bias — cần báo cáo rõ trong paper và xem xét dùng S1-llm thay thế cho KMI.
  - Nếu **S1-llm ≈ S1-utt**: loại bỏ giả thuyết artifact dịch — bias có thể do đặc điểm nội dung của dataset KMI hoặc do judge xử lý KO text kém (S3).
- **ZH datasets** (simpsydial, PsyDial, SoulChat): không có khác biệt thống kê giữa các setting → bản dịch LLM không thay đổi đáng kể tổng điểm.
- S2 cho discriminative power kém nhất (Overall std=0.159 trên 4 ds) → xác nhận §3.3: S2 không phù hợp làm trục ranking chéo.

### 13.4 Thematic strength profile

| Dataset | Điểm nổi bật | Điểm yếu nhất |
|---|---|---|
| **cactus** | Toàn diện (z>+1 mọi metric) | — |
| **simpsydial** | AI-Comm, Assessment | — |
| **Psy-Insight** | Clinical, Ethics | Alliance |
| **PsyDial** | Alliance | Ethics |
| **SoulChat** | AI-Comm (tương đối) | Clinical, Assessment |
| **KMI** | Ethics (tương đối) | Alliance, AI-Comm |

### 13.5 Files output

```
data/_analysis/mind_eval/
  report.md                          ← báo cáo tổng hợp
  tables/
    summary_raw_means.csv            ← raw means 6ds × 3setting × 6metric
    summary_std.csv                  ← std tương ứng
    ranking_S1.csv                   ← z-score + mean-rank theo S1
    ranking_S3.csv                   ← z-score + mean-rank theo S3
    language_effect.csv              ← 12 cặp so sánh (4 non-EN ds × 3 cặp; EN bị loại đúng)
    discriminative_power.csv         ← std per metric per setting
  charts/
    01_overall_heatmap.png           ← heatmap Overall score ds × setting (S2="-" với EN)
    02_per_metric_heatmap_S1.png     ← heatmap 5 metric theo S1 (6 datasets)
    03_per_metric_heatmap_S3.png     ← heatmap 5 metric theo S3 (6 datasets)
    04_language_effect_S1_S3.png     ← scatter S1 vs S3 (translation effect, non-EN)
    05_language_effect_S2_S3.png     ← scatter S2 vs S3 (judge-lang effect, non-EN)
    06_boxplot_settings.png          ← boxplot Overall per dataset × setting (S1/S2/S3)
    07_strength_profile_S1.png       ← radar chart z-score strength profile (S1)
    08_ranking_bar_S1.png            ← grouped bar z-score per metric per dataset (S1)
    09_spearman_heatmap.png          ← Spearman corr matrix S1/S2/S3 (non-EN)
    10_criterion_comparison_all.png  ← S1/S2/S3 per metric per dataset (S2 gạch chéo=non-EN)
    11_per_metric_heatmap_S2.png     ← heatmap 5 metric theo S2 (S2="-" với EN datasets)
```

---

---

## 14. Pipeline đầy đủ — thứ tự lệnh từ đầu đến cuối

> **Thư mục làm việc**: `H:\Vy\Paper\Empathy\Code\mind-eval\mind-eval`

### 14.1 Bước 0 — Chuẩn bị (1 lần)

```powershell
cd H:\Vy\Paper\Empathy\Code\mind-eval\mind-eval

# Kiểm tra datasets đã đăng ký
python evaluate.py --list

# Xem trước toàn bộ jobs sẽ chạy (không gọi API)
python -m mindeval.scripts.run_eval_matrix --dry_run --eval mind-eval
```

---

### 14.2 Bước 1 — Dịch S1 (chỉ dataset ZH + KMI KO)

Dữ liệu EN (cactus, Psy-Insight) không cần dịch — dùng trực tiếp canonical.

```powershell
# ── Pilot N=20 ──
# ZH datasets: simpsydial, PsyDial, SoulChat → EN
python -m mindeval.scripts.translate_to_en --datasets simpsydial psydial soulchat --limit 20

# KMI: KO → EN (dùng LLM thay cho utterance_en có sẵn — xem §6.6)
python -m mindeval.scripts.translate_to_en --datasets kmi_ko --limit 20

# ── Full 200 ──
python -m mindeval.scripts.translate_to_en --datasets simpsydial psydial soulchat
python -m mindeval.scripts.translate_to_en --datasets kmi_ko
```

Kết quả:
```
data/simpsydial/test/interactions_200_S1_en.jsonl
data/PsyDial/test/interactions_200_S1_en.jsonl
data/SoulChat/test/interactions_200_S1_en.jsonl
data/KMI/test/interactions_200_S1_ko_translated_en.jsonl
```

---

### 14.3 Bước 2 — Đánh giá judge GPT

```powershell
# ── Pilot N=20 ──
python -m mindeval.scripts.run_eval_matrix --pilot --pilot_n 20 --judge_name gpt --eval mind-eval --max_workers 3

# ── Full 200 ── (sau khi pilot phân tích xong)
python -m mindeval.scripts.run_eval_matrix --full --judge_name gpt --eval mind-eval --max_workers 5
```

Jobs chạy (14 jobs pilot, bỏ S2 cho EN datasets):
| # | Dataset | Setting | Input |
|---|---|---|---|
| 1 | simpsydial | S1 | `*_S1_en.jsonl` |
| 2 | simpsydial | S2 | `*_canonical.jsonl` + judge ZH |
| 3 | simpsydial | S3 | `*_canonical.jsonl` + judge EN |
| 4 | PsyDial | S1 | `*_S1_en.jsonl` |
| 5 | PsyDial | S2 | `*_canonical.jsonl` + judge ZH |
| 6 | PsyDial | S3 | `*_canonical.jsonl` + judge EN |
| 7 | SoulChat | S1 | `*_S1_en.jsonl` |
| 8 | SoulChat | S2 | `*_canonical.jsonl` + judge ZH |
| 9 | SoulChat | S3 | `*_canonical.jsonl` + judge EN |
| 10 | KMI | S1 | `*_S1_ko_translated_en.jsonl` |
| 11 | KMI | S2 | `*_canonical_ko.jsonl` + judge KO |
| 12 | KMI | S3 | `*_canonical_ko.jsonl` + judge EN |
| 13 | cactus | S1 | `*_canonical.jsonl` → copy → S3 |
| 14 | Psy-Insight | S1 | `*_canonical.jsonl` → copy → S3 |

---

### 14.4 Bước 3 — Đánh giá judge Claude (so sánh với GPT)

> Anthropic rate limit: dùng `max_workers=1` và `batch_delay=5`.

```powershell
# ── Pilot N=20 ──
python -m mindeval.scripts.run_eval_matrix --pilot --pilot_n 20 --judge_name claude --eval mind-eval --max_workers 1 --batch_delay 5

# ── Full 200 ──
python -m mindeval.scripts.run_eval_matrix --full --judge_name claude --eval mind-eval --max_workers 1 --batch_delay 5
```

Resume tự động (skip_existing ID-based) — nếu bị gián đoạn, chạy lại lệnh tương tự.

---

### 14.5 Bước 4 — Phân tích kết quả

```powershell
# ── Phân tích GPT judge ──
# Output: data/_analysis/mind_eval/ (Chart 1–12 + report.md)
python -m mindeval.scripts.analyze_results

# ── Phân tích so sánh GPT vs Claude ──
# Output: thêm Chart 13 (judge comparison) + Section 9 vào report.md
python -m mindeval.scripts.analyze_results --judge_name claude

# ── Lưu sang thư mục riêng (tùy chọn) ──
python -m mindeval.scripts.analyze_results --judge_name claude --output_dir data/_analysis/mind_eval_v2
```

Output:
```
data/_analysis/mind_eval/
  report.md                              ← báo cáo tổng hợp (tất cả sections)
  tables/
    summary_raw_means.csv
    ranking_S1.csv, ranking_S3.csv
    language_effect.csv
    discriminative_power.csv
  charts/
    01_overall_heatmap.png  …  12_kmi_translation.png
    13_judge_comparison_claude.png        ← chỉ có khi --judge_name claude
```

---

### 14.5b Bước 5 — Đánh giá WAI-O-S (Dim-B)

> Chạy **sau** Bước 2 (Dim-A GPT) hoặc song song. WAI không phụ thuộc kết quả Dim-A.

#### Thiết kế S1 / S3 cho WAI

| Setting | Input | Prompt | Áp dụng |
|---|---|---|---|
| **S1** | EN-translated dialogue (`*_S1_en.jsonl`) | English WAI prompts | Non-EN datasets |
| **S3** | Native-language dialogue (`*_canonical.jsonl`) | English WAI prompts | Non-EN datasets |
| **EN datasets** | Canonical EN file (không dịch) | English WAI prompts | S1 only; S3 = copy S1 |

> **S2 không áp dụng cho WAI**: WAI-O-S không có bản native-language judge — prompt chỉ tồn tại bằng tiếng Anh.

> **EN datasets (cactus, Psy-Insight, AnnoMI, ESConv)**: S1 = S3 (cùng file), chỉ chạy S1; `copy_en_results()` tự copy `S1_gpt_wai_judgments.jsonl` → `S3_gpt_wai_judgments.jsonl` sau khi chạy xong.

#### Dataset coverage (11 datasets)

| Dataset | Lang | S1 file | S3 file | Trạng thái |
|---|---|---|---|---|
| cactus | en | canonical | = S1 (copy) | ✓ S1+S3 có |
| Psy-Insight | en | canonical | = S1 (copy) | ✓ S1+S3 có |
| AnnoMI | en | canonical | = S1 (copy) | ✓ S1 có; S3 sẽ copy |
| ESConv | en | canonical | = S1 (copy) | chạy mới |
| simpsydial | zh | `*_S1_en.jsonl` (20 records) | `*_canonical.jsonl` | ✓ S1+S3 có |
| PsyDial | zh | `*_S1_en.jsonl` (20 records) | `*_canonical.jsonl` | ✓ S1+S3 có |
| SoulChat | zh | `*_S1_en.jsonl` (20 records) | `*_canonical.jsonl` | ✓ S1+S3 có |
| CPsyCoun | zh | `*_S1_en.jsonl` (20 records) | `*_canonical.jsonl` | chạy mới |
| smile | zh | `*_S1_en.jsonl` (20 records) | `*_canonical.jsonl` | chạy mới |
| KokoroChat | ja | `*_S1_en.jsonl` (20 records) | `*_canonical.jsonl` | chạy mới |
| KMI | ko | `*_S1_en.jsonl` (200 records, cap 20) | `*_canonical_ko.jsonl` | ✓ S1+S3 có |

#### Lệnh chạy

```powershell
# ── Pilot N=20 — tất cả dataset, S1+S3, skip existing tự động ──
cd "H:\Vy\Paper\Empathy\Code\mind-eval\mind-eval"
python -m mindeval.scripts.run_eval_matrix --pilot --eval wai --settings S1 S3

# ── Chạy từng dataset (resume nếu gián đoạn) ──
python evaluate.py --dataset cpscycoun  --option S1 --eval wai --max_dialogues 20
python evaluate.py --dataset smile      --option S1 --eval wai --max_dialogues 20
python evaluate.py --dataset kokorochat --option S1 --eval wai --max_dialogues 20
python evaluate.py --dataset esconv     --option S1 --eval wai --max_dialogues 20

# ── Full 200 (kết quả chính thức — n_runs=3) ──
python -m mindeval.scripts.run_eval_matrix --full --eval wai --settings S1 S3 --wai_n_runs 3
```

> **Tham số `--wai_pilot_n`** (default 20): điều chỉnh pilot size cho WAI (áp dụng cho KO/EN/JA datasets; ZH S1 files đã pre-sized 20 records → không cần cap).
> **Batch mode**: 12 câu hỏi gộp vào 1 LLM call → `n_runs=3`: 3 calls/record/dataset.
> **Skip logic**: `skip_existing` dùng `interaction_id` → resume bất kỳ lúc nào.

Output:
```
data/<dataset>/results/wai/
  S1_gpt_wai_judgments.jsonl   ← EN-translated dialogue + EN WAI prompts
  S3_gpt_wai_judgments.jsonl   ← native dialogue + EN WAI prompts (EN: copy từ S1)
```

---

### 14.5c Bước 6 — Phân tích WAI-O-S

```powershell
# ── Phân tích S3 (baseline, tất cả dataset) ──
# Output: data/_analysis/wai/ (6 charts + 3 tables + report.md)
python -m mindeval.scripts.analyze_wai_results --setting S3

# ── Phân tích S1 ──
python -m mindeval.scripts.analyze_wai_results --setting S1

# ── So sánh S1 vs S3 (delta heatmap + correlation) ──
# Output: thêm tables/compare_S1_vs_S3.csv + charts/07_compare_S1_vs_S3_heatmap.png + report_compare_S1_vs_S3.md
python -m mindeval.scripts.analyze_wai_results --setting S3 --compare --setting_a S1 --setting_b S3
```

Output:
```
data/_analysis/wai/
  report.md                              ← báo cáo tổng hợp (S3)
  report_compare_S1_vs_S3.md            ← delta table + interpretation
  tables/
    summary_raw_means.csv               ← raw mean ± std per dataset per dimension
    ranking_S3.csv                      ← z-score per dimension + mean-rank (S3)
    per_question_means.csv              ← mean per Q1–Q12 per dataset
    compare_S1_vs_S3.csv               ← delta S1−S3 per dataset × dimension
  charts/
    01_dimension_heatmap.png            ← heatmap Goal/Approach/Bond × datasets
    02_per_question_heatmap.png         ← heatmap Q1–Q12 × datasets
    03_strength_profile.png             ← radar chart z-score 3 dimensions
    04_ranking_bar.png                  ← grouped bar z-score per dataset
    05_boxplot_dims.png                 ← boxplot Total WAI per dataset
    06_total_bar.png                    ← horizontal bar Mean Total WAI (sorted)
    07_compare_S1_vs_S3_heatmap.png    ← delta heatmap (green=S1 higher, red=S3 higher)
```

---

### 14.6 Thứ tự tóm tắt (tham chiếu nhanh)

```
[1] translate ZH/KO/JA → EN      translate_to_en.py
[2] evaluate Dim-A GPT (S1/S2/S3) run_eval_matrix --judge_name gpt --eval mind-eval
[3] evaluate Dim-A Claude          run_eval_matrix --judge_name claude --eval mind-eval
[4] analyze Dim-A (GPT only)       analyze_results.py
[4'] analyze Dim-A (GPT + Claude)  analyze_results.py --judge_name claude
[5] evaluate Dim-B WAI S1+S3       run_eval_matrix --eval wai --settings S1 S3
     └─ EN datasets: chỉ chạy S1; copy_en_results tự copy S1→S3
     └─ Non-EN: S1 (EN-translated) + S3 (native) đều chạy
[6] analyze Dim-B WAI              analyze_wai_results.py --setting S3
[6'] compare S1 vs S3              analyze_wai_results.py --setting S3 --compare
```

> Bước [2] và [3] độc lập — có thể chạy [3] trước hoặc song song nếu đủ credit.
> Bước [5] và [2] độc lập — có thể chạy song song.
> `skip_existing` đảm bảo có thể resume bất kỳ bước nào khi bị gián đoạn.

---

## 16. Kết quả phân tích pilot (N=20) — Dim-B WAI-O-S

> Script: `python -m mindeval.scripts.analyze_wai_results --setting S3`
> Output: `data/_analysis/wai/` | Thang điểm 1–5 | n_runs=3 | judge GPT | setting S3
> **Dataset coverage (Jun 2026)**: 11 datasets — xem §14.5b cho trạng thái từng dataset.

### 16.1 Phương pháp WAI-O-S

**Nguồn**: Li et al. (2024) — Working Alliance Inventory, phiên bản rút gọn 12 mục (WAI-O-S).

**3 dimension** đánh giá liên minh trị liệu:
| Dimension | Câu hỏi | Mô tả |
|---|---|---|
| Goal | Q1, Q4, Q7, Q10 | Sự đồng thuận về mục tiêu trị liệu |
| Approach | Q2, Q5, Q8, Q11 | Sự đồng thuận về phương pháp/chiến lược |
| Affective Bond | Q3, Q6, Q9, Q12 | Mối liên kết cảm xúc giữa client–therapist |

**Chain-of-Thought prompting**: Mỗi câu hỏi yêu cầu LLM cung cấp:
- `evidence`: trích dẫn trực tiếp từ hội thoại
- `analysis`: lý giải tại sao evidence hỗ trợ mức điểm
- `score`: 1–5 theo detailed rubric

**Batch mode** (mặc định): 12 câu hỏi gộp vào 1 LLM call/run.
- `n_runs=1`: 1 call/record (pilot, nhanh, tiết kiệm token)
- `n_runs=3`: 3 calls/record → lấy mean (kết quả chính thức)

### 16.2 Rubric fix quan trọng (Q1 & Q3)

Rubric gốc Li et al. (2024) Appendix A.3 có lỗi đảo ngữ nghĩa tại Q1 (Goal) và Q3 (Affective Bond):

| Trước fix | Sau fix |
|---|---|
| Level 2 mô tả liên minh TỐT → điểm thấp (sai) | Level 2 mô tả liên minh YẾU → điểm thấp (đúng) |
| Level 4 mô tả liên minh YẾU → điểm cao (sai) | Level 4 mô tả liên minh TỐT → điểm cao (đúng) |

→ Fix: hoán đổi nội dung level 2 ↔ 4 trong `wai_evaluator.py` (`DETAILED_GUIDELINES`).
→ Sau fix: thang đo monotonic (1=xấu nhất → 5=tốt nhất) cho tất cả 12 câu.

### 16.3 Ranking tổng hợp (Total WAI, N=20, S3)

> **Xem \data/_analysis/wai/report.md\** va \	ables/ranking_S3.csv\ de co so lieu cap nhat sau moi lan chay \nalyze_wai_results.py\. Bang duoi la placeholder.

| # | Dataset | Lang | Goal | Approach | Bond | **Total** |
|---|---|---|---|---|---|---|
| 1 | cactus | en | — | — | — | — |
| 2 | Psy-Insight | en | — | — | — | — |
| 3 | AnnoMI | en | — | — | — | — |
| 4 | ESConv | en | — | — | — | — |
| 5 | simpsydial | zh | — | — | — | — |
| 6 | PsyDial | zh | — | — | — | — |
| 7 | CPsyCoun | zh | — | — | — | — |
| 8 | SoulChat | zh | — | — | — | — |
| 9 | smile | zh | — | — | — | — |
| 10 | KokoroChat | ja | — | — | — | — |
| 11 | KMI | ko | — | — | — | — |

> **Pilot cu (6 dataset, n_runs=3, S3)**: cactus ~4.36 > simpsydial ~4.22 > PsyDial ~4.12 > SoulChat ~4.03 > KMI ~3.78 > Psy-Insight ~3.35.

### 16.4 Nhan xet phuong phap luan

- **S1 vs S3 non-EN**: Sau khi co du ket qua, chay \--compare\ de do translation effect (S1-S3 delta).
- **EN datasets (S1=S3)**: File S3 duoc copy tu S1 boi \copy_en_results\. Delta nho la nhieu LLM stochasticity.
- **Q1/Q3 sau fix**: Goal dimension nhat quan voi Approach va Affective Bond.
- **Consistency Dim-A vs Dim-B**: Dataset xep hang cao Dim-A co xu huong xep hang cao Dim-B.
- **Can full run**: 200 records voi n_runs=3 truoc khi bao cao chinh thuc.

### 16.5 Files va lenh tham chieu nhanh

\\powershell
# Chay tat ca dataset, S1+S3 (skip existing tu dong)
python -m mindeval.scripts.run_eval_matrix --pilot --eval wai --settings S1 S3

# Phan tich S3
python -m mindeval.scripts.analyze_wai_results --setting S3

# So sanh S1 vs S3
python -m mindeval.scripts.analyze_wai_results --setting S3 --compare --setting_a S1 --setting_b S3
\
\data/_analysis/wai/
  report.md                           <- bao cao tong hop S3
  report_compare_S1_vs_S3.md         <- delta + interpretation
  tables/
    summary_raw_means.csv
    ranking_S3.csv
    per_question_means.csv
    compare_S1_vs_S3.csv
  charts/
    01_dimension_heatmap.png
    02_per_question_heatmap.png
    03_strength_profile.png
    04_ranking_bar.png
    05_boxplot_dims.png
    06_total_bar.png
    07_compare_S1_vs_S3_heatmap.png  <- delta heatmap
\
---

## 12. Quyết định còn mở (cần xác nhận trước khi code)
1. Translator nào ngoài GPT muốn thử (Claude / Qwen / Gemini / Google Translate)? — để chuẩn bị config & API key.
2. Pilot dịch chạy trên những dataset nào? (đề xuất: 3 ZH — simpsydial, PsyDial, SoulChat).
3. Ngưỡng coi là "S1 ≈ S3" (vd Spearman ≥ 0.9 và |Δ z-score| nhỏ)?
4. Dim-B có chạy full 200 hay giới hạn khi thử (vì tốn token)?
5. **[Profile covariate]** Có cần chạy sensitivity analysis: so sánh điểm cactus khi dùng profile thực vs khi truyền `null` (để đo impact của profile lên điểm judge)? Nếu impact lớn → cần báo cáo riêng; nếu nhỏ → có thể merge kết quả.

---

## 15. Thông tin model judge

| Judge | Model config | Ghi chú |
|---|---|---|
| GPT | `gpt-5.1` (key: `judges.gpt` trong `config.json`) | max_workers=3, temperature=0 |
| Claude | `anthropic/claude-sonnet-4-6` (key: `judges.claude` trong `config.json`) | max_workers=1, batch_delay=5, timeout=180s (Anthropic rate limit) |


### câu lệnh chạy từng dataset full 200 records
python evaluate.py --dataset cpscycoun --option S3 --eval mind-eval --judge_name claude_9router --output_suffix _full --max_workers 1 --batch_delay 3