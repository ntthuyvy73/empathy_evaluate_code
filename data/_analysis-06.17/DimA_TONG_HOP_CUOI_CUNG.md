# Dim-A — BỨC TRANH TỔNG HỢP & KẾT LUẬN CUỐI CÙNG
### Hợp nhất từ `DimA_FINAL_3judge.md` + `DimA_provenance_matched_pairs.md`
*Panel 3 judge: GPT-5.1 · Claude-Sonnet-4.6 · Gemini-3.1-pro · 11 dataset · S3 · N=20/ô*

> **Định vị bài báo:** survey/audit về **xu hướng xây dựng dataset tham vấn tâm lý multi-turn** gần đây. Đóng góp = đánh giá mọi dataset trên **một chuẩn metric chung** (3 chiều A/B/C, đơn vị = dialogue), rồi rút ra **ưu/khuyết của từng phương thức thu thập** và **khuyến nghị setting S1/S2/S3 cho ngôn ngữ non-EN/low-resource (vd VN)**. Tài liệu này khép lại **Dim-A** và chuẩn bị khớp với Dim-B (WAI) + Dim-C (cảm xúc).

---

## PHẦN I — SÁU GÓC NHÌN (cùng một dữ liệu, sáu lăng kính)

### Góc 1 — Theo DATASET: ba tầng, không phải hạng 1–11
Bootstrap CI chỉ tách được **3 tầng** (xem `F1`):
- **ĐỈNH (~3.1–3.3):** cactus (LLM-CBT), **Psy-Insight (real)**, simpsydial (LLM-rp), **AnnoMI (real)** — *trộn real + synthetic*.
- **GIỮA (~2.5–2.7):** KokoroChat (human-rp), KMI (LLM-MI), PsyDial, CPsyCoun (semi-real).
- **ĐÁY (~1.8–2.3):** SoulChat (LLM-empathy), smile (LLM-exp), ESConv (crowd).

→ **Thông điệp #1:** đỉnh bảng trộn lẫn nguồn dữ liệu → "cách thu thập" **không** quyết định thứ hạng rubric lâm sàng.

### Góc 2 — Theo METRIC: "Safe but Shallow" + rubric thực chất ~1 chiều
- **Eth cao nhất, Assessment & AI-Comm thấp nhất** ở đa số dataset (Eth-cao-nhất: GPT 10/11, Gemini 9/11, Claude 6/11). Cả thế hệ dataset **"an toàn bề mặt nhưng nông"**.
- **5 metric ≈ 1 nhân tố halo** (PC1 74–81% mọi judge; Clin–Asr r≈0.8–0.9). Rubric dư thừa nặng.
- **AI-Comm là metric phân kỳ nhất** giữa judge (α 0.37) và reliability item-level chung thấp (α 0.55).

→ **Thông điệp #2:** điểm tổng hợp Dim-A đo "chất lượng lâm sàng chung", nhưng **chỉ đáng tin ở cấp dataset** (trung bình 20 item), **không** ở cấp từng dialogue; và "Ethics" cao là dấu hiệu cần giải mã (Góc 4), không phải đạo đức tốt.

### Góc 3 — Theo JUDGE: điểm không chuyển giao, thứ hạng thì có
- **Severity lệch lớn:** GPT 2.98 > Claude 2.55 > Gemini 2.45 (và Qwen3 1.79 — đã loại vì outlier nén thang, reliability thấp, lệch cross-lingual).
- **Thứ hạng rất bền:** Kendall W = **0.92**; tương quan profile 0.84–0.94.

→ **Thông điệp #3:** dùng **panel đa-hãng + rank/z-score**, không bao giờ dùng điểm tuyệt đối của một judge. (Bài học trực tiếp cho Dim-B.)

### Góc 4 — Theo PROVENANCE / PHƯƠNG THỨC THU THẬP (trọng tâm bài) — neo bằng matched-pair

**(a) Mean score KHÔNG phân biệt provenance** — khi cố định confound:
- Cố định **ngôn ngữ EN** (cặp ⑤): Psy-Insight (real) 3.23 ≈ cactus (sim) 3.30, **Δ +0.07** — *dưới* nhiễu nội bộ data thật (cặp ⑥ = 0.11).
- Cố định **origin LLM** (cặp ⑦): cactus − KMI = +0.68 — chênh **trong cùng synthetic** lớn gấp ~10× chênh real-vs-sim.
- **Negative control** (cặp ③ PsyDial↔CPsyCoun): Δ = 0.02 → các gap khác không phải nhiễu.
- → **Yếu tố chi phối điểm thật sự: ngôn ngữ > modality/format/purpose ≫ provenance.**

**(b) Provenance hiện rõ ở PHƯƠNG SAI & CHẾ ĐỘ THẤT BẠI** (xem `F7`):
- within-SD: real (0.92–1.33) ≫ human-rp (0.46) > LLM/semi (0.27–0.49). Đúng "ba bậc xác thực".
- Data real chứa **cả đỉnh chuyên gia lẫn lỗi nguy hiểm thật** (AnnoMI `annomi_69`: counselor nói citalopram+phenelzine "should be fine" — lỗi MAOI chết người, cả 3 judge chấm sàn ≤1.3). Synthetic là **"trung bình lý tưởng hoá"**, mất cả hai đuôi.

**(c) "Ethics" là chỉ số TRỘN** (cặp ①②⑦⑧, `F5`):
- Cố định purpose/modality → human rơi sàn đạo đức nhiều hơn LLM **27–35 điểm%** (AnnoMI-MI 35% vs KMI-MI 0%) = **lỗi đạo đức thật của người vs an toàn do RLHF**.
- Cố định origin → narrow-purpose rơi sàn nhiều hơn full-protocol **52 điểm%** (SoulChat empathy 57% vs simpsydial roleplay 5%, đều LLM) = **độ đầy đủ lâm sàng**.
- → Không yếu tố nào ánh xạ "therapy tốt/xấu".

→ **Thông điệp #4 (mạnh nhất cho bài):** rubric lâm sàng **không thiên vị synthetic**; khác biệt phương thức thu thập bộc lộ ở **phương sai/đuôi phân phối** và ở **chế độ thất bại**, chứ không ở điểm trung bình.

### Góc 5 — Theo NGÔN NGỮ / SETTING (cho khuyến nghị low-resource)
- **Thứ hạng bền qua dịch:** Spearman(S1,S3) = 0.75 trên 7 ds non-EN.
- **Reading-language:** GPT & Claude ổn định (S2≈S3); **chất lượng bản dịch quan trọng** — bản `utterance_en` ship-kèm của KMI làm mất ~0.37đ (mất kính ngữ Hàn), dịch lại bằng LLM thì phục hồi.
- **KO & JA (nhiều kính ngữ) chịu thiệt cross-lingual nhiều nhất; ZH bền.**

→ **Thông điệp #5:** ngôn ngữ giàu kính ngữ/đại từ thân tộc (KO, JA, **và VN**) dễ mất nghĩa khi đánh giá cross-lingual → cần chọn setting cẩn thận (Phần IV).

### Góc 6 — Theo VALIDITY: Dim-A đo được & KHÔNG đo được gì
| Dim-A ĐO được | Dim-A KHÔNG đo được (→ cần B/C) |
|---|---|
| Chất lượng lâm sàng bề mặt (cấp dataset) | Liên minh trị liệu thực chất (→ **Dim-B/WAI**) |
| Độ đầy đủ/cấu trúc của can thiệp | Tính xác thực **cảm xúc** (→ **Dim-C**) |
| Sự hiện diện lỗi đạo đức (qua floor) | Quỹ đạo cảm xúc client theo lượt (→ **Dim-C**) |
| Phương sai/đuôi phân phối (dấu provenance) | Liệu warmth/power của counselor có tự nhiên (→ **Dim-C**) |

→ **Thông điệp #6:** Dim-A là lớp "sàng lọc lâm sàng bề mặt"; nó **mù** với chiều quan hệ và cảm xúc — đúng chỗ Dim-B và Dim-C bổ khuyết.

---

## PHẦN II — KẾT LUẬN CUỐI CÙNG CHO Dim-A (7 chốt)

1. **Thứ hạng dataset ổn định nhưng điểm tuyệt đối không chuyển giao** (Kendall W=0.92; severity span 0.5–1.2đ). ⇒ chuẩn báo cáo = panel đa-hãng + rank/z-score.
2. **Cả thế hệ dataset "an toàn nhưng nông"** (Ethical mạnh; Assessment & AI-Comm yếu) — đặc trưng chung, không phụ thuộc nguồn.
3. **Rubric 5-chiều thực chất ~1 nhân tố** (PC1 74–81%) ⇒ Dim-A một mình **không đủ đa chiều**; phải kết hợp B/C và chứng minh không trùng (factor analysis A+B+C, N=200).
4. **Rubric lâm sàng KHÔNG thiên vị dữ liệu synthetic**: khi cố định ngôn ngữ, real ≈ best-synthetic (Δ≤0.07 < nhiễu 0.11). "Synthetic thắng" trong bảng thô là **artifact ngôn ngữ + purpose**.
5. **Dấu hiệu provenance đáng tin = PHƯƠNG SAI & FAILURE-MODE**, không phải mean: real phân tán gấp 3–4×, chứa cả đỉnh chuyên gia lẫn lỗi nguy hiểm thật; synthetic lý tưởng-hoá, mất hai đuôi.
6. **"Ethics" là construct trộn** (RLHF-safety + độ đầy đủ lâm sàng), không đo đạo đức trị liệu ⇒ thận trọng khi diễn giải; nên tách hoặc tái định nghĩa.
7. **AI-Comm là metric kém tin cậy & phân kỳ nhất** (α 0.37) ⇒ cân nhắc bỏ khỏi điểm tổng hợp hoặc gắn decision-rule riêng cho transcript người thật.

### Rào trước (hedge) & cách khắc phục bằng HUMAN-ANCHOR THEO TỪNG CHIỀU

**Giới hạn:** mọi điểm Dim-A do LLM chấm — **không có chuyên gia người chấm để đối chiếu** — nên các kết luận là về *cách đo lường* và *so sánh tương đối*, chưa phải sự thật lâm sàng. Thêm nữa, mọi so sánh "real vs synthetic" dựa trên **chỉ 2 dataset real** → cỡ mẫu rất nhỏ.

**Cách vá — phân biệt "dữ liệu real" với "anchor được":** một dataset làm anchor cần (a) có **nhãn chất lượng/kết quả do người gán** (không chỉ là văn do người viết) **và** (b) nhãn đó **khớp đúng chiều** cần kiểm. "Real" (cách dữ liệu được tạo) ≠ "anchor được". Vì mỗi dataset có loại nhãn người khác nhau, anchor phải gán **theo từng chiều**:

| Dataset | Nhãn người có sẵn | Anchor cho chiều |
|---|---|---|
| **AnnoMI** | Chuyên gia gán **chất lượng MI: high vs low** | **Dim-A** — kiểm rubric có chấm "high" > "low" không |
| **ESConv** | Seeker **tự báo cảm xúc trước/sau** + strategy + feedback | **Dim-C** — kiểm quỹ đạo cảm xúc; *với Dim-A là counter-anchor* (người thấy hỗ trợ tốt nhưng Dim-A xếp đáy → bằng chứng Dim-A mù purpose) |
| **Psy-Insight** | *Chưa xác minh có nhãn chất lượng dùng được không* | **Cần kiểm** — nếu có nhãn chuyên gia thì bổ sung anchor Dim-A (nâng "real n=2") |

→ **ESConv là dữ liệu real và là anchor hợp lệ — nhưng nhãn của nó là CẢM XÚC nên thuộc Dim-C, không phải Dim-A.** Không phải bị loại, mà được gán đúng chỗ. Dùng nhãn cảm xúc của ESConv để kiểm rubric lâm sàng Dim-A sẽ là **lệch khái niệm** (đúng cái purpose-mismatch khiến Dim-A xếp ESConv đáy, floor 88%).

---

## PHẦN III — ƯU/KHUYẾT TỪNG PHƯƠNG THỨC THU THẬP (góc nhìn Dim-A; chờ B/C bổ sung)

| Phương thức | Ví dụ | Ưu (bằng chứng Dim-A) | Khuyết (bằng chứng Dim-A) | Dùng tốt cho mục đích nào |
|---|---|---|---|---|
| **LLM-simulated, full-protocol** | cactus (CBT), simpsydial | Điểm cao & **đồng nhất**; **0% lỗi đạo đức** (RLHF-safe); rẻ, scale; sinh thẳng ngôn ngữ đích (không lỗi dịch) | **Mất đuôi phân phối**: không ca xuất sắc vượt trội, **không ca lỗi nguy hiểm** → kém cho học nhận diện rủi ro; phương sai thấp = ít đa dạng tình huống | Huấn luyện **kỹ năng lâm sàng có cấu trúc**; bootstrap nhanh dataset ngôn ngữ mới; baseline "an toàn" |
| **LLM-generated, narrow-purpose** | SoulChat (empathy), smile (expanded) | Rẻ nhất; tập trung một kỹ năng (đồng cảm) | Điểm **đáy**; rơi sàn đạo đức cao do **thiếu can thiệp đầy đủ**; hẹp | Dữ liệu **bổ trợ một kỹ năng**; KHÔNG dùng làm exemplar lâm sàng đầy đủ |
| **Real clinical transcript** | AnnoMI (MI), Psy-Insight | **Giàu tín hiệu nhất** (phương sai cao); chứa **cả đỉnh chuyên gia lẫn lỗi thật** (vô giá cho safety/error-detection); xác thực | Đắt, khan hiếm (N nhỏ); chứa **lỗi đạo đức thật** (cần lọc tuỳ mục đích); lộn xộn/disfluent | **Benchmark/đánh giá** (có đủ phổ); huấn luyện **nhận diện thực hành tốt VÀ nguy hiểm**; làm **mỏ neo** cho mọi so sánh |
| **Human role-play** (counselor đóng vai) | KokoroChat | Tương tác người thật; phương sai > LLM | Điểm thấp hơn (lẫn imperfection thật + thiệt dịch JA); vẫn rơi sàn đạo đức 32% | Dữ liệu **đào tạo/huấn luyện** có động lực tương tác thật; thay thế khi thiếu transcript thật |
| **Crowdsourced** (người thường) | ESConv | Scale người thật; bắt **register hỗ trợ cảm xúc** | **Đáy** rubric lâm sàng (88% floor) — nhưng do **lệch mục đích** (support ≠ clinical), KHÔNG phải data tệ | Tác vụ **emotional-support / peer-support**; **đừng** đánh giá bằng rubric lâm sàng |
| **Semi-real** (LLM mở rộng từ seed thật) | PsyDial, CPsyCoun | Trung gian; tận dụng seed thật; nội bộ nhất quán | Giữa bảng, không xuất sắc; pipeline là thứ yếu | **Cân bằng** scale–xác thực khi không đủ data thật |

> **Khuyến nghị xây dựng (chỉ từ Dim-A — sẽ tinh chỉnh sau B/C):**
> - Cần **scale + an toàn + nhất quán** → LLM-simulated full-protocol.
> - Cần **dạy model nhận diện rủi ro/lỗi** → **bắt buộc có real clinical** (chỉ nơi đó có lỗi nguy hiểm).
> - Cần **benchmark/đánh giá** → real (đủ phổ) làm chuẩn.
> - Cần **emotional-support** → crowd, nhưng đổi bộ metric (không dùng rubric lâm sàng).
> - **Cảnh báo treo cho B/C:** Dim-A không thấy *tính xác thực cảm xúc*. Dự kiến Dim-C sẽ lộ **khuyết của LLM-sim** (counselor ấm/áp đảo bất thường) — tức một CON quan trọng **chưa** thể hiện ở Dim-A. Vì vậy "LLM-sim điểm cao" **không** được đọc là "nên dùng LLM-sim" cho đến khi có Dim-C.

---

## PHẦN IV — KHUYẾN NGHỊ SETTING S1/S2/S3 CHO NON-EN / LOW-RESOURCE (vd VN)

**Nhắc lại định nghĩa:** S1 = dịch dialogue sang EN + judge EN · S2 = dialogue bản ngữ + judge bản ngữ · S3 = dialogue bản ngữ + judge EN.

**Bằng chứng Dim-A liên quan:**
- Thứ hạng bền qua dịch (S1↔S3 ρ=0.75) → kết luận **so sánh tương đối** ít nhạy setting.
- **Chất lượng bản dịch là rủi ro lớn nhất** (KMI: bản ship-kèm −0.37đ; LLM dịch lại thì phục hồi).
- **KO & JA (kính ngữ) mất nghĩa nhiều nhất cross-lingual.** VN cũng giàu kính ngữ + đại từ thân tộc (anh/chị/em/con/cháu…) → **cùng nhóm rủi ro KO/JA**.

**Khuyến nghị cho VN (và low-resource giàu kính ngữ), theo thứ tự ưu tiên:**

1. **Ưu tiên S2** *nếu* có **judge bản ngữ đáng tin** (đã kiểm tính ổn định): đánh giá trực tiếp bằng tiếng Việt giữ trọn kính ngữ/sắc thái quan hệ — chính chỗ rubric quan tâm (alliance, lễ độ). **Điều kiện:** phải **validate judge** trước (bài học Qwen3: có judge nén thang & lệch cross-lingual tới +1.08; đừng tin mặc định).
2. **Nếu chưa có judge VN tin cậy → S3** (giữ dialogue VN, judge EN): ổn định hơn S2-với-judge-kém, nhưng **chấp nhận mất sắc thái kính ngữ** → chỉ dùng **rank/ratio**, không so điểm tuyệt đối cross-lingual.
3. **Hạn chế S1, và nếu dùng thì PHẢI dịch lại bằng LLM mạnh** (đừng dùng bản dịch ship-kèm/MT rẻ — sẽ thâm hụt điểm như KMI). S1 chỉ nên làm **cross-check**, không làm trục chính.
4. **Luôn dùng panel ≥2 hãng**, không single-judge; cho **so sánh tuyệt đối cross-lingual, ưu tiên metric judge-free (kiểu Dim-C)** hơn LLM-judge — nhưng ngay cả Dim-C với VN/KO/JA cũng chỉ dùng **ratio/gap**, không valence tuyệt đối.

> **Một câu cho bài:** *Với ngôn ngữ giàu kính ngữ và ít tài nguyên như tiếng Việt, ưu tiên đánh giá bản ngữ (S2) với một LLM-judge đã được kiểm định tính ổn định; nếu không sẵn, dùng S3 và chỉ diễn giải theo thứ hạng/tỉ lệ. Tránh phụ thuộc bản dịch sẵn có vì chất lượng dịch tác động tới điểm lớn hơn cả phương thức thu thập.*

---

## PHẦN V — KHỚP Dim-A VỚI Dim-B & Dim-C (bản đồ tích hợp)

| | **Dim-A (MindEval)** | **Dim-B (WAI)** | **Dim-C (cảm xúc, lexicon)** |
|---|---|---|---|
| Đo gì | Chất lượng lâm sàng bề mặt | Liên minh trị liệu (Goal/Approach/Bond) | Quỹ đạo & cân bằng cảm xúc (VAD) |
| Đơn vị | dialogue | dialogue | dialogue (theo lượt) |
| Phụ thuộc judge | Có (panel 3 hãng) | Có (panel 3 hãng) | **Không** (judge-free) |
| Vai trò provenance | mean *mù*, **variance** thấy | (chờ kiểm: WAI có tăng về synthetic?) | **Trục provenance chính** (warmth/power gap) |
| Rủi ro chính | ~1 nhân tố (redundant) | **Trùng "Alliance" của A?** | portability lexicon (KO/JA/VN) |
| Điều A bàn giao | "an toàn-nông", variance-marker, Ethics-là-trộn, AI-Comm-bỏ | phải chứng minh **bổ sung** ngoài Alliance của A | gánh **tính xác thực cảm xúc** mà A mù |

**Ba việc khớp nối bắt buộc trước khi viết phần "đa chiều":**
1. **Factor analysis A+B+C trên cùng N=200 interaction_id** → chứng minh 3 chiều không trùng (Dim-C đã ~độc lập r≈0; Dim-B phải tự chứng minh ≠ Alliance của A).
2. **Human-anchor THEO TỪNG CHIỀU** (không gom một chỗ): **Dim-A ← AnnoMI** (nhãn high/low MI của chuyên gia) để khoá nhân-quả cho rubric lâm sàng; **Dim-C ← ESConv** (self-report cảm xúc) để validate quỹ đạo cảm xúc; **kiểm Psy-Insight** xem có nhãn chất lượng không, nếu có thì bổ sung anchor Dim-A. Dim-B chưa có anchor trực tiếp → mượn AnnoMI high/low (giả định alliance tương quan chất lượng MI) như kiểm tra gián tiếp.
3. **Tổng hợp provenance 3 chiều:** Dim-A nói "mean mù, variance thấy"; Dim-C nói "cảm xúc lộ provenance"; ghép lại thành kết luận hoàn chỉnh **"phương thức nào cho mục đích nào"** — đây là đóng góp chính của bài.

> **Câu khung tổng cho bài (sau khi có đủ A+B+C):** *Trên một chuẩn metric chung 3 chiều, các dataset tham vấn multi-turn gần đây "an toàn nhưng nông" về lâm sàng (A), và phương thức thu thập để dấu không ở điểm trung bình mà ở phương sai (A), ở liên minh trị liệu (B), và rõ nhất ở tính xác thực cảm xúc (C). Synthetic tối ưu sự nhất quán & an toàn nhưng đánh mất đuôi phân phối và sắc thái cảm xúc của thực hành thật; data thật là chuẩn vàng cho benchmark & an toàn nhưng khan hiếm. Với ngôn ngữ ít tài nguyên giàu kính ngữ, đánh giá bản ngữ (S2) với judge đã kiểm định là lựa chọn ít mất mát nhất.*

---
### Hình tổng hợp
- **`F7_master_map.png`** — bản đồ điểm × phương sai × provenance (một hình tóm tắt cả Dim-A).
- `F1` ranking tầng · `F2` severity & provenance · `F3` safe-but-shallow · `F4` dimensionality · `F5` ethics-floor matched · `F6` matched-pair per-metric.
- File nguồn: `DimA_FINAL_3judge.md`, `DimA_provenance_matched_pairs.md`; số liệu nền T1–T8; quá trình & số Qwen3: `_ARCHIVE_incremental_v1.md`.
