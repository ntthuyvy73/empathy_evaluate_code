# Đánh giá phản biện & Định hướng Q1
## Dành cho: Paper về đánh giá 6 dataset tư vấn tâm lý (mind-eval)

> **Mục đích file này**: Ghi lại toàn bộ phân tích phản biện, điểm mạnh/yếu, khoảng trống nghiên cứu,
> tính khả thi và các quyết định chiến lược — để tham chiếu khi tiếp tục ở conversation khác.
>
> **Đọc kèm**: `PLAN-standardization-and-ranking.md` (kế hoạch thực thi chi tiết).
>
> **Ngày phân tích**: 09/06/2026

---

## A. CONTEXT — Tóm tắt bức tranh tổng thể

### Hệ thống đánh giá đang xây dựng

- **6 dataset** counseling/mental-health: Psy-Insight (EN/human), cactus (EN/simulated), simpsydial (ZH/simulated), PsyDial (ZH/simulated), SoulChat (ZH/single-turn), KMI (KO/human).
- **3 dimension đánh giá**:
  - Dim-A: MindEval (5 metric, thang 1–6) — Clinical Accuracy, Ethical Conduct, Assessment & Response, Therapeutic Relationship, AI-Specific Communication.
  - Dim-B: WAI-O-S (3 metric, thang 1–5) — Goal, Approach, Affective Bond.
  - Dim-C: Emotional Dynamic Trajectory (BEL, ETV, ECP) — **chưa implement, gác lại**.
- **3 setting ngôn ngữ (S1/S2/S3)** để phân tích ảnh hưởng ngôn ngữ trước khi chọn trục ranking.
- **Mục tiêu**: xếp hạng thế mạnh từng dataset, định hướng chọn dataset để train/eval.

### Cấu trúc kỹ thuật đã có

- Pipeline: `evaluate.py` → `generate_judgments.py` (Dim-A) / `generate_wai_judgments.py` (Dim-B).
- Format judge: `member_profile` + `interaction [{role, content}]` → `messages_to_convo_str` (chỉ nhận `role=="user"` làm client).
- Config: `config.json` có `translation`, `judge`, `profile_extraction`, `google_translate`.
- 3/6 dataset đã có `option_*` (simpsydial, KMI); 3 dataset còn thiếu converter (cactus, PsyDial, Psy-Insight).

---

## B. VẤN ĐỀ KHUNG BÀI — ⚠️ QUYẾT ĐỊNH CHƯA CHỐT

### ⚡ Highlight: Cần chốt sau khi có kết quả phân tích

Bạn gọi đây là "paper survey" nhưng nội dung thực chất là **empirical benchmark/dataset audit**. Đây là phân kỳ quan trọng cho Q1:

| Framing | Điểm mạnh | Rủi ro |
|---|---|---|
| **Survey thuần** | Quen thuộc với tạp chí | Đông đúc; "thiếu tính mới" dễ bị reject Q1 |
| **Benchmark/audit** | Contribution rõ ràng; timely | Reviewer đòi validation (human/multi-judge) |
| **Hybrid: survey + benchmark** | Cân bằng định vị + đóng góp | Phức tạp hơn để viết mạch lạc |

**Tín hiệu để chốt sau khi có kết quả**:
- Nếu ra **phát hiện khái quát** (vd synthetic kém human rõ rệt trên lâm sàng, ranking ổn định qua ngôn ngữ/judge) → **đẩy benchmark/audit**, nhấn đây là lần đầu có framework đo dataset counseling.
- Nếu phát hiện mỏng/không nhất quán → **lùi về hybrid** để giảm áp lực tính mới.
- **Tránh survey thuần** trừ khi phần tổng hợp literature thực sự đồ sộ và có taxonomy mới.

**Framing được khuyến nghị (nếu phải chọn sớm)**:
> *"A multi-dimensional, psychometrically-grounded benchmark for auditing mental-health dialogue datasets, with a cross-lingual LLM-judge reliability study."*

---

## C. TÍNH MỚI & KHOẢNG TRỐNG NGHIÊN CỨU

### Đủ mạnh để là đóng góp — giữ và nhấn mạnh

1. **Đơn vị đánh giá là DATASET, không phải model.**
   - Hầu hết công trình hiện tại đánh giá hệ thống/agent; "kiểm toán chất lượng dataset" cho counseling là niche thưa người.
   - Khoảng trống rõ: cộng đồng đang sinh ồ ạt dataset LLM-synthetic cho mental health mà **chưa có khung chuẩn để so chất lượng/đặc tính** → hướng dẫn chọn dataset để train/eval năng lực cụ thể.

2. **Tổ hợp 3 góc nhìn có cơ sở tâm lý học được thiết lập.**
   - Lâm sàng (MindEval) + liên minh trị liệu (WAI-O-S, từ instrument psychometric thật của Bordin 1979/Munder 2010) + động học cảm xúc (Dim-C).
   - Việc *kết hợp* 3 trục thành một profile dataset là đóng góp framework mới.

3. **Phân tích human-vs-synthetic provenance — rất timely (2025–2026).**
   - Câu hỏi "dataset LLM-mô phỏng khác transcript người thật thế nào trên 3 trục lâm sàng" là phát hiện có giá trị tức thì cho cộng đồng.
   - Nếu kết quả thể hiện rõ gap → thuyết phục mạnh, dễ được cite.

4. **Nghiên cứu độ tin cậy LLM-judge xuyên ngôn ngữ.**
   - Phân rã judge-language effect (S3 vs S2) vs. translation effect (S1 vs S3) là contribution methodological độc lập, đủ mạnh.
   - Hiện chưa có công trình nào làm bài bản cho *counseling dialogue* domain xuyên 3 ngôn ngữ (EN/ZH/KO).

### Điểm yếu / dễ bị đánh — phải xử lý trong bài

1. **"Leaderboard 6 dataset" tự thân không phải đóng góp khoa học.**
   - Reviewer sẽ hỏi: ta *học* được điều gì khái quát, có thể áp dụng ra ngoài 6 dataset này?
   - Xử lý: đặt **research questions/hypotheses tường minh** (xem mục E.3), không chỉ ra bảng.

2. **Một LLM-judge duy nhất, không có human validation.**
   - Đây là **lý do reject phổ biến nhất** cho loại bài benchmark bằng LLM-as-judge.
   - Xử lý: multi-judge (mục D.2) + mục Limitations trung thực.

---

## D. NHỮNG THỨ PLAN ĐANG THIẾU — BẮT BUỘC CHO Q1

### D.1 ⚠️ Validation của judge (meta-evaluation) — QUAN TRỌNG NHẤT

**Quyết định của bạn**: Multi-judge model (không có nguồn lực annotate người).

**Cách triển khai**:
- Dùng **2–3 judge đa dạng nhà cung cấp**: vd GPT-5.1 (đã có) + Claude Sonnet/Opus + Gemini.
- Chạy trên **subset đại diện** (~80–100 hội thoại, trải đều 6 dataset) → không cần chạy full 200×6.
- Báo cáo **Krippendorff's α** hoặc **Spearman/Kendall** giữa các judge cho mỗi metric.
- Nếu ranking ổn định qua các judge → kết luận mạnh: "ranking không phụ thuộc vào danh tính judge model".
- **Gọi đúng tên trong bài**: "inter-judge reliability" (không phải validity tuyệt đối — vì không có ground truth người).
- Đưa "thiếu human validation" vào **Limitations / Future Work** một cách tường minh.

**Gợi ý rẻ thêm (không bắt buộc)**:
- Author spot-check ~20–30 mẫu làm sanity check thủ công → đủ để nói "đã kiểm tra tay", tăng độ tin cậy mà gần như không tốn nguồn lực.

### D.2 Research Questions tường minh (chưa có trong plan)

Phải đặt trước khi thiết kế phân tích. Đề xuất:

- **RQ1** (Profile thế mạnh): Dataset nào mạnh ở trục nào, và có mẫu hình nào nhất quán theo nguồn gốc (human/synthetic/single-turn)?
- **RQ2** (Provenance): Dataset LLM-simulated có kém dataset human trên trục lâm sàng (Dim-A) và liên minh trị liệu (Dim-B) không, và mức độ như thế nào?
- **RQ3** (Ngôn ngữ/Judge): LLM-judge có cho điểm nhất quán xuyên ngôn ngữ (S1/S2/S3) không? Ảnh hưởng của bản dịch và ngôn ngữ judge lớn đến đâu?
- **RQ4** (Dim-C, tùy chọn): Các dataset có khác biệt về dynamic cảm xúc theo phiên (BEL/ETV/ECP)?

### D.3 Thống kê đúng chuẩn

- **Bootstrap CI** cho mỗi metric/dataset.
- **Significance test** khi so dataset (đã có `significance_testing.py` trong repo — tận dụng).
- **Effect size** (Cohen's d hoặc tương đương) cho mỗi so sánh pair.
- **Hiệu chỉnh đa so sánh** (Bonferroni hoặc BH/FDR) — bắt buộc khi so nhiều dataset × nhiều metric.

### D.4 Reproducibility (Q1 đòi hỏi)

- Pin **model version + ngày chạy** cho judge và translator (cảnh báo: `gpt-5.1` sẽ drift theo thời gian, gây non-reproducibility nếu không ghi).
- Ghi rõ **random seed, prompt version** (đã có `v0_1`).
- Lưu **raw outputs** (unparsed_judgment, thinking_trace) → cho phép reparse nếu cần.
- Code release trên GitHub (hoặc tối thiểu README reproducibility rõ ràng).

### D.5 Định nghĩa Dim-C (BEL/ETV/ECP)

- Cần **định nghĩa chính thức + trích dẫn paper** (paper "Detecting Emotional Dynamic Trajectories").
- Cần rõ: thang điểm, cách tính từng metric, cách trích cảm xúc từ hội thoại (dùng `emotional_label` trong `extra`?).
- Schema canonical đã chừa `extra.emotional_label` — không cần convert lại khi cắm Dim-C.

---

## E. TÍNH KHẢ THI — PHÂN TÍCH CHI PHÍ THỰC TẾ

### E.1 Điểm nghẽn chi phí

| Hạng mục | Lý do tốn | Ước lượng đơn giản |
|---|---|---|
| **Dim-B (WAI)** | 12 câu × n_runs=3 = **36 call/hội thoại** | 6×200×3 setting ≈ ~100k+ call |
| **Dịch per-turn (S1)** | Dịch **từng turn một** (hàm hiện tại) | PsyDial: 142 turn/hội → hàng chục nghìn call |
| Dim-A (MindEval) | 1 call/hội thoại | 6×200×3 setting ≈ 3,600 call — không lo |
| Profile extraction | Đã bỏ (dùng Unknown) | Tiết kiệm hẳn một stage |

### E.2 Tối ưu bắt buộc trước khi chạy diện rộng

1. **Dịch theo-hội-thoại (không phải per-turn)**: gửi cả dialogue trong 1 call với định dạng giữ role → giảm chi phí dịch **10–100× tùy dataset**.
2. **WAI subsample**: chỉ cần ~80–100/200 hội thoại cho WAI, đủ để phân tích thống kê.
3. **WAI n_runs**: giảm 3→2 trong giai đoạn khám phá.
4. **S2 thu hẹp**: chỉ chạy 4 dataset non-EN, chỉ subset cần cho phân tích ngôn ngữ.

### E.3 Kết luận khả thi

Khả thi, nhưng **nếu không tối ưu dịch và WAI trước** thì token cost sẽ phình 10–50× và có thể không hoàn thành trong budget.

---

## F. CÁC BƯỚC DƯ / NÊN CẮT HOẶC TỐI ƯU

| Bước | Đánh giá | Hành động |
|---|---|---|
| S2 chạy full 6 dataset × full 200 | **Dư** — S2 chỉ phục vụ phân tích ngôn ngữ, không vào ranking chéo; EN datasets: S2=S1=S3 | Thu hẹp: chỉ 4 non-EN, subset |
| 3 loại chuẩn hóa (raw+z+mean-rank) báo cáo đồng thời ở mọi nơi | **Hơi thừa khi trình bày** | Giữ đủ 3 loại; **z-score làm chính**, raw ở phụ lục, mean-rank chỉ khi gộp chéo dimension |
| Thí nghiệm đa-translator diện rộng | **Dư nếu pilot không thấy khác biệt** | Pilot nhỏ + gate bằng tác động hạ nguồn: nếu đổi translator không đổi điểm Dim-A trên 5–10 mẫu → dừng, chọn 1 translator |
| Back-translation đầy đủ cho mọi hội thoại | **Nặng không cần thiết** | Thay bằng embedding similarity + chấm tay vài mẫu cho pilot; back-translation chỉ làm xác nhận khi cần |
| Length normalization (cắt/cửa sổ) | **Đã loại** — dùng covariate (theo quyết định của bạn) | Giữ nguyên, đừng quay lại |
| Profile extraction per-dataset | **Đã bỏ đúng** — dùng Unknown đồng nhất | Giữ nguyên |

---

## G. CHECKLIST PHẢN BIỆN CUỐI — CHECK TRƯỚC KHI SUBMIT Q1

### G.1 Về phương pháp

- [ ] **Framing đã chốt** (benchmark/audit vs hybrid vs survey)? ← *Chốt sau khi có kết quả*
- [ ] Research Questions tường minh (RQ1–RQ4) có trong paper không?
- [ ] Multi-judge validation (≥2 model khác nhà cung cấp) đã chạy?
- [ ] Báo cáo **inter-judge reliability** (Krippendorff's α / Spearman) đúng thuật ngữ?
- [ ] "Thiếu human validation" được nêu trong Limitations?
- [ ] Bootstrap CI + significance test + effect size + đa-so-sánh correction?
- [ ] Model version + ngày chạy + seed + prompt version đã pin?

### G.2 Về dữ liệu & kết quả

- [ ] Bẫy role (client→user / therapist→assistant) đã khóa & spot-check?
- [ ] Annotation không lọt vào prompt judge (tách sang `extra`)?
- [ ] Length-bucket + partial correlation đã báo cáo (covariate độ dài)?
- [ ] Kết quả ranking đi kèm caveat provenance (human/synthetic/single-turn)?
- [ ] Phân rã S3 vs S2 (judge-language) và S1 vs S3 (translation effect) rõ ràng?

### G.3 Về Dim-C

- [ ] Định nghĩa BEL/ETV/ECP có paper trích dẫn chính thức?
- [ ] Cách tính từ `emotional_label` đã xác nhận?
- [ ] Nếu chưa implement → nêu rõ trong Future Work hay tách ra (paper riêng)?

### G.4 Về trình bày

- [ ] Framing contribution rõ ràng ngay ở Abstract/Introduction?
- [ ] Related work định vị được "gap" so với survey/benchmark đã có?
- [ ] Bảng kết quả dùng z-score (không phải raw) khi so chéo dimension?
- [ ] Reproducibility: code/data release URL hoặc supplementary?

---

## H. QUYẾT ĐỊNH ĐÃ CHỐT

| # | Vấn đề | Quyết định |
|---|---|---|
| 1 | Framing | **Chưa chốt** — xem kết quả phân tích trước |
| 2 | Judge validation | **Multi-judge model** (không có nguồn lực annotate người) |
| 3 | Dim-C | **Giữ đủ 3 dimension** — cần định nghĩa BEL/ETV/ECP |
| 4 | Trục ranking chéo | **S1 hoặc S3** (judge EN chung) — chọn sau phân tích S1/S2/S3 |
| 5 | S2 ranking chéo | **Không** — S2 chỉ phân tích trong-ngôn-ngữ & tham chiếu bản ngữ |
| 6 | Xử lý độ dài | **Covariate** (không cắt dữ liệu) |
| 7 | Profile | **DEFAULT_PROFILE Unknown** đồng nhất 6 dataset |

---

## I. ĐIỀU CẦN CUNG CẤP TIẾP THEO (để unblock các bước tiếp)

1. **Định nghĩa Dim-C** (BEL/ETV/ECP): trích dẫn paper "Detecting Emotional Dynamic Trajectories", thang điểm, cách tính, cách trích từ hội thoại.
2. **Danh sách judge model cho multi-judge**: ngoài GPT-5.1 muốn thêm Claude / Gemini / model nào?
3. **Danh sách translator muốn thử**: ngoài GPT (đang dùng), muốn thêm Claude / Qwen / Google Translate?
4. **Ngưỡng "S1 ≈ S3"** (vd Spearman ≥ 0.9 và |Δ z-score| < 0.2)?
5. **Dim-B (WAI): giới hạn số hội thoại** khi chạy thử (đề xuất: 80–100/200)?

---

*File này dùng để bắt đầu conversation mới: đọc file này + `PLAN-standardization-and-ranking.md` là đủ context để tiếp tục.*
