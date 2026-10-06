# Dimension C — Emotional Trajectory Profiling Pipeline
## UED Framework + NRC-VAD Lexicon v2 | Phương án C (Dual-Lexicon Comparison)

> **Mục tiêu**: Đánh giá quỹ đạo cảm xúc phía client trong các counseling dialogue datasets,
> sử dụng framework UED (Hipson & Mohammad, 2021) theo protocol "Feel the Difference"
> (Wang et al., EMNLP 2025 Findings).
>
> **Phương án C**: Chạy song song Approach A (lexicon bản ngữ) và Approach B (dịch sang EN + lexicon EN),
> so sánh ranking stability → biến limitation thành finding.

---

## 0. Prerequisites

### 0.1 Cài đặt packages

```bash
# Python >= 3.9
pip install numpy pandas scipy matplotlib seaborn

# UED metrics — clone repo gốc của nhóm Mohammad
git clone https://github.com/Priya22/EmotionDynamics.git
cd EmotionDynamics
pip install -e .

# Emotion arcs evaluation (repo Teodorescu & Mohammad 2023)
git clone https://github.com/dteodore/EmotionArcs.git

# Tokenizer (tùy ngôn ngữ)
pip install jieba       # ZH
pip install konlpy      # KO (cần JDK)
pip install fugashi     # JA
pip install underthesea  # VI (nếu chạy pilot)
pip install nltk         # EN
```

### 0.2 Tải NRC-VAD Lexicon v2

- URL: http://saifmohammad.com/WebPages/nrc-vad.html
- Tải file zip, giải nén → thư mục chứa:
  - `NRC-VAD-Lexicon-v2.txt` (EN, ~55K entries)
  - `OneFilePerLanguage/` → các file theo ngôn ngữ:
    - `Chinese-Simplified-NRC-VAD-Lexicon.txt`
    - `Korean-NRC-VAD-Lexicon.txt`
    - `Japanese-NRC-VAD-Lexicon.txt`
    - `Vietnamese-NRC-VAD-Lexicon.txt` (cho pilot)
- Format mỗi file: `word \t valence \t arousal \t dominance`
- Thang điểm: 0–1 (0 = cực tiêu cực/thụ động/yếu, 1 = cực tích cực/chủ động/mạnh)

### 0.3 Chuẩn bị datasets

Danh sách 11 multi-turn datasets (xem Bảng 1 trong Dataset_Audit_Tables.pptx).
Mỗi dataset cần format chuẩn trước khi chạy pipeline:

```
data/
├── cactus/
│   ├── dialogues.jsonl       # mỗi dòng = 1 dialogue
│   └── metadata.json         # thông tin dataset
├── annomi/
│   ├── dialogues.jsonl
│   └── metadata.json
├── ...
```

Format mỗi dialogue trong `dialogues.jsonl`:

```json
{
  "dialogue_id": "cactus_001",
  "dataset": "cactus",
  "language": "en",
  "turns": [
    {"role": "counselor", "text": "How are you feeling today?"},
    {"role": "client", "text": "I've been really anxious lately..."},
    {"role": "counselor", "text": "Can you tell me more about that?"},
    {"role": "client", "text": "It started about two weeks ago when..."}
  ]
}
```

**Lưu ý quan trọng về role mapping:**
- Mỗi dataset có tên role khác nhau (therapist/counselor/supporter/helper vs client/patient/seeker/user)
- Cần mapping thống nhất về `counselor` và `client` trước khi chạy
- Tạo file `role_mapping.json` cho mỗi dataset

---

## 1. Bước 1 — Tách utterances theo speaker

### 1.1 Mục tiêu
Tách riêng chuỗi utterances của CLIENT và COUNSELOR cho mỗi dialogue.
Trọng tâm Dim C = client. Counselor chạy song song để đối chiếu.

### 1.2 Logic

```python
def extract_speaker_texts(dialogue, role="client"):
    """
    Trích xuất tất cả utterances của 1 speaker,
    giữ đúng thứ tự thời gian.

    Returns:
        texts: list[str] — danh sách utterances theo thứ tự
        word_sequence: str — nối tất cả thành 1 chuỗi từ liên tục
    """
    texts = [
        turn["text"]
        for turn in dialogue["turns"]
        if turn["role"] == role
    ]
    word_sequence = " ".join(texts)
    return texts, word_sequence
```

### 1.3 Chạy cho cả hai speaker

```python
for dialogue in dataset:
    client_texts, client_words = extract_speaker_texts(dialogue, "client")
    counselor_texts, counselor_words = extract_speaker_texts(dialogue, "counselor")
```

### 1.4 Edge case cần xử lý
- **Client chỉ nói 1–2 lượt hoặc < 20 từ**: arc quá ngắn → UED metrics không có ý nghĩa.
  Ngưỡng tối thiểu: **≥ 30 từ client** (để rolling window 10 tạo ít nhất 21 điểm).
  Dialogues dưới ngưỡng → loại khỏi tính toán, ghi lại số lượng loại trong paper.
- **Client chỉ nói "vâng", "ừ"**: các từ này thường không có trong lexicon → cửa sổ trống → bỏ qua.

---

## 2. Bước 2 — Tokenization theo ngôn ngữ

### 2.1 Mục tiêu
Chuyển chuỗi từ thành danh sách tokens. Bước này khác nhau theo ngôn ngữ.

### 2.2 Logic

```python
import nltk
import jieba
import fugashi

def tokenize(text, language):
    """Tokenize text theo ngôn ngữ."""
    text = text.lower().strip()

    if language == "en":
        return nltk.word_tokenize(text)

    elif language == "zh":
        return list(jieba.cut(text))

    elif language == "ko":
        from konlpy.tag import Okt
        okt = Okt()
        return okt.morphs(text)

    elif language == "ja":
        tagger = fugashi.Tagger()
        return [word.surface for word in tagger(text)]

    elif language == "vi":
        from underthesea import word_tokenize
        tokens = word_tokenize(text)
        # underthesea trả về multi-word tokens dạng "sinh_viên"
        # → giữ nguyên vì lexicon VN cũng dùng format này
        return tokens.split()

    else:
        return text.split()
```

### 2.3 Lưu ý
- Lowercase cho EN; các ngôn ngữ khác giữ nguyên case
- Loại bỏ punctuation, số, ký tự đặc biệt trước khi tokenize
- Giữ lại stopwords (UED dùng tất cả từ, không lọc)

---

## 3. Bước 3 — Tính emotion scores bằng rolling window

> ⚠️ **ĐÂY LÀ BƯỚC QUAN TRỌNG NHẤT — KHÔNG TÍNH PER-UTTERANCE**
>
> UED tính emotion score trên **rolling window cấp từ**,
> KHÔNG PHẢI trên từng utterance.

### 3.1 Load lexicon

```python
def load_vad_lexicon(filepath):
    """
    Load NRC-VAD lexicon từ file.
    Returns: dict[str, tuple(float, float, float)]
             word → (valence, arousal, dominance)
    """
    lexicon = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 4:
                word = parts[0].lower()
                v, a, d = float(parts[1]), float(parts[2]), float(parts[3])
                lexicon[word] = (v, a, d)
    return lexicon
```

### 3.2 Tính emotion arc bằng rolling window

```python
import numpy as np

def compute_emotion_arc(tokens, lexicon, window_size=10, step=1):
    """
    Tính emotion arc từ chuỗi tokens bằng rolling window.

    Tại mỗi cửa sổ:
    1. Lấy window_size tokens
    2. Tra từng token trong lexicon
    3. Tính trung bình V, A, D của các tokens CÓ trong lexicon
    4. Nếu không có token nào trong lexicon → bỏ qua cửa sổ này

    Args:
        tokens: list[str] — chuỗi từ đã tokenize
        lexicon: dict — NRC-VAD lexicon
        window_size: int — kích thước cửa sổ (default 10, theo Feel the Difference)
        step: int — bước trượt (default 1)

    Returns:
        arc: np.ndarray shape (N, 3) — chuỗi [V, A, D] theo thời gian
        valid_indices: list[int] — chỉ số của các cửa sổ hợp lệ
    """
    arc = []
    valid_indices = []

    for i in range(0, len(tokens) - window_size + 1, step):
        window = tokens[i : i + window_size]

        # Tra lexicon
        scores = [lexicon[w] for w in window if w in lexicon]

        if len(scores) == 0:
            continue  # Bỏ qua cửa sổ không có từ nào trong lexicon

        scores = np.array(scores)
        mean_vad = scores.mean(axis=0)  # [mean_V, mean_A, mean_D]
        arc.append(mean_vad)
        valid_indices.append(i)

    if len(arc) == 0:
        return None, []

    return np.array(arc), valid_indices
```

### 3.3 Cấu hình theo "Feel the Difference"

```python
CONFIG = {
    "window_size": 10,   # theo Wang et al. 2025
    "step": 1,           # trượt 1 từ mỗi bước
    "min_tokens": 30,    # tối thiểu 30 từ client để tính arc
    "dimensions": ["valence", "arousal", "dominance"],  # 3 chiều VAD
}
```

### 3.4 Chạy cho cả Approach A và Approach B

```python
# === APPROACH A: Lexicon bản ngữ ===
LEXICON_PATHS = {
    "en": "lexicons/NRC-VAD-Lexicon-v2.txt",
    "zh": "lexicons/Chinese-Simplified-NRC-VAD-Lexicon.txt",
    "ko": "lexicons/Korean-NRC-VAD-Lexicon.txt",
    "ja": "lexicons/Japanese-NRC-VAD-Lexicon.txt",
    "vi": "lexicons/Vietnamese-NRC-VAD-Lexicon.txt",
}

def run_approach_a(dialogue, language):
    """Approach A: dùng lexicon bản ngữ trên text gốc."""
    lexicon = load_vad_lexicon(LEXICON_PATHS[language])
    _, client_words = extract_speaker_texts(dialogue, "client")
    tokens = tokenize(client_words, language)

    if len(tokens) < CONFIG["min_tokens"]:
        return None  # Quá ngắn

    arc, indices = compute_emotion_arc(tokens, lexicon, CONFIG["window_size"])
    return arc


# === APPROACH B: Dịch sang EN + lexicon EN ===
def translate_to_en(text, source_lang):
    """
    Dịch text sang EN.
    Dùng GPT hoặc Google Translate API.
    Lưu bản dịch để reproducibility.

    LƯU Ý: KHÔNG dùng bản dịch có sẵn trong dataset (utterance_en)
    vì đã chứng minh translation artifact ở Dim A (F4).
    Dùng 1 pipeline dịch thống nhất cho tất cả.
    """
    # TODO: implement translation
    # Gợi ý: dùng GPT-4o-mini hoặc Google Translate API
    # Cache kết quả để tránh gọi lại
    pass

def run_approach_b(dialogue, language):
    """Approach B: dịch sang EN rồi dùng lexicon EN."""
    if language == "en":
        return run_approach_a(dialogue, "en")  # Không cần dịch

    lexicon_en = load_vad_lexicon(LEXICON_PATHS["en"])
    _, client_words = extract_speaker_texts(dialogue, "client")
    translated = translate_to_en(client_words, language)
    tokens = tokenize(translated, "en")

    if len(tokens) < CONFIG["min_tokens"]:
        return None

    arc, indices = compute_emotion_arc(tokens, lexicon_en, CONFIG["window_size"])
    return arc
```

---

## 4. Bước 4 — Tính UED metrics từ emotion arc

### 4.1 Danh sách metrics đầy đủ

Dùng EmotionDynamics package hoặc tự implement theo định nghĩa dưới đây.
Tính **riêng cho từng chiều V, A, D** → 14 metrics × 3 chiều = 42 giá trị per speaker per dialogue.

#### Nhóm Overall (6 metrics per dimension)

| Metric | Ký hiệu | Định nghĩa | Ý nghĩa tâm lý |
|--------|----------|-------------|-----------------|
| Emotion Mean | `emo_mean` | mean(arc) | Trạng thái cảm xúc trung bình (home base proxy) |
| Variability | `emo_std` | std(arc) | Mức dao động cảm xúc — cao = bất ổn, thấp = phẳng |
| Avg Peak Distance | `emo_avg_peak_dist` | mean(peak distances of all displacements) | Cường độ trung bình khi rời home base |
| Avg Displacement Length | `emo_avg_disp_length` | mean(lengths of all displacements in timesteps) | Thời gian trung bình ở ngoài home base |
| Rise Rate | `emo_rise_rate` | mean(peak_dist / rise_duration for all displacements) | Tốc độ phản ứng cảm xúc (emotional reactivity) |
| Recovery Rate | `emo_recovery_rate` | mean(peak_dist / recovery_duration for all displacements) | Tốc độ hồi phục cảm xúc (emotion regulation) |

#### Nhóm tách theo hướng displacement (8 metrics per dimension)

| Metric | Ký hiệu | Hướng |
|--------|----------|-------|
| Low Peak Distance | `emo_low_peak_dist` | Displacement DƯỚI home base (client trở nên tiêu cực) |
| Low Displacement Length | `emo_low_disp_length` | ← |
| Low Rise Rate | `emo_low_rise_rate` | Tốc độ rơi vào trạng thái tiêu cực |
| Low Recovery Rate | `emo_low_recovery_rate` | Tốc độ hồi phục TỪ trạng thái tiêu cực |
| High Peak Distance | `emo_high_peak_dist` | Displacement TRÊN home base (client trở nên tích cực) |
| High Displacement Length | `emo_high_disp_length` | ← |
| High Rise Rate | `emo_high_rise_rate` | Tốc độ đạt trạng thái tích cực |
| High Recovery Rate | `emo_high_recovery_rate` | Tốc độ rơi TỪ trạng thái tích cực |

### 4.2 Tính displacement và các metric liên quan

```python
def compute_ued_metrics(arc_1d):
    """
    Tính toàn bộ UED metrics cho 1 chiều (V hoặc A hoặc D).

    Args:
        arc_1d: np.ndarray shape (N,) — chuỗi emotion scores 1 chiều

    Returns:
        dict — tất cả UED metrics
    """
    if arc_1d is None or len(arc_1d) < 10:
        return None

    mean = np.mean(arc_1d)
    std = np.std(arc_1d)

    # Home base: [mean - std, mean + std]
    home_low = mean - std
    home_high = mean + std

    # Tìm displacements: các đoạn liên tục nằm ngoài home base
    displacements = []
    current_disp = None

    for t, val in enumerate(arc_1d):
        outside = val < home_low or val > home_high

        if outside:
            if current_disp is None:
                current_disp = {
                    "start": t,
                    "values": [val],
                    "direction": "low" if val < home_low else "high"
                }
            else:
                current_disp["values"].append(val)
        else:
            if current_disp is not None:
                current_disp["end"] = t - 1
                displacements.append(current_disp)
                current_disp = None

    # Đóng displacement cuối nếu arc kết thúc ngoài home base
    if current_disp is not None:
        current_disp["end"] = len(arc_1d) - 1
        displacements.append(current_disp)

    # Tính metrics cho mỗi displacement
    all_peak_dist = []
    all_disp_length = []
    all_rise_rate = []
    all_recovery_rate = []

    low_peak_dist, low_disp_length, low_rise_rate, low_recovery_rate = [], [], [], []
    high_peak_dist, high_disp_length, high_rise_rate, high_recovery_rate = [], [], [], []

    for disp in displacements:
        values = np.array(disp["values"])
        length = len(values)

        if disp["direction"] == "low":
            peak_val = np.min(values)
            peak_idx = np.argmin(values)
        else:
            peak_val = np.max(values)
            peak_idx = np.argmax(values)

        peak_dist = abs(peak_val - mean)

        # Rise: từ đầu displacement đến peak
        rise_duration = peak_idx + 1  # +1 vì index 0-based
        rise_rate = peak_dist / rise_duration if rise_duration > 0 else 0

        # Recovery: từ peak đến cuối displacement
        recovery_duration = length - peak_idx
        recovery_rate = peak_dist / recovery_duration if recovery_duration > 0 else 0

        # Overall
        all_peak_dist.append(peak_dist)
        all_disp_length.append(length)
        all_rise_rate.append(rise_rate)
        all_recovery_rate.append(recovery_rate)

        # Tách theo hướng
        target = (low_peak_dist, low_disp_length, low_rise_rate, low_recovery_rate) \
            if disp["direction"] == "low" else \
            (high_peak_dist, high_disp_length, high_rise_rate, high_recovery_rate)

        target[0].append(peak_dist)
        target[1].append(length)
        target[2].append(rise_rate)
        target[3].append(recovery_rate)

    def safe_mean(lst):
        return float(np.mean(lst)) if len(lst) > 0 else None

    return {
        "emo_mean": float(mean),
        "emo_std": float(std),
        "emo_avg_peak_dist": safe_mean(all_peak_dist),
        "emo_avg_disp_length": safe_mean(all_disp_length),
        "emo_rise_rate": safe_mean(all_rise_rate),
        "emo_recovery_rate": safe_mean(all_recovery_rate),
        "emo_low_peak_dist": safe_mean(low_peak_dist),
        "emo_low_disp_length": safe_mean(low_disp_length),
        "emo_low_rise_rate": safe_mean(low_rise_rate),
        "emo_low_recovery_rate": safe_mean(low_recovery_rate),
        "emo_high_peak_dist": safe_mean(high_peak_dist),
        "emo_high_disp_length": safe_mean(high_disp_length),
        "emo_high_rise_rate": safe_mean(high_rise_rate),
        "emo_high_recovery_rate": safe_mean(high_recovery_rate),
        "n_displacements": len(displacements),
        "n_low_displacements": len(low_peak_dist),
        "n_high_displacements": len(high_peak_dist),
    }
```

### 4.3 Tính cho cả 3 chiều V, A, D

```python
def compute_full_ued(arc_3d):
    """
    Tính UED metrics cho cả 3 chiều.

    Args:
        arc_3d: np.ndarray shape (N, 3) — [V, A, D] per timestep

    Returns:
        dict — metrics có prefix valence_/arousal_/dominance_
    """
    dim_names = ["valence", "arousal", "dominance"]
    all_metrics = {}

    for i, dim in enumerate(dim_names):
        metrics = compute_ued_metrics(arc_3d[:, i])
        if metrics is None:
            continue
        for key, val in metrics.items():
            all_metrics[f"{dim}_{key}"] = val

    return all_metrics
```

### 4.4 Thống kê mô tả bổ sung (ngoài UED)

```python
def compute_descriptive_stats(arc_3d, ratio=0.2):
    """
    Tính NEC và happy-ending indicator.
    Đây KHÔNG phải UED metrics — là thống kê mô tả bổ sung
    cho mục tiêu "kết quả trị liệu" của audit.

    Args:
        arc_3d: np.ndarray shape (N, 3)
        ratio: float — tỷ lệ đầu/cuối arc để tính NEC (default 20%)

    Returns:
        dict
    """
    n = len(arc_3d)
    k = max(1, int(n * ratio))

    stats = {}
    dim_names = ["valence", "arousal", "dominance"]

    for i, dim in enumerate(dim_names):
        arc = arc_3d[:, i]
        first_k = arc[:k].mean()
        last_k = arc[-k:].mean()
        nec = last_k - first_k  # Net Emotional Change

        stats[f"{dim}_nec"] = float(nec)
        stats[f"{dim}_first_mean"] = float(first_k)
        stats[f"{dim}_last_mean"] = float(last_k)
        stats[f"{dim}_happy_ending"] = bool(nec > 0)  # client kết thúc tích cực hơn?

    return stats
```

---

## 5. Bước 5 — Chạy toàn bộ pipeline

### 5.1 Main pipeline

```python
import json
import pandas as pd

def run_pipeline(dataset_path, dataset_name, language):
    """
    Chạy Dimension C pipeline cho 1 dataset.
    Chạy cả Approach A (native lexicon) và Approach B (EN lexicon).
    """
    # Load data
    with open(f"{dataset_path}/dialogues.jsonl", "r") as f:
        dialogues = [json.loads(line) for line in f]

    # Load lexicons
    lexicon_native = load_vad_lexicon(LEXICON_PATHS[language])
    lexicon_en = load_vad_lexicon(LEXICON_PATHS["en"])

    results = []

    for dlg in dialogues:
        dlg_id = dlg["dialogue_id"]

        # --- CLIENT ---
        _, client_words = extract_speaker_texts(dlg, "client")
        tokens_native = tokenize(client_words, language)

        # Approach A: native lexicon
        arc_a = None
        if len(tokens_native) >= CONFIG["min_tokens"]:
            arc_a, _ = compute_emotion_arc(
                tokens_native, lexicon_native, CONFIG["window_size"]
            )

        # Approach B: translate → EN lexicon
        arc_b = None
        if language != "en":
            translated = translate_to_en(client_words, language)
            tokens_en = tokenize(translated, "en")
            if len(tokens_en) >= CONFIG["min_tokens"]:
                arc_b, _ = compute_emotion_arc(
                    tokens_en, lexicon_en, CONFIG["window_size"]
                )
        else:
            arc_b = arc_a  # EN dataset: A và B giống nhau

        # --- COUNSELOR (đối chiếu) ---
        _, counselor_words = extract_speaker_texts(dlg, "counselor")
        tokens_counselor = tokenize(counselor_words, language)
        arc_counselor = None
        if len(tokens_counselor) >= CONFIG["min_tokens"]:
            arc_counselor, _ = compute_emotion_arc(
                tokens_counselor, lexicon_native, CONFIG["window_size"]
            )

        # --- Tính metrics ---
        row = {
            "dialogue_id": dlg_id,
            "dataset": dataset_name,
            "language": language,
            "client_n_tokens": len(tokens_native),
            "client_arc_length_a": len(arc_a) if arc_a is not None else 0,
        }

        # Client Approach A
        if arc_a is not None:
            ued_a = compute_full_ued(arc_a)
            desc_a = compute_descriptive_stats(arc_a)
            for k, v in ued_a.items():
                row[f"client_A_{k}"] = v
            for k, v in desc_a.items():
                row[f"client_A_{k}"] = v

        # Client Approach B
        if arc_b is not None:
            ued_b = compute_full_ued(arc_b)
            desc_b = compute_descriptive_stats(arc_b)
            for k, v in ued_b.items():
                row[f"client_B_{k}"] = v
            for k, v in desc_b.items():
                row[f"client_B_{k}"] = v

        # Counselor (Approach A only)
        if arc_counselor is not None:
            ued_c = compute_full_ued(arc_counselor)
            for k, v in ued_c.items():
                row[f"counselor_A_{k}"] = v

            # Variability ratio: client/counselor (proxy emotional authenticity)
            if arc_a is not None:
                for dim in ["valence", "arousal", "dominance"]:
                    c_std = row.get(f"client_A_{dim}_emo_std")
                    t_std = row.get(f"counselor_A_{dim}_emo_std")
                    if c_std and t_std and t_std > 0:
                        row[f"{dim}_variability_ratio"] = c_std / t_std

        results.append(row)

    return pd.DataFrame(results)


# === Chạy cho tất cả datasets ===
DATASETS = {
    "cactus":     {"path": "data/cactus",     "lang": "en"},
    "annomi":     {"path": "data/annomi",     "lang": "en"},
    "psy_insight":{"path": "data/psy_insight","lang": "en"},
    "esconv":     {"path": "data/esconv",     "lang": "en"},
    "psydial":    {"path": "data/psydial",    "lang": "zh"},
    "cpsycoun":   {"path": "data/cpsycoun",   "lang": "zh"},
    "simpsydial": {"path": "data/simpsydial", "lang": "zh"},
    "soulchat":   {"path": "data/soulchat",   "lang": "zh"},
    "smile":      {"path": "data/smile",      "lang": "zh"},
    "kmi":        {"path": "data/kmi",        "lang": "ko"},
    "kokoroch":   {"path": "data/kokoroch",   "lang": "ja"},
}

all_results = []
for name, info in DATASETS.items():
    print(f"Processing {name}...")
    df = run_pipeline(info["path"], name, info["lang"])
    df.to_csv(f"results/dim_c/{name}_ued.csv", index=False)
    all_results.append(df)

combined = pd.concat(all_results, ignore_index=True)
combined.to_csv("results/dim_c/all_datasets_ued.csv", index=False)
```

---

## 6. Bước 6 — Tổng hợp dataset-level & kiểm định thống kê

### 6.1 Tổng hợp per-dataset

```python
from scipy import stats as sp_stats

def aggregate_dataset(df, approach="A"):
    """Tổng hợp metrics ở cấp dataset."""
    prefix = f"client_{approach}_"
    metric_cols = [c for c in df.columns if c.startswith(prefix) and "happy_ending" not in c]

    agg = {}
    for col in metric_cols:
        metric_name = col.replace(prefix, "")
        values = df[col].dropna()
        if len(values) == 0:
            continue
        agg[metric_name] = {
            "mean": values.mean(),
            "median": values.median(),
            "std": values.std(),
            "q25": values.quantile(0.25),
            "q75": values.quantile(0.75),
            "n": len(values),
        }

    # Happy-ending rate
    for dim in ["valence", "arousal", "dominance"]:
        he_col = f"{prefix}{dim}_happy_ending"
        if he_col in df.columns:
            he_values = df[he_col].dropna()
            agg[f"{dim}_happy_ending_rate"] = he_values.mean()

    return agg
```

### 6.2 So sánh giữa các dataset/provenance

```python
def compare_groups(df, group_col, metric_col):
    """
    So sánh metric giữa các nhóm (dataset hoặc provenance tier).
    Dùng Mann-Whitney U test (2 nhóm) hoặc Kruskal-Wallis (>2 nhóm).
    """
    groups = df.groupby(group_col)[metric_col].apply(list).to_dict()
    group_names = list(groups.keys())

    if len(group_names) == 2:
        stat, p = sp_stats.mannwhitneyu(
            groups[group_names[0]],
            groups[group_names[1]],
            alternative="two-sided"
        )
        # Effect size: rank-biserial correlation
        n1, n2 = len(groups[group_names[0]]), len(groups[group_names[1]])
        r = 1 - (2 * stat) / (n1 * n2)
        return {"test": "Mann-Whitney U", "stat": stat, "p": p, "effect_size_r": r}

    else:
        stat, p = sp_stats.kruskal(
            *[groups[g] for g in group_names if len(groups[g]) > 0]
        )
        return {"test": "Kruskal-Wallis", "stat": stat, "p": p}


# So sánh theo provenance tier
PROVENANCE_MAP = {
    "annomi": "1_real", "psy_insight": "1_real",
    "psydial": "2_semi_real", "cpsycoun": "2_semi_real",
    "kokoroch": "3_human_rp", "esconv": "3_human_rp",
    "cactus": "4a_llm_scratch", "simpsydial": "4a_llm_scratch",
    "soulchat": "4a_llm_scratch", "kmi": "4a_llm_scratch",
    "smile": "4b_llm_expanded",
}
combined["provenance"] = combined["dataset"].map(PROVENANCE_MAP)
```

### 6.3 So sánh Approach A vs B (Phương án C)

```python
def compare_approaches(df, dataset_name):
    """
    So sánh ranking stability giữa Approach A và B cho 1 dataset.
    Chỉ chạy cho dataset non-EN (EN thì A=B).
    """
    key_metrics = [
        "valence_emo_mean", "valence_emo_std",
        "valence_emo_rise_rate", "valence_emo_recovery_rate",
        "valence_nec",
    ]

    results = {}
    for metric in key_metrics:
        col_a = f"client_A_{metric}"
        col_b = f"client_B_{metric}"

        if col_a not in df.columns or col_b not in df.columns:
            continue

        valid = df[[col_a, col_b]].dropna()
        if len(valid) < 5:
            continue

        # Spearman correlation giữa A và B
        rho, p = sp_stats.spearmanr(valid[col_a], valid[col_b])

        # Mean absolute difference
        mad = (valid[col_a] - valid[col_b]).abs().mean()

        results[metric] = {
            "spearman_r": rho,
            "spearman_p": p,
            "mean_abs_diff": mad,
            "mean_A": valid[col_a].mean(),
            "mean_B": valid[col_b].mean(),
        }

    return results
```

---

## 7. Bước 7 — Sanity Check với "Feel the Difference"

> Mục tiêu: xác nhận pipeline hoạt động đúng bằng cách
> so sánh kết quả CACTUS của bạn với Bảng 8 của Wang et al. (2025).

### 7.1 Giá trị tham chiếu từ "Feel the Difference" (CACTUS — Synthetic Dialogue)

```python
REFERENCE_CACTUS = {
    # Valence metrics cho Synthetic Dialogue (Bảng 8)
    "valence_emo_mean": 0.2761,
    "valence_emo_std": 0.1480,
    "valence_emo_avg_peak_dist": 0.0779,
    "valence_emo_avg_disp_length": 4.2282,
    "valence_emo_rise_rate": 0.0332,
    "valence_emo_recovery_rate": 0.0325,
    # Synthetic Client
    "valence_client_emo_mean": 0.2339,
    "valence_client_emo_std": 0.1518,
    "valence_client_emo_rise_rate": 0.0349,
    "valence_client_emo_recovery_rate": 0.0369,
}
```

### 7.2 Kiểm tra

```python
def sanity_check_cactus(your_results_df):
    """
    So sánh kết quả CACTUS của bạn với reference.
    Chấp nhận sai lệch ≤ 10% do sampling/tokenization khác.
    """
    cactus_df = your_results_df[your_results_df["dataset"] == "cactus"]

    print("=== SANITY CHECK: CACTUS vs Feel the Difference ===")
    for metric, ref_val in REFERENCE_CACTUS.items():
        col = f"client_A_{metric.replace('valence_client_', 'valence_')}"
        if col in cactus_df.columns:
            your_val = cactus_df[col].mean()
            diff_pct = abs(your_val - ref_val) / ref_val * 100
            status = "✓ OK" if diff_pct < 10 else "✗ CHECK"
            print(f"  {metric}: yours={your_val:.4f} ref={ref_val:.4f} "
                  f"diff={diff_pct:.1f}% {status}")
```

---

## 8. Output Files

Pipeline tạo ra các file sau:

```
results/dim_c/
├── {dataset}_ued.csv              # UED metrics per dialogue per dataset
├── all_datasets_ued.csv           # Tất cả datasets gộp lại
├── dataset_summary.csv            # Tổng hợp mean/median/IQR per dataset
├── provenance_comparison.csv      # Kruskal-Wallis giữa các provenance tiers
├── approach_comparison.csv        # Spearman A-vs-B cho dataset non-EN
├── happy_ending_rates.csv         # Tỷ lệ happy-ending per dataset
└── sanity_check_cactus.txt        # So sánh với Feel the Difference
```

---

## 9. Sensitivity Analysis & Robustness

### 9.1 Window size sensitivity
Chạy thêm với window_size = 20 (robustness check).
Báo cáo Spearman r giữa ranking dataset ở window=10 vs window=20.
Teodorescu & Mohammad (2023) khuyến nghị window ≥ 100 cho accuracy cao nhất,
nhưng counseling dialogues ngắn hơn narratives nên window=10 là hợp lý
(theo tiền lệ "Feel the Difference"). Khai báo đây là limitation.

### 9.2 Lexicon coverage
Báo cáo % từ client có trong lexicon, tách theo ngôn ngữ.
Nếu coverage < 30% cho 1 ngôn ngữ → kết quả ngôn ngữ đó cần caveat.

```python
def lexicon_coverage(tokens, lexicon):
    """Tính % tokens có trong lexicon."""
    if len(tokens) == 0:
        return 0
    found = sum(1 for t in tokens if t in lexicon)
    return found / len(tokens)
```

### 9.3 Validate với ESConv self-report
ESConv có self-report emotion intensity trước/sau của seeker.
Tính Spearman r giữa NEC (Valence) và Δ intensity self-report.
Nếu tương quan dương → estimator có external validity.

---

## 10. Tích hợp với Dim A & Dim B

### 10.1 Cross-dimension analysis
Sau khi có kết quả cả 3 dimensions:
- Dim A: Clinical Quality scores per dialogue
- Dim B: WAI-O-S scores per dialogue
- Dim C: UED metrics per dialogue

Tính Spearman correlation giữa:
- Dim A Overall ↔ Dim C valence_emo_mean (counselor giỏi → client positive hơn?)
- Dim B Alliance ↔ Dim C valence_emo_std (alliance cao → client ổn định hơn?)
- Dim A ↔ Dim C valence_nec (counselor giỏi → client cải thiện nhiều hơn?)

### 10.2 Provenance signature
Mỗi provenance tier có "chữ ký" riêng trên cả 3 dimensions:
- Real (tier 1): variability CAO, recovery rate CHẬM, NEC nhỏ (realistic)
- LLM from scratch (tier 4a): variability THẤP, recovery NHANH, NEC lớn (happy-ending bias)
- Nếu pattern này xuất hiện → finding chính của toàn bộ audit

---

## 11. Citation Guide

Khi viết paper, cite theo thứ tự:

1. **Framework UED**: Hipson & Mohammad (2021). "Emotion dynamics in movie dialogues." PLOS ONE.
2. **Validate đa ngôn ngữ**: Teodorescu & Mohammad (2023). "Evaluating Emotion Arcs Across Languages." EMNLP Findings.
3. **Protocol counseling**: Wang et al. (2025). "Feel the Difference?" EMNLP Findings.
4. **NRC-VAD Lexicon v2**: Mohammad (2025). "NRC VAD Lexicon v2." arXiv:2503.23547.
5. **Emotion dynamics gốc (Psychology)**: Kuppens & Verduyn (2017). "Emotion dynamics." Current Opinion in Psychology.

---

## Checklist trước khi chạy

- [ ] NRC-VAD Lexicon v2 đã tải và giải nén
- [ ] EmotionDynamics package đã cài
- [ ] Tất cả datasets đã convert sang format dialogues.jsonl chuẩn
- [ ] Role mapping đã kiểm tra cho từng dataset
- [ ] Tokenizer đã test cho từng ngôn ngữ
- [ ] Translation pipeline đã setup cho Approach B
- [ ] CACTUS sẵn sàng cho sanity check
- [ ] ESConv self-report data sẵn sàng cho validation
