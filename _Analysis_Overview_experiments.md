> **[CẬP NHẬT — kiểm chứng thực nghiệm]** Mỗi finding F1–F12 dưới đây đã được gắn **note kiểm chứng dựa trên kết quả đánh giá** (Dim-A 11 dataset · Dim-B WAI · Dim-C). Ký hiệu: ✅ vững / 🟡 cần điều chỉnh / 🔴 không tái lập. (*) = finding quan trọng nhất (F4, F7, F9, F12). Mục **§Kết quả đánh giá tổng quan theo phổ provenance** (chỉ multi-turn) được bổ sung ở cuối.

---
1. Insight bạn chưa khai thác
Mấy điểm trong báo cáo phân tích thực ra có giá trị paper cao hơn cả phần ranking:

F12 (*) — "An toàn bề mặt, nông về can thiệp": Ethics cao nhất ở mọi dataset, mọi judge, trong khi Assessment/AIComm thấp nhất. Đây là claim tổng quát về toàn bộ thế hệ dataset hiện tại — đáng làm finding chủ đạo, mạnh hơn việc xếp hạng.
  > ✅ **Kiểm chứng — VỮNG cho GPT, một phần cho Claude:** GPT: Ethics cao nhất **10/11**, thấp nhất ∈{Assessment,AIComm} **11/11** → rất vững. Claude: Ethics cao nhất chỉ **4/6**. → cụm 'mọi judge' hơi quá; **lõi (Ethics kịch trần, Assessment đáy) đứng vững**. Headline 'Safe but Shallow' giữ nguyên.
F8 — 5 metric thực chất ~2 chiều (Clinical↔Assess r=0.92). Hệ quả nghiêm trọng hơn bạn nghĩ: khi chạy Dim B, rất có thể WAI trùng với metric Alliance của Dim A → 3 dimension A/B/C của bạn có thể không độc lập như slide tuyên bố. Nếu kiểm tra và thấy đúng, bản thân điều đó là một finding (framework đánh giá đa chiều hiện hành bị redundant); nếu sai, bạn có bằng chứng justify framework. Đằng nào cũng thắng — nên chạy factor analysis ở N=200.
  > 🟡 **Kiểm chứng — một nửa đúng, nhưng headline MẠNH hơn:** Clinical↔Assess r=0.88 (GPT)/**0.94 (Claude)** ✓ — số 0.92 chính là giá trị Claude. **Alliance↔AIComm chỉ r=0.70–0.72, KHÔNG phải 0.85.** Bằng chứng mạnh nhất: **PCA → PC1 giải thích 79% phương sai** ⇒ cả 5 metric ≈ **1 nhân tố trội** (mạnh hơn '2 chiều'). Dim-B(WAI)↔metric Alliance: item-level r=0.60 (trùng *một phần*). **Dim-C thì ĐỘC LẬP** (item r≈0) → chiều thứ 3 KHÔNG dư thừa.
F9 — hai judge chấm hai khái niệm khác nhau dưới cùng tên AIComm (ρ=0.29). Đây là đóng góp phương pháp luận độc lập về LLM-as-judge: rubric thiếu decision rule cho human transcript khiến construct phân kỳ. Case psyinsight_000856 (GPT chấm 2.5 "mechanical", Claude chấm 5.0 "remarkably natural" cho cùng đoạn) là ví dụ minh họa rất "ăn tiền" trong paper.
  > ✅ **Kiểm chứng — VỮNG:** within-dataset r(GPT,Claude) trên AIComm = **0.33** (≈0.29; pooled 0.55) — **thấp nhất mọi chiều** (các chiều khác 0.53–0.63); cactus thậm chí **−0.06**. Case `psyinsight_000856` **tái lập CHÍNH XÁC**: cùng đoạn 'So, um/Hmm' → GPT 2.5 'mechanical', Claude 5.0 'exceptionally natural'.
F4/F5 — translation artifact hai chiều dẫn đến guideline thực tiễn chưa ai phát biểu rõ: đừng bao giờ ship bản dịch EN "làm sẵn" kèm dataset bản ngữ (bài học utterance_en của KMI làm mất 0.27 điểm oan, tập trung ở Ethics vì mất kính ngữ tiếng Hàn). Việc judge "đọc được" tín hiệu văn hóa như kính ngữ cũng mở ra luận điểm culture-aware evaluation — liên quan trực tiếp đến định hướng VN.
  > ✅ **Kiểm chứng — VỮNG (tái lập 3 chữ số):** S1-utt Overall 2.672 vs GPT dịch lại 3.038 vs bản ngữ S2 2.948 → mất **+0.365**. 🔧 *Đính chính:* mất điểm **KHÔNG tập trung ở Ethics** mà gần đều, **lớn nhất ở Assessment (+0.413) và Alliance (+0.412)**. Guideline "đừng ship bản dịch làm sẵn" đứng vững.
Strength profile khớp với theory grounding: KMI (MI) mạnh duy nhất Ethics nhưng yếu Alliance; cactus (CBT, full session) mạnh đều; SoulChat (emotional support) bị phạt Clinical. Tức chữ ký metric phản ánh lý thuyết xây dựng dataset — một giả thuyết kiểm chứng được và rất hợp với mục tiêu "phương thức nào cho mục đích nào". Nó cũng gợi ý framework của bạn nên conditional không chỉ theo cấu trúc (single/multi-turn) mà theo cả intent của dataset.
F10 — provenance confound: hai dataset LLM-simulated chiếm top-2 dưới cả hai judge khác gia đình. Bạn không thể tách "LLM judge thích văn LLM" khỏi chất lượng thật bằng thiết kế hiện tại — đây là lý do thứ hai (sau yêu cầu Q1) bắt buộc phải có lớp human expert đánh giá trên mẫu nhỏ.
  > ✅ **Kiểm chứng — VỮNG:** cactus #1, simpsydial #2 dưới **CẢ GPT lẫn Claude** (Dim-A *và* WAI). Tier-level: Dim-A của LLM-sim (3.13) = Real (3.12) → **rubric KHÔNG phân biệt được provenance** (xem §Provenance). Củng cố bởi gradient happy-ending. → **bắt buộc human anchor.**


=====
2. Đây là dạng bài gì, nên đặt tên thế nào?
Bạn nói đúng — đây không phải survey. Survey là tổng hợp tài liệu; bài của bạn chạy thực nghiệm thống nhất trên các dataset, tức là một empirical/comparative evaluation study — giới NLP hay gọi là benchmark study hoặc dataset audit. Genre gần nhất: "systematic audit of resources under a unified evaluation framework".
Gợi ý cách đặt tên (cấu trúc, bạn chỉnh chữ):

"Auditing Empathy: A Unified Multi-Dimensional Evaluation of Mental Health Counseling Dialogue Datasets"
"Beyond Cataloguing: An Empirical Audit of Counseling Dialogue Datasets with LLM-based Multi-Dimensional Evaluation"
Nếu muốn nhấn phát hiện chính: "Safe but Shallow: ..." (từ F12) làm đầu đề rất bắt.
Từ khóa nên có trong title/abstract: unified evaluation, audit, multi-dimensional, counseling dialogue datasets. Tránh chữ "survey" hoàn toàn, vì nó vừa sai genre vừa kéo kỳ vọng reviewer về độ phủ (survey thì 10 datasets là quá ít; audit thì 10–12 là hợp lý).

=====================
# Bảng tổng hợp Datasets — Audit đa chiều Empathy Datasets trong Mental Health

> Sắp xếp theo **phổ provenance 4 bậc** (Real → Semi-real → Human role-play → LLM role-play/generated)

---

## Bảng 1 — Multi-turn Datasets (đánh giá trên Dim A · Dim B · Dim C)

| # | Bậc Provenance | Dataset | Năm | Ngôn ngữ | Quy mô | Lý thuyết nền | Availability | Nội dung chính của bài báo | Vai trò trong thiết kế audit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **1 · Real counseling** | **AnnoMI** ★ | 2022 (ext. 2023) | EN | 133 dlg · ~9,700 utterances | Motivational Interviewing (MI) | Public (GitHub, Public Domain) | Dataset transcript MI thật đầu tiên được công bố công khai. Nguồn từ video demo MI chuyên nghiệp, được chuyên gia MI annotate ở cấp utterance (behaviour codes: reflection, question, giving info, MI-adherent/non-adherent). Phân tích thuộc tính ở cấp utterance, dialogue, corpus. Có nhãn chất lượng session (high/low). | **Anchor "real" duy nhất public multi-turn.** Cặp matched với KMI: cùng framework MI, khác provenance → so sánh có kiểm soát. Nhãn high/low quality → kiểm chứng external validity của Dim A. |
| 2 | 1 · Real counseling | **Psy-Insight** | 2025 | EN + ZH | 520 EN + 431 ZH sessions | Tham vấn tâm lý thật, nhiều trường phái | Public (GitHub) | Dataset song ngữ (EN/ZH) đầu tiên với annotation giải thích đa tầng cho hội thoại tham vấn tâm lý nhiều lượt. Cấu trúc phân tầng Case → Session → Turn, mỗi tầng có annotation khác nhau (phân tích ca, kế hoạch tham vấn, chiến lược từng turn). Hỗ trợ multitask learning cho LLM. | **Anchor real thứ hai.** Song ngữ nên dùng được luôn cho phân tích S1/S2/S3 mà không đổi nội dung. Annotation giải thích giúp đối chiếu với thinking trace của judge. |
| 3 | **2 · Semi-real** (tái dựng từ dữ liệu thật) | **PsyDial** | 2025 | ZH | ~2,400 dlg · avg 37.8 turns · ~7M tokens | Humanistic + PD + CBT | Public (GitHub) | Dataset tham vấn tâm lý quy mô lớn, xây dựng bằng pipeline RMRR (Retrieve–Mask–Reconstruct–Refine) từ hội thoại counselor-client thật. Bảo vệ quyền riêng tư bằng masking thông tin nhạy cảm rồi dùng LLM tái dựng. Đánh giá bằng human experts xác nhận chất lượng lâm sàng. | Đại diện bậc 2 chính. So với CPsyCoun trong cùng bậc, cùng ZH: hai pipeline tái dựng khác nhau. |
| 4 | 2 · Semi-real | **CPsyCoun** ★ | 2024 | ZH | 3,134 dlg | 9 loại tham vấn · 7 trường phái | Public (GitHub/HF) — CPsyCounR cần ký thỏa thuận | Đề xuất framework tái dựng hội thoại tham vấn từ báo cáo tâm lý (case report). Phase 1: LLM đóng vai "supervisor" trích thông tin + lập kế hoạch. Phase 2: LLM đóng vai "counselor" sinh hội thoại theo kế hoạch. Benchmark đánh giá gồm 4 tiêu chí: toàn diện, chuyên môn, chân thực, an toàn (ACL 2024 Findings). | So sánh pipeline semi-real cùng ngôn ngữ với PsyDial. Phương pháp Memo2Demo minh họa xu hướng xây dataset từ case report. |
| 5 | **3 · Human role-play** (người được huấn luyện) | **KokoroChat** ★ | 2025 | JA | 6,589 dlg · 600K utterances | Tham vấn tâm lý tổng quát | Public (GitHub/HF, CC BY-NC-ND) | Dataset hội thoại tham vấn JA lớn nhất tính đến 06/2025, thu thập bằng role-play giữa 480 counselor được huấn luyện 10 giờ. Counselor dùng keyboard, client dùng LINE — mô phỏng tham vấn online thật. Mỗi dialogue kèm client feedback chi tiết đánh giá chất lượng tham vấn. Fine-tune LLM trên dataset cải thiện cả sinh response lẫn tự động đánh giá (ACL 2025 Main). | **Thay thế EmplifAI.** Đại diện bậc 3 chất lượng cao; so với bậc 4 trả lời "người đóng vai vs LLM đóng vai". Có sẵn client feedback → đối chiếu với Dim B. |
| 6 | 3 · Human role-play (crowdsource) | **ESConv** | 2021 | EN | 1,300 dlg · 31K utterances | Hill's Helping Skills (Exploration–Comforting–Action) | Public (GitHub/HF) | Định nghĩa task Emotional Support Conversation. Thu thập bằng crowdworker (seeker + supporter) được huấn luyện qua tutorial. Mỗi supporter turn annotate 1/8 strategy labels. Seeker tự báo cáo emotion type, intensity trước/sau và feedback 1–5 sao trong quá trình hội thoại. Đánh giá baseline cho thấy strategy-aware model vượt trội (ACL 2021). | **Đưa lại vào đánh giá.** Có self-report cảm xúc trước/sau → anchor validate estimator Dim C. Bậc 3 EN duy nhất. |
| 7 | **4 · LLM role-play** | **CACTUS** | 2024 | EN | 31,577 dlg · ~1M utterances · avg 16.6 turns | CBT (Cognitive Behavioral Therapy) | Public (GitHub) | Dataset multi-turn mô phỏng phiên CBT thật bằng LLM. Client có persona đa dạng + thái độ khác nhau (tích cực/trung tính/tiêu cực). Counselor áp dụng kỹ thuật CBT có kế hoạch. Đề xuất COUNSELINGEVAL framework đánh giá kỹ năng counselor + thay đổi cảm xúc client theo tiêu chí tâm lý học (EMNLP 2024 Findings). | Anchor synthetic hạng 1 hiện tại của pilot. Có CBT plan rõ ràng → kiểm chứng strength profile (F7: metric phản ánh theory grounding). |
| 8 | 4 · LLM role-play | **SimPsyDial** | 2024 | ZH | 1,000 dlg · avg 13 turns | Hill's (2009) + Tích hợp CC/PD/CBT | Public (GitHub) | Hội thoại tham vấn ZH sinh bằng GPT-4 role-play. Tích hợp nhiều trường phái (Client-Centered, Psychodynamic, CBT) qua framework Helping Skills. Mỗi dialogue có nhãn chiến lược và giai đoạn trị liệu. | Đã có pilot S1/S2/S3 đầy đủ. Dùng làm reference khi mở rộng thiết kế ngôn ngữ. |
| 9 | 4 · LLM-generated | **SoulChat** | 2023 | ZH | ~2.3M samples | Empathy-centered (lắng nghe, an ủi, tin tưởng) | Public | Dataset quy mô rất lớn, LLM sinh ra để cải thiện khả năng empathy, lắng nghe và an ủi của chatbot. Tập trung vào emotional support hơn là tham vấn lâm sàng có cấu trúc. Fine-tune SoulChat model trên dataset này (EMNLP 2023 Findings). | Đại diện "emotional support thuần" — case bị rubric trị liệu phạt (F7: SoulChat yếu Clinical/Assessment). Minh họa ranh giới empathy ≠ counseling. |
| 10 | 4 · LLM role-play | **KMI** | 2025 | KO | 1,000 dlg | Motivational Interviewing (MI) | Public (NAACL 2025) | Dataset hội thoại MI tiếng Hàn sinh bằng GPT-4 + MI forecasting. Mô phỏng quy trình MI với client personas và giai đoạn thay đổi hành vi. | **Cặp matched với AnnoMI** (cùng MI). Đã có pilot: phát hiện translation artifact (F4) và strength profile "đúng mực nhưng kém kết nối" (F7). |
| 11 | 4 · LLM-expanded | **SMILE (SmileChat)** ★ | 2023 (EMNLP 2024) | ZH | 55,165 dlg · avg 10.4 turns | Tham vấn tâm lý (kế thừa PsyQA) | Public (GitHub/HF) | Đề xuất kỹ thuật SMILE: dùng ChatGPT mở rộng cặp QA đơn lượt (từ PsyQA) thành hội thoại nhiều lượt. Phân tích tính khả thi qua language transformation analysis + đánh giá đa dạng (lexical, semantic, topical). Train chatbot MeChat; đánh giá bằng cả automatic và human evaluation so với dữ liệu tham vấn thật. | **Ablation sạch nhất toàn bài:** cùng nội dung nguồn với PsyQA (Bảng 2), chỉ khác bước "LLM hóa" → đo trực tiếp ảnh hưởng của LLM expansion lên chất lượng. |
| — | *(2 · Semi-real, multi-session)* | ***MusPsy*** *(case study)* | 2025 | ZH | Multi-session / client | Tham vấn tâm lý theo tiến trình | Cần xác minh repo (HIT-SCIR) | Đề xuất dataset multi-session đầu tiên cho tham vấn tâm lý tự động. Xây từ profile client thật (case report công khai), mô hình hóa therapeutic arc qua nhiều session liên tiếp. Phát triển MusPsy-Model để theo dõi tiến triển client và điều chỉnh hướng tham vấn theo thời gian. Đánh giá bằng GPT-4o + human trên 4 metric + 3 chiều WAI. | **Section mở rộng riêng** (10–15 case). Kiểm chứng framework mở rộng sang multi-session. Đối chiếu alliance xuyên session với finding "alliance không tăng theo session" của bài Alliance. |

### Tổng kết phổ provenance (Multi-turn)

| Bậc | Số dataset | Đại diện |
|---|---|---|
| 1 · Real counseling | 2 | AnnoMI (EN), Psy-Insight (EN+ZH) |
| 2 · Semi-real | 2 (+1 multi-session) | PsyDial (ZH), CPsyCoun (ZH), MusPsy (ZH, case study) |
| 3 · Human role-play | 2 | KokoroChat (JA), ESConv (EN) |
| 4 · LLM role-play/generated | 5 | CACTUS (EN), SimPsyDial (ZH), SoulChat (ZH), KMI (KO), SMILE (ZH) |

### Cặp đối chứng chính (Matched Pairs)

| Cặp | Biến kiểm soát | Câu hỏi trả lời |
|---|---|---|
| **AnnoMI ↔ KMI** | Cùng MI, khác provenance (real vs LLM) | Phương thức thu thập ảnh hưởng thế nào khi cùng framework? |
| **KokoroChat ↔ CACTUS / SimPsyDial** | Cùng role-play, khác actor (người vs LLM) | Người đóng vai vs LLM đóng vai tạo chất lượng khác nhau thế nào? |
| **PsyDial ↔ CPsyCoun** | Cùng bậc 2, cùng ZH, khác pipeline tái dựng | Pipeline semi-real nào cho chất lượng cao hơn? |
| **PsyQA (Bảng 2) ↔ SMILE** | Cùng nội dung nguồn, khác cấu trúc (ST→MT) | LLM expansion ảnh hưởng thế nào đến chất lượng? |
| **ESConv ↔ CACTUS** | Cùng EN, khác provenance (crowd vs LLM) | Crowdsource vs LLM synthetic trong cùng ngôn ngữ? |

---


## Ghi chú

- ★ = dataset mới đề xuất bổ sung (chưa có trong slide gốc)
- Bậc 3 single-turn trống: đây là observation tự nhiên đáng ghi trong paper — cấu trúc QA đơn lượt hầu như chỉ được xây bằng crawl thật hoặc LLM sinh, không ai thuê người đóng vai viết Q&A
- **MusPsy** được đặt ngoài bảng chính, ở section case study riêng vì: (1) không có đối thủ multi-session để so sánh, (2) đơn vị phân tích khác (case → sessions → turns), (3) availability cần xác minh
- Tổng: **11 multi-turn + 5 single-turn = 16 datasets** (+ 1 case study MusPsy)

Tổng hợp 12 Findings:
F1 — Ranking tổng thể ổn định: cactus hạng 1, KMI hạng cuối trên cả 3 settings (S1/S2/S3). Ranking phản ánh đúng "chất lượng tương đối" giữa các dataset trong pilot.
  > 🟡 **Kiểm chứng (dựa trên kết quả đánh giá):** cactus #1 VỮNG (Dim-A 3.51 + WAI 4.36 + dưới Claude 3.27). Nhưng "KMI hạng cuối" CHỈ đúng ở S1 — do `utterance_en` (xem F4); ở S3/bản ngữ KMI=2.93 (hạng 8/11), **hạng cuối thật là ESConv 2.29**. "Ranking phản ánh chất lượng tương đối" quá mạnh: thứ hạng **phụ thuộc thước đo** — Spearman(Dim-A, Dim-B)=0.21.
F2 — Ethics luôn cao nhất, AIComm luôn thấp nhất ở mọi dataset. Đây là tiền đề cho F12.
  > 🟡 **Kiểm chứng:** Ethics cao nhất ✅ (10/11 dưới GPT; ESConv ngoại lệ→Alliance). "AIComm luôn thấp nhất" KHÔNG chính xác — chiều thấp nhất là **Assessment HOẶC AIComm** (Assessment đáy ở 6/11, AIComm ở 5/11). Nên sửa thành "Assessment/AIComm thấp nhất". Tiền đề F12 vẫn đúng.
F3 — S1 có sức phân biệt cao nhất (std Overall = 0.311 > S3 = 0.254 > S2 = 0.159). Tức đánh giá hoàn toàn bằng EN phân biệt tốt nhất giữa các dataset.
  > 🔴 **Kiểm chứng — KHÔNG tái lập trên dữ liệu rộng:** trên 7 dataset có đủ S2, SD_across của Overall: S1=0.205, S2=0.214, S3=0.182 — **ba setting xấp xỉ nhau**, không phải S1≫S2. Lợi thế phân biệt của S1 trong pilot 6-dataset gần như chắc chắn do outlier KMI-`utterance_en` (chính là artifact F4) kéo giãn dải S1. → **F3 bị F4 thâu tóm; nên bỏ hoặc viết lại.**
F4 (*) — Translation artifact ở KMI: bản dịch có sẵn (utterance_en) bị mất sắc thái văn hóa (kính ngữ tiếng Hàn), khiến KMI bị chấm thấp hơn 0.365 điểm so với bản dịch mới bằng GPT-5.1. Kết luận: đừng ship bản dịch "làm sẵn" kèm dataset bản ngữ.
  > ✅ **Kiểm chứng — VỮNG (tái lập 3 chữ số):** S1-utt Overall 2.672 vs GPT dịch lại 3.038 vs bản ngữ S2 2.948 → mất **+0.365**. 🔧 *Đính chính:* mất điểm **KHÔNG tập trung ở Ethics** mà gần đều, **lớn nhất ở Assessment (+0.413) và Alliance (+0.412)**. Guideline "đừng ship bản dịch làm sẵn" đứng vững.
F5 — Bản dịch ảnh hưởng đáng kể đến ranking: Spearman S1-vs-S3 chỉ r=0.503 (thấp). Riêng KMI là dataset duy nhất có sig_diff=True giữa S1 và S2, và giữa S1 và S3 — phần lớn do F4.
  > 🟡 **Kiểm chứng — cần ĐẢO hướng kết luận:** Spearman(S1,S3) thực ra **CAO**: 0.750 (7 non-EN) / **0.909 (11 dataset)** → ranking S1≈S3, **dịch KHÔNG đảo ranking** (con số 0.503 là artifact pilot n=6). Dịch chỉ xáo trộn từng *item* (mean|Δ|≈0.17). KMI sig_diff ✅ (do F4). → Kết luận đúng: **ranking ổn định qua dịch (ủng hộ 'dùng S3')**, riêng KMI lệch vì `utterance_en`.
F6 — S2 ≈ S3 cho hầu hết dataset (PsyDial r=0.809, SoulChat r=0.754): ngôn ngữ judge (bản ngữ vs EN) ít ảnh hưởng hơn ngôn ngữ hội thoại. Khuyến nghị: dùng S3 (dịch hội thoại sang EN + judge EN) cho ngôn ngữ non-EN.
  > 🟡 **Kiểm chứng — đúng cho ZH, KHÔNG cho JA:** S2≈S3 trung bình (+0.016) nhưng **KokoroChat (Nhật) lệch +0.26**. Khuyến nghị 'dùng S3 cho non-EN' hợp lý, nhưng 'S2≈S3' **không phổ quát** — với ngôn ngữ mới (VN) phải pilot lại (JA đã phá vỡ).
F7 (*) — Strength profile phản ánh theory grounding: KMI (MI) mạnh duy nhất Ethics nhưng yếu Alliance; cactus (CBT, full session) mạnh đều; SoulChat (emotional support) bị phạt Clinical. Metric signature khớp với lý thuyết xây dựng dataset — bằng chứng rubric đo đúng thứ cần đo.
  > ✅ **Kiểm chứng — VỮNG (mô tả):** z-profile: KMI Ethics z+0.89, AIComm z−1.52 (yếu nhất bảng) ✓; cactus mọi chiều z>+1.3 ✓; SoulChat Clinical z−0.60 nhưng mạnh WAI Bond ✓. ⚠️ Là **pattern mô tả** trên 11 dataset → 'nhất quán với lý thuyết', chưa phải test giả thuyết (cần neo ngoài như nhãn AnnoMI để thành construct validity thật).
F8 — 5 metrics thực chất chỉ ~2 chiều: Clinical↔Assessment r=0.92, Alliance↔AIComm r=0.85. Toàn bộ 5 metrics gần như sụp thành 2 nhân tố. Hệ quả: Dim B (WAI-O-S) có nguy cơ trùng với metric Alliance của Dim A → cần kiểm tra bằng factor analysis ở N=200.
  > 🟡 **Kiểm chứng — một nửa đúng, nhưng headline MẠNH hơn:** Clinical↔Assess r=0.88 (GPT)/**0.94 (Claude)** ✓ — số 0.92 chính là giá trị Claude. **Alliance↔AIComm chỉ r=0.70–0.72, KHÔNG phải 0.85.** Bằng chứng mạnh nhất: **PCA → PC1 giải thích 79% phương sai** ⇒ cả 5 metric ≈ **1 nhân tố trội** (mạnh hơn '2 chiều'). Dim-B(WAI)↔metric Alliance: item-level r=0.60 (trùng *một phần*). **Dim-C thì ĐỘC LẬP** (item r≈0) → chiều thứ 3 KHÔNG dư thừa.
F9 (*) — Hai judge đo hai construct khác nhau dưới cùng tên "AIComm": GPT-5.1 vs Claude correlation chỉ ρ=0.29 trên AIComm, trong khi các metric khác ρ=0.6–0.8. Case cụ thể: psyinsight_000856 — GPT chấm 2.5 vì "mechanical/scripted", Claude chấm 5.0 vì "remarkably natural" cho cùng đoạn hội thoại. Nguyên nhân: rubric thiếu decision rule cho human transcript (khi nào thì "AI-like" áp dụng cho counselor người thật?). Đây là đóng góp phương pháp luận về LLM-as-judge.
  > ✅ **Kiểm chứng — VỮNG:** within-dataset r(GPT,Claude) trên AIComm = **0.33** (≈0.29; pooled 0.55) — **thấp nhất mọi chiều** (các chiều khác 0.53–0.63); cactus thậm chí **−0.06**. Case `psyinsight_000856` **tái lập CHÍNH XÁC**: cùng đoạn 'So, um/Hmm' → GPT 2.5 'mechanical', Claude 5.0 'exceptionally natural'.
F10 — Provenance confound (LLM judge thiên vị văn LLM?): hai dataset LLM-simulated (cactus, SimPsyDial) chiếm top-2 dưới cả hai judge. Không tách được "LLM judge thích văn LLM" khỏi "chất lượng thật cao hơn" bằng thiết kế hiện tại — lý do bắt buộc có lớp human expert validation.
  > ✅ **Kiểm chứng — VỮNG:** cactus #1, simpsydial #2 dưới **CẢ GPT lẫn Claude** (Dim-A *và* WAI). Tier-level: Dim-A của LLM-sim (3.13) = Real (3.12) → **rubric KHÔNG phân biệt được provenance** (xem §Provenance). Củng cố bởi gradient happy-ending. → **bắt buộc human anchor.**
F11 — Claude chấm thấp hơn GPT-5.1 một cách hệ thống: Global mean Δ = −0.367 (Claude luôn thấp hơn). SoulChat bị Claude phạt nặng nhất (Δ = −0.495 ở S1, −0.713 ở S2). Cần kiểm tra judge nào "đúng hơn" bằng human anchor.
  > ✅ **Kiểm chứng — VỮNG:** GPT−Claude = **+0.388** (Claude thấp hơn, ≈ −0.367) trên 6 dataset; **lớn nhất ở Ethics (+0.71) & Clinical (+0.55)**, nhỏ nhất TRA (+0.14). SoulChat bị Claude phạt nặng nhất (+0.69 ở S3).
F12 (*) — "An toàn bề mặt, nông về can thiệp" (Safe but Shallow): Ethics cao nhất ở mọi dataset, mọi judge, mọi setting; Assessment và AIComm thấp nhất. Tức toàn bộ thế hệ dataset hiện tại (cả real lẫn synthetic) đạt chuẩn đạo đức nhưng yếu ở khả năng đánh giá vấn đề và can thiệp cụ thể. Đây là claim tổng quát về cả field, mạnh hơn việc xếp hạng từng dataset.
  > ✅ **Kiểm chứng — VỮNG cho GPT, một phần cho Claude:** GPT: Ethics cao nhất **10/11**, thấp nhất ∈{Assessment,AIComm} **11/11** → rất vững. Claude: Ethics cao nhất chỉ **4/6**. → cụm 'mọi judge' hơi quá; **lõi (Ethics kịch trần, Assessment đáy) đứng vững**. Headline 'Safe but Shallow' giữ nguyên.
Trong số 12 findings, mình đánh giá F12, F9, F7, F4 là có giá trị paper Q1 cao nhất — F12 làm headline ("Safe but Shallow"), F9 là đóng góp phương pháp luận (LLM-as-judge divergence), F7 nối metrics với lý thuyết tâm lý (construct validity), F4 là guideline thực tiễn cho xây dataset đa ngôn ngữ. Kết hợp với F-C1 của Dim C (happy-ending gradient), bạn có 5 findings chính cho paper — đủ chất cho Q1.

=====================
# Kết quả đánh giá tổng quan theo phổ provenance (multi-turn)

> Tổng hợp điểm thực nghiệm theo 4 bậc provenance. **Dim-A** = rubric Overall (GPT, S3, thang 1–6) · **Dim-B** = WAI total (thang 1–5) · **Dim-C**: `nec` = Net Emotional Change (last−first valence), `happy%` = tỉ lệ hội thoại client kết thúc tích cực hơn. *(Single-turn chưa xét theo yêu cầu.)*

| Dataset | Bậc provenance | Dim-A | Dim-B | nec | happy% |
|---|---|---|---|---|---|
| AnnoMI | 1 · Real | 3.06 | 3.73 | +0.027 | 65% |
| Psy-Insight | 1 · Real | 3.19 | 3.35 | −0.000 | 50% |
| PsyDial | 2 · Semi-real | 3.01 | 4.11 | +0.045 | 75% |
| CPsyCoun | 2 · Semi-real | 3.02 | 3.46 | +0.023 | 65% |
| KokoroChat | 3 · Human role-play | 3.01 | 3.71 | +0.037 | 70% |
| ESConv | 3 · Human role-play | 2.29 | 3.88 | +0.082 | 78% |
| cactus | 4 · LLM role-play/gen | 3.51 | 4.36 | +0.049 | 72% |
| simpsydial | 4 · LLM role-play/gen | 3.29 | 4.21 | +0.079 | 95% |
| SoulChat | 4 · LLM role-play/gen | 2.81 | 3.99 | +0.073 | 70% |
| KMI | 4 · LLM role-play/gen | 2.93 | 3.75 | +0.076 | 74% |
| smile | 4 · LLM-expanded | 2.65 | 3.59 | +0.083 | 83% |

### Trung bình theo bậc

| Bậc provenance | Dim-A | Dim-B | nec | happy% |
|---|---|---|---|---|
| **1 · Real** | **3.12** | **3.54** | **+0.013** | **57%** |
| **2 · Semi-real** | 3.02 | 3.79 | +0.034 | 70% |
| **3 · Human role-play** | 2.65 | 3.80 | +0.060 | 74% |
| **4 · LLM role-play/gen** | 3.13 | 4.08 | +0.069 | 78% |
| **4 · LLM-expanded** (smile) | 2.65 | 3.59 | +0.083 | 83% |

### Ba phát hiện chính (dựa trên kết quả đánh giá)

**P1 — Rubric lâm sàng (Dim-A) MÙ trước provenance.** Real (3.12) ≈ LLM-sim (3.13); thậm chí Human-roleplay crowdsource (2.65) và LLM-expand (2.65) còn thấp hơn. → **Dim-A không phân biệt được dữ liệu thật vs tổng hợp** — đây chính là confound F10 lượng hóa ở cấp bậc. Hệ quả: không thể dùng riêng Dim-A để kết luận "phương thức nào tốt hơn".

**P2 — Dim-B (alliance) và Dim-C (cảm xúc) đều TĂNG về phía synthetic.** Dim-B: Real 3.54 → LLM-sim 4.08. Dim-C đơn điệu hoàn hảo: happy% **57% → 70% → 74% → 78% → 83%**. → **Dữ liệu tổng hợp được lý tưởng hóa về mặt cảm xúc**: ấm áp hơn (alliance cao) và "kết thúc có hậu" hơn. Tham vấn thật (AnnoMI/Psy-Insight) là **ít ấm nhất và ít resolved nhất** — đúng bản chất trị liệu thật: lộn xộn, biến thiên lâm sàng, cảm xúc chưa khép.

**P3 — F-C1 (Dim-C):** gradient happy-ending là finding Dim-C độc lập, kiểm chứng ở item-level r≈0 với cả Dim-A/B (không phải hệ quả của điểm judge). 🟡 *Giới hạn:* mỗi bậc chỉ 1–4 dataset → **giả thuyết mạnh, cần thêm dataset mỗi bậc** (đặc biệt bậc Real n=2) để test thống kê.

### Lưu ý đọc bảng
- **n mỗi bậc rất nhỏ (1–4 dataset)** → trung bình bậc là *chỉ báo*, không phải kết luận thống kê.
- **Phương sai trong bậc lớn:** bậc Real trộn AnnoMI (biến thiên cao, WAI 3.73) với Psy-Insight (rubric cao nhưng 7/20 hội thoại hỏng quỹ đạo, WAI 3.35). Bậc Human-roleplay: KokoroChat (Dim-A 3.01) vs ESConv (2.29, crowdsource ≠ chuyên gia) chênh rất lớn — ESConv kéo bậc 3 xuống ở Dim-A nhưng lại cao ở Dim-B/C (đúng tính chất emotional-support).
- Dim-A 1–6 và Dim-B 1–5 khác thang → **không so trực tiếp giá trị tuyệt đối giữa hai cột**, chỉ so xu hướng theo bậc trong cùng cột.

### Cặp đối chứng chính (Matched Pairs)

| Cặp | Biến kiểm soát | Câu hỏi trả lời |
|---|---|---|
| **AnnoMI ↔ KMI** | Cùng MI, khác provenance (real vs LLM) | Phương thức thu thập ảnh hưởng thế nào khi cùng framework? |
| **KokoroChat ↔ CACTUS / SimPsyDial** | Cùng role-play, khác actor (người vs LLM) | Người đóng vai vs LLM đóng vai tạo chất lượng khác nhau thế nào? |
| **PsyDial ↔ CPsyCoun** | Cùng bậc 2, cùng ZH, khác pipeline tái dựng | Pipeline semi-real nào cho chất lượng cao hơn? |
| **PsyQA (Bảng 2) ↔ SMILE** | Cùng nội dung nguồn, khác cấu trúc (ST→MT) | LLM expansion ảnh hưởng thế nào đến chất lượng? |
| **ESConv ↔ CACTUS** | Cùng EN, khác provenance (crowd vs LLM) | Crowdsource vs LLM synthetic trong cùng ngôn ngữ? |

#### Số liệu kết quả cho từng cặp (dựa trên kết quả đánh giá · GPT, setting S3)

> Cột: **Dim-A** = Overall (thang 1–6) · **SD** = độ phân tán nội bộ · **WAI** = total (1–5) · **nec / happy%** = Dim-C. *(Mọi cặp dùng GPT vì mỗi cặp có ≥1 dataset chưa chạy Claude.)*

**① AnnoMI ↔ KMI** — cùng MI, real vs LLM

| | Dim-A | SD | WAI | nec | happy% |
|---|---|---|---|---|---|
| AnnoMI (real) | 3.06 | **0.86** | 3.73 | +0.027 | 65% |
| KMI (LLM) | 2.93 | **0.21** | 3.75 | +0.076 | 74% |

→ **Trả lời:** giữ nguyên framework MI, provenance **gần như không đổi Dim-A trung bình** (3.06 vs 2.93) lẫn WAI (≈3.74). Khác biệt nằm ở **chữ ký, không phải mức điểm**: (a) real có **phương sai gấp ~4×** (0.86 vs 0.21 — AnnoMI chứa cả MI giỏi lẫn dở, KMI đồng đều); (b) KMI "an toàn hơn" (Ethics 3.99 vs 3.45) nhưng **máy móc hơn** (AIComm 2.31 vs 2.89) và **kết thúc vui hơn** (74% vs 65%). → Provenance hiện ra ở *variance + style + happy-ending*, không ở chất lượng lâm sàng trung bình.

**② KokoroChat ↔ cactus / simpsydial** — human role-play vs LLM role-play

| | Dim-A | SD | WAI | nec | happy% |
|---|---|---|---|---|---|
| KokoroChat (human, JA) | 3.01 | 0.21 | 3.71 | +0.037 | 70% |
| cactus (LLM, EN) | 3.51 | 0.18 | 4.36 | +0.049 | 72% |
| simpsydial (LLM, ZH) | 3.29 | 0.16 | 4.21 | +0.079 | 95% |

→ **Trả lời:** LLM role-play cao hơn human role-play ở **cả Dim-A (+0.3–0.5) lẫn WAI (+0.5–0.65)**. ⚠️ **Confound ngôn ngữ:** KokoroChat là tiếng Nhật (F6 cho thấy JA là ngoại lệ của ngôn ngữ judge) → chênh lệch *một phần* do ngôn ngữ → **đây là cặp kém sạch nhất**. Độ đồng nhất tương đương (0.16–0.21): human role-play *cũng* rất đồng đều, khác hẳn real AnnoMI.

**③ PsyDial ↔ CPsyCoun** — cùng semi-real, cùng ZH, khác pipeline tái dựng *(CẶP SẠCH NHẤT — kiểm soát tốt nhất)*

| | Dim-A | SD | WAI | nec | happy% |
|---|---|---|---|---|---|
| PsyDial (RMRR · từ hội thoại thật) | 3.01 | 0.29 | **4.11** | +0.045 | 75% |
| CPsyCoun (Memo2Demo · từ case report) | 3.02 | 0.19 | **3.46** | +0.023 | 65% |

→ **Trả lời:** pipeline **KHÔNG đổi Dim-A** (3.01 vs 3.02, y hệt) nhưng **đổi mạnh alliance** (WAI **+0.65**). PsyDial dựng *từ hội thoại counselor–client thật* → giữ hơi ấm tương tác (Alliance 3.09, happy 75%); CPsyCoun dựng *từ case report* → cấu trúc lâm sàng nhưng alliance phẳng (2.79, happy 65%). → **Chọn pipeline = đánh đổi alliance, không đụng năng lực lâm sàng đo được.**

**④ PsyQA ↔ SMILE** — cùng nguồn, ST→MT

→ 🔴 **Chưa đủ dữ liệu:** PsyQA là single-turn, hiện chưa chạy. Mới có SMILE (MT): Dim-A 2.65 · WAI 3.59 · nec +0.083 · happy 83%. Cần chạy PsyQA (7-metric ST) để hoàn tất cặp này.

**⑤ ESConv ↔ cactus** — cùng EN, crowd vs LLM

| | Dim-A | SD | WAI | nec | happy% |
|---|---|---|---|---|---|
| ESConv (crowd, EN) | **2.29** | 0.37 | 3.88 | +0.082 | 78% |
| cactus (LLM, EN) | **3.51** | 0.18 | 4.36 | +0.049 | 72% |

→ **Trả lời:** cactus áp đảo Dim-A (**+1.22 — chênh lớn nhất toàn bài**), đậm nhất ở Ethics (4.25 vs 2.33) và Clinical (3.58 vs 2.35). Nhưng ESConv **bám sát WAI** (3.88 vs 4.36) và **vượt về cảm xúc** (happy 78% vs 72%, nec +0.082 vs +0.049). ⚠️ **Confound mục đích:** ESConv là *emotional support*, không phải trị liệu lâm sàng → rubric phạt nó vì không làm thứ nó không định làm (đúng hiện tượng F7). Khoảng cách Dim-A vì thế **thổi phồng** khác biệt "chất lượng".

> **Tổng hợp xuyên cặp:** hai cặp kiểm soát chặt (③ cùng ZH/tier; ① cùng MI) cho thấy **provenance/pipeline tác động lên ALLIANCE và VARIANCE/STYLE, không lên điểm lâm sàng trung bình**. Hai cặp cross-provenance (②, ⑤) có chênh Dim-A lớn nhưng bị nhiễu bởi **ngôn ngữ (②)** và **mục đích (⑤)**. Sợi chỉ chung: LLM/synthetic → alliance ↑, happy-ending ↑, variance ↓, "an toàn" hơn (Ethics↑) nhưng "máy móc" hơn (AIComm↓); real → variance ↑, cảm xúc chưa khép. **Khớp với §Provenance và F10: điểm lâm sàng không phân biệt được nguồn gốc — khác biệt thật nằm ở alliance, cảm xúc, và độ phân tán.**

### Một insight bấp bênh khi nó ngầm hỏi "điểm cao này có phải vì chất lượng thật không?". Mọi thứ trong vùng vàng đều vướng đúng câu đó. Mà LLM-judge không tự trả lời được — vì nếu cả GPT, Claude (và có thể cả Gemini) đều thích văn LLM, chúng sẽ cùng đẩy cactus lên #1, và bạn không có cách nào nhìn thấy thiên kiến đó từ bên trong. Phải có một tín hiệu đến từ ngoài LLM. Bạn chỉ có đúng hai nguồn như vậy:

### Human có sẵn trong dataset (nhãn high/low của AnnoMI, self-report của ESConv) → trả lời "có đúng chất lượng thật không" = validity.
### Judge thứ 3 khác họ → trả lời "thiên kiến này là của riêng GPT/Claude hay dùng chung" = reliability + lộ bias chung.

### 2 việc cần bổ sung
**1. Human-in-dataset neo cho dim nào?**
Không chọn một dim chung — mỗi tín hiệu người neo cho đúng dim mà nó cùng "khái niệm". Điều hay là gộp lại, các dataset phủ được cả ba dim, mỗi dim một nguồn khác nhau:
Tín hiệu người (có sẵn)Nó thực chất đo gìNeo cho dimPhép testAnnoMI — nhãn chuyên gia high/low MInăng lực trị liệu (MI competence)Dim-A (rubric lâm sàng)known-groups (nhãn rời rạc) → AUC, Mann-WhitneyESConv — emotion intensity trước/sau của seekerclient cảm thấy đỡ hơn bao nhiêuDim-C (nec/net change)tương quan (Spearman)ESConv — feedback 1–5★ của supporterhỗ trợ có giúp khôngDim-B (alliance) + một phần Atương quanKokoroChat — client feedback mỗi dialogueđánh giá phiên tham vấnDim-A/Btương quanCounselChat — upvote câu trả lờichất lượng cộng đồngDim-A (single-turn)tương quan
Hai điểm quan trọng:

ESConv → Dim-C là mỏ neo sạch nhất và cấp thiết nhất. Vì Dim-C là chân yếu nhất (lexicon native chỉ phủ 44%, A vs B chỉ đồng thuận r=0.44), mà ESConv lại cho đúng cùng khái niệm: seeker tự báo cảm xúc đầu–cuối, so thẳng với nec (cảm xúc đo bằng VAD). Nếu hai cái tương quan dương → Dim-C đo đúng cảm xúc thật. Đây là cách duy nhất gỡ "treo" cho Dim-C.
AnnoMI → Dim-A là cái mở khóa mục tiêu ranking (cactus #1 thật hay ảo). Lưu ý khi chạy: nhãn MI chỉ neo được các metric lâm sàng (Clinical, Assessment) — đừng kỳ vọng AIComm tách được high/low, vì AnnoMI là transcript người, AIComm là về "chất LLM", không liên quan. Chiều nào PASS cho biết chiều đó đo đúng chất lượng thật.

→ Tóm lại: A neo bằng AnnoMI · B neo bằng ESConv-star · C neo bằng ESConv-intensity. Mỗi dim một nguồn, không cái nào neo được cả ba.
**2. Judge thứ 3 kiểm reliability trên dim nào?**
Chủ yếu Dim-A (bộ rubric 5 metric), vì ba lý do:

Dim-A là chỗ bạn đã có GPT vs Claude → thêm judge thứ 3 hoàn tất tam giác để tính Krippendorff α/ICC. Dim-B (WAI) hiện chỉ có GPT chạy — tức Dim-B đang không có một mẩu reliability nào, còn hở hơn cả Dim-A. Nếu dư ngân sách, nên thêm Claude + judge-3 cho Dim-B nữa (nhưng WAI tốn 36 call/dialogue → ưu tiên sau).
Vấn đề bất đồng nằm gọn ở AIComm của Dim-A (within-r=0.33). Judge thứ 3 trả lời dứt điểm: AIComm cứu được hay phải loại khỏi ranking.
Phép thử confound F10 ("model khác họ có cũng đẩy synthetic lên top không?") chạy trên Dim-A — đúng dim đang dùng để ranking.

Dim-C KHÔNG cần judge thứ 3 — nó là tính toán lexicon NRC-VAD tất định (chạy lại ra y hệt, không có nhiễu để triangulate). Reliability của Dim-C là chuyện coverage/validity (mục 1), không phải chuyện đồng thuận giữa các judge.
→ Tóm lại: judge-3 cho Dim-A trước (rẻ, đúng chỗ có vấn đề), mở rộng Dim-B nếu còn budget, bỏ qua Dim-C.
