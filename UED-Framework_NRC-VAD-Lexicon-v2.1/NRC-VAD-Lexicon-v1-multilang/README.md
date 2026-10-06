# NRC-VAD Lexicon v1 — Multilingual Files

Thư mục này chứa các file lexicon NRC-VAD **phiên bản 1** cho các ngôn ngữ bản ngữ.

NRC-VAD v2.1 chỉ có **tiếng Anh**. Các ngôn ngữ khác (Tiếng Trung, Tiếng Nhật, ...)
được cung cấp trong NRC-VAD **v1** dưới dạng bản dịch Google Translate (2022).

---

## Cách tải (1 lần duy nhất)

1. Truy cập: **http://saifmohammad.com/WebPages/nrc-vad.html**
2. Tải `NRC-VAD-Lexicon-v1.zip`
3. Giải nén → vào thư mục `OneFilePerLanguage/`
4. Copy **3 file** sau vào thư mục này:

| File gốc (trong zip) | Copy vào đây | Dùng cho dataset |
|---|---|---|
| `Chinese-Simplified-NRC-VAD-Lexicon.txt` | `Chinese-Simplified-NRC-VAD-Lexicon.txt` | simpsydial_zh, psydial_zh, soulchat_zh, cpsycoun_zh |
| `Japanese-NRC-VAD-Lexicon.txt` | `Japanese-NRC-VAD-Lexicon.txt` | kokorochat_ja |
| `Korean-NRC-VAD-Lexicon.txt` | `Korean-NRC-VAD-Lexicon.txt` | kmi_ko (tùy chọn) |

---

## Format file v1

```
word<TAB>valence<TAB>arousal<TAB>dominance
```

- **Scale: 0 đến 1** (khác v2.1 EN là -1 đến +1)
- `dimC_pipeline.py` tự động normalize sang [-1, +1]:
  - Công thức: `new = (old - 0.5) × 2`

---

## Tokenizer cần thiết

Cài thêm nếu muốn tokenization chính xác (không bắt buộc — có fallback):

```powershell
pip install jieba          # ZH (tiếng Trung) — khuyến nghị
pip install fugashi[unidic-lite]  # JA (tiếng Nhật) — khuyến nghị
# pip install konlpy       # KO (tiếng Hàn, optional)
```

Nếu không cài:
- ZH → character-level fallback (mỗi ký tự Hán = 1 token)
- JA → character-level fallback (Kanji/Kana)

---

## Files đã có

- [ ] `Chinese-Simplified-NRC-VAD-Lexicon.txt`  ← **cần cho ZH datasets**
- [ ] `Japanese-NRC-VAD-Lexicon.txt`            ← **cần cho KokoroChat**
- [ ] `Korean-NRC-VAD-Lexicon.txt`              ← tùy chọn (KMI)
