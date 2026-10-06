1. Bộ 10 datasets đã đủ cho mục đích chưa?
Chưa đủ, và có một vài lỗ hổng cấu trúc cần xử lý trước khi viết.
Mâu thuẫn nội bộ đầu tiên: slide liệt kê 10 datasets, nhưng thực nghiệm pilot lại chạy trên 6 datasets trong đó có cactus và Psy-Insight không hề xuất hiện trong slide, còn ESConv, CUEMPATHY, AuraDial trong slide thì chưa được chạy. Reviewer sẽ bắt lỗi này ngay — bạn cần thống nhất danh sách (mình nghĩ nên đưa cactus và Psy-Insight vào chính thức, vì cactus đang là anchor hạng 1 của toàn bộ kết quả).
Lỗ hổng lớn nhất với mục tiêu "so sánh phương thức thu thập": ma trận provenance × ngôn ngữ × cấu trúc của bạn đang bị confound nặng. Cụ thể:

Không có real counseling multi-turn nào khả dụng. CUEMPATHY là private và là speech — nếu không xin được access thì toàn bộ nhánh "human real" trong so sánh multi-turn sụp đổ, và kết luận "simulated vs human" chỉ còn dựa trên crowdsourced (ESConv) vốn không phải tham vấn thật. Đề xuất bổ sung: AnnoMI (MI thật, EN, multi-turn, public) — cặp này cực đẹp vì so trực tiếp được với KMI (MI synthetic): cùng framework lý thuyết, khác provenance — đây chính là matched comparison mà mục tiêu của bạn cần. Tương tự có thể cân nhắc HOPE/MEMO (transcript counseling EN) và CPsyCoun (ZH, tái dựng từ báo cáo tham vấn thật).
Nhánh single-turn quá mỏng: chỉ PsyQA (ZH), EmplifAI (JA, availability còn dấu "?"), và EmpatheticDialogues — mà ED không phải counseling, là chitchat emotion-grounded; chấm nó bằng 7 metric counseling sẽ lặp lại đúng hiện tượng SoulChat bị rubric phạt oan (F7). Hoặc bạn phải khung lại diễn giải, hoặc thay/bổ sung CounselChat (therapist thật trả lời, EN, single-turn) để có cặp real-vs-synthetic single-turn cùng ngôn ngữ.
Availability: CUEMPATHY private, EmplifAI và KMI còn "?" — với journal Q1, reproducibility là tiêu chí cứng. Mọi dataset trong bảng đánh giá chính nên public hoặc obtainable theo thủ tục rõ ràng.
Cho claim low-resource/VN: S2≈S3 mới được chứng minh trên ZH/KO — hai ngôn ngữ mà frontier model rất mạnh. Khuyến nghị "dùng S3 cho VN" hiện là ngoại suy chưa kiểm chứng. Bạn cần một pilot ~20 hội thoại tiếng Việt (tự dịch/tự tạo cũng được) chạy đúng thí nghiệm S2-vs-S3 — chi phí nhỏ nhưng biến khuyến nghị từ "suy đoán" thành "bằng chứng", và đây cũng chính là điểm bán hàng riêng của bài.
Multi-session: đúng là gap thật, nhưng hiện bạn chỉ có thể bàn định tính. Có thể tận dụng corpus 859 sessions của bài Alliance (avg 10.48 sessions/client) làm bằng chứng gián tiếp — finding "alliance không tăng theo số session" của họ là motivation rất tốt cho luận điểm này.

2. Insight bạn chưa khai thác
Mấy điểm trong báo cáo phân tích thực ra có giá trị paper cao hơn cả phần ranking:

F12 — "An toàn bề mặt, nông về can thiệp": Ethics cao nhất ở mọi dataset, mọi judge, trong khi Assessment/AIComm thấp nhất. Đây là claim tổng quát về toàn bộ thế hệ dataset hiện tại — đáng làm finding chủ đạo, mạnh hơn việc xếp hạng.
F8 — 5 metric thực chất ~2 chiều (Clinical↔Assess r=0.92). Hệ quả nghiêm trọng hơn bạn nghĩ: khi chạy Dim B, rất có thể WAI trùng với metric Alliance của Dim A → 3 dimension A/B/C của bạn có thể không độc lập như slide tuyên bố. Nếu kiểm tra và thấy đúng, bản thân điều đó là một finding (framework đánh giá đa chiều hiện hành bị redundant); nếu sai, bạn có bằng chứng justify framework. Đằng nào cũng thắng — nên chạy factor analysis ở N=200.
F9 — hai judge chấm hai khái niệm khác nhau dưới cùng tên AIComm (ρ=0.29). Đây là đóng góp phương pháp luận độc lập về LLM-as-judge: rubric thiếu decision rule cho human transcript khiến construct phân kỳ. Case psyinsight_000856 (GPT chấm 2.5 "mechanical", Claude chấm 5.0 "remarkably natural" cho cùng đoạn) là ví dụ minh họa rất "ăn tiền" trong paper.
F4/F5 — translation artifact hai chiều dẫn đến guideline thực tiễn chưa ai phát biểu rõ: đừng bao giờ ship bản dịch EN "làm sẵn" kèm dataset bản ngữ (bài học utterance_en của KMI làm mất 0.27 điểm oan, tập trung ở Ethics vì mất kính ngữ tiếng Hàn). Việc judge "đọc được" tín hiệu văn hóa như kính ngữ cũng mở ra luận điểm culture-aware evaluation — liên quan trực tiếp đến định hướng VN.
Strength profile khớp với theory grounding: KMI (MI) mạnh duy nhất Ethics nhưng yếu Alliance; cactus (CBT, full session) mạnh đều; SoulChat (emotional support) bị phạt Clinical. Tức chữ ký metric phản ánh lý thuyết xây dựng dataset — một giả thuyết kiểm chứng được và rất hợp với mục tiêu "phương thức nào cho mục đích nào". Nó cũng gợi ý framework của bạn nên conditional không chỉ theo cấu trúc (single/multi-turn) mà theo cả intent của dataset.
F10 — provenance confound: hai dataset LLM-simulated chiếm top-2 dưới cả hai judge khác gia đình. Bạn không thể tách "LLM judge thích văn LLM" khỏi chất lượng thật bằng thiết kế hiện tại — đây là lý do thứ hai (sau yêu cầu Q1) bắt buộc phải có lớp human expert đánh giá trên mẫu nhỏ.


=====
3. Đây là dạng bài gì, nên đặt tên thế nào?
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

## Bảng 2 — Single-turn Datasets (đánh giá trên 7 metrics MentalChat16K)

| # | Bậc Provenance | Dataset | Năm | Ngôn ngữ | Quy mô | Nguồn gốc cụ thể | Availability | Nội dung chính của bài báo | Vai trò trong thiết kế audit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **1 · Real** (web crawl) | **PsyQA** | 2021 | ZH | 22K Q / 56K A | Crawl từ nền tảng tham vấn online 壹心理 (Yixinli) | Public | Dataset QA tiếng Trung quy mô lớn thu thập từ nền tảng tham vấn tâm lý trực tuyến. Mỗi câu hỏi do người dùng thật đặt, mỗi câu trả lời do supporter/counselor viết. Annotate chiến lược hỗ trợ theo Hill's Helping Skills. Phân tích đặc trưng ngôn ngữ và kỹ thuật hỗ trợ trong dữ liệu. | **Anchor real ZH.** Nguồn gốc của SMILE (Bảng 1) → nối hai bảng, tạo cặp ablation ST↔MT. |
| 2 | 1 · Real (therapist response) | **CounselChat** ★ | 2020 | EN | 940 Q / 2,775 QA pairs | 433 therapist có giấy phép trả lời trên CounselChat.com | Public (GitHub/HF, MIT) | Tập dữ liệu scrape từ CounselChat.com — nền tảng nơi therapist có giấy phép hành nghề trả lời câu hỏi tâm lý để xây dựng uy tín. Mỗi QA pair có số upvote và lượt view, cho phép đánh giá chất lượng response theo cộng đồng. Bao phủ nhiều chủ đề: lo âu, trầm cảm, trauma, self-esteem, relationships. | **Anchor real EN** — nhánh single-turn hiện thiếu đối trọng EN-real. Có upvote → proxy chất lượng từ cộng đồng. Cùng phân bố topic với MentalChat16K Synthetic. |
| 3 | **2 · Semi-real** (audio → QA) | **Psych8K (ChatPsychiatrist)** ★ | 2023 | EN | 8,187 QA pairs từ 260 bản ghi âm | Transcript tham vấn thật → chuyển đổi thành QA | Public (GitHub) | Xây dataset từ 260 bản ghi âm tham vấn tâm lý thật, chuyển đổi thành cặp QA. Đào tạo ChatPsychiatrist — LLM chuyên biệt cho QA counseling tiếng Anh đầu tiên. Là baseline chính mà MentalChat16K so sánh (gấp đôi quy mô Psych8K). | Bậc 2 single-turn; chính là baseline MentalChat16K so sánh → context cho cặp Interview↔Synthetic. |
| 4 | 2 · Semi-real (transcript → QA) | **MentalChat16K — Interview** ★ | 2025 | EN | 9,775 QA pairs từ 378 sessions / 514 caregivers | Transcript clinical trial thật, paraphrase local bằng Mistral-7B | Public (HF) | Một nửa dataset MentalChat16K. Nguồn từ clinical trial can thiệp problem-solving therapy cho caregivers bệnh nhân hospice/palliative. Audio → human transcription → paraphrase cục bộ bằng Mistral-7B (không upload cloud vì privacy). Lọc QA < 40 từ + kiểm tra thủ công xóa PII. | Một nửa cặp đối chứng Interview↔Synthetic: **cùng paper, cùng format, cùng ngôn ngữ, khác provenance.** |
| 5 | **4 · LLM-generated** | **MentalChat16K — Synthetic** ★ | 2025 | EN | 6,338 QA pairs · 33 topics | GPT-3.5 Turbo sinh theo framework Airoboros, phân bố topic CounselChat | Public (HF) | Nửa còn lại của MentalChat16K. GPT-3.5 Turbo sinh patient queries theo 33 chủ đề (phân bố theo CounselChat), rồi sinh counselor responses. 100 mẫu human review. Paper gốc phát hiện: GPT-4 judge thiên vị phần synthetic; Gemini Pro ưu tiên interview data → bằng chứng cho dual-judge. 7 metrics validate bởi GPT-4 + Gemini Pro + human experts (KDD 2025). | Nửa kia cặp: matched pair tinh khiết nhất cho single-turn. Paper gốc cũng là nguồn 7 metrics → khai báo caveat khi đánh giá. |

### Tổng kết phổ provenance (Single-turn)

| Bậc | Số dataset | Đại diện |
|---|---|---|
| 1 · Real | 2 | PsyQA (ZH), CounselChat (EN) |
| 2 · Semi-real | 2 | Psych8K (EN), MentalChat16K Interview (EN) |
| 3 · Human role-play | 0 | *(Ô trống — observation đáng ghi: không ai thuê người đóng vai viết QA đơn lượt)* |
| 4 · LLM-generated | 1 | MentalChat16K Synthetic (EN) |

### Cặp đối chứng chính (Matched Pairs — Single-turn)

| Cặp | Biến kiểm soát | Câu hỏi trả lời |
|---|---|---|
| **MentalChat16K Interview ↔ MentalChat16K Synthetic** | Cùng paper, cùng format, cùng ngôn ngữ | Human-origin vs LLM-generated ảnh hưởng thế nào khi mọi thứ khác giống nhau? |
| **CounselChat ↔ MentalChat16K Synthetic** | Cùng phân bố topic (CounselChat là nguồn topic) | Real therapist vs LLM sinh: chênh lệch lớn nhất ở metric nào? |
| **PsyQA ↔ CounselChat** | Cùng bậc 1, khác ngôn ngữ (ZH vs EN) | Ngôn ngữ ảnh hưởng thế nào ở cùng bậc real? (áp dụng S1/S3 cho PsyQA) |

---

## Ghi chú

- ★ = dataset mới đề xuất bổ sung (chưa có trong slide gốc)
- Bậc 3 single-turn trống: đây là observation tự nhiên đáng ghi trong paper — cấu trúc QA đơn lượt hầu như chỉ được xây bằng crawl thật hoặc LLM sinh, không ai thuê người đóng vai viết Q&A
- **MusPsy** được đặt ngoài bảng chính, ở section case study riêng vì: (1) không có đối thủ multi-session để so sánh, (2) đơn vị phân tích khác (case → sessions → turns), (3) availability cần xác minh
- Tổng: **11 multi-turn + 5 single-turn = 16 datasets** (+ 1 case study MusPsy)

Tổng hợp 12 Findings:
F1 — Ranking tổng thể ổn định: cactus hạng 1, KMI hạng cuối trên cả 3 settings (S1/S2/S3). Ranking phản ánh đúng "chất lượng tương đối" giữa các dataset trong pilot.
F2 — Ethics luôn cao nhất, AIComm luôn thấp nhất ở mọi dataset. Đây là tiền đề cho F12.
F3 — S1 có sức phân biệt cao nhất (std Overall = 0.311 > S3 = 0.254 > S2 = 0.159). Tức đánh giá hoàn toàn bằng EN phân biệt tốt nhất giữa các dataset.
F4 (*) — Translation artifact ở KMI: bản dịch có sẵn (utterance_en) bị mất sắc thái văn hóa (kính ngữ tiếng Hàn), khiến KMI bị chấm thấp hơn 0.365 điểm so với bản dịch mới bằng GPT-5.1. Kết luận: đừng ship bản dịch "làm sẵn" kèm dataset bản ngữ.
F5 — Bản dịch ảnh hưởng đáng kể đến ranking: Spearman S1-vs-S3 chỉ r=0.503 (thấp). Riêng KMI là dataset duy nhất có sig_diff=True giữa S1 và S2, và giữa S1 và S3 — phần lớn do F4.
F6 — S2 ≈ S3 cho hầu hết dataset (PsyDial r=0.809, SoulChat r=0.754): ngôn ngữ judge (bản ngữ vs EN) ít ảnh hưởng hơn ngôn ngữ hội thoại. Khuyến nghị: dùng S3 (dịch hội thoại sang EN + judge EN) cho ngôn ngữ non-EN.
F7 (*) — Strength profile phản ánh theory grounding: KMI (MI) mạnh duy nhất Ethics nhưng yếu Alliance; cactus (CBT, full session) mạnh đều; SoulChat (emotional support) bị phạt Clinical. Metric signature khớp với lý thuyết xây dựng dataset — bằng chứng rubric đo đúng thứ cần đo.
F8 — 5 metrics thực chất chỉ ~2 chiều: Clinical↔Assessment r=0.92, Alliance↔AIComm r=0.85. Toàn bộ 5 metrics gần như sụp thành 2 nhân tố. Hệ quả: Dim B (WAI-O-S) có nguy cơ trùng với metric Alliance của Dim A → cần kiểm tra bằng factor analysis ở N=200.
F9 (*) — Hai judge đo hai construct khác nhau dưới cùng tên "AIComm": GPT-5.1 vs Claude correlation chỉ ρ=0.29 trên AIComm, trong khi các metric khác ρ=0.6–0.8. Case cụ thể: psyinsight_000856 — GPT chấm 2.5 vì "mechanical/scripted", Claude chấm 5.0 vì "remarkably natural" cho cùng đoạn hội thoại. Nguyên nhân: rubric thiếu decision rule cho human transcript (khi nào thì "AI-like" áp dụng cho counselor người thật?). Đây là đóng góp phương pháp luận về LLM-as-judge.
F10 — Provenance confound (LLM judge thiên vị văn LLM?): hai dataset LLM-simulated (cactus, SimPsyDial) chiếm top-2 dưới cả hai judge. Không tách được "LLM judge thích văn LLM" khỏi "chất lượng thật cao hơn" bằng thiết kế hiện tại — lý do bắt buộc có lớp human expert validation.
F11 — Claude chấm thấp hơn GPT-5.1 một cách hệ thống: Global mean Δ = −0.367 (Claude luôn thấp hơn). SoulChat bị Claude phạt nặng nhất (Δ = −0.495 ở S1, −0.713 ở S2). Cần kiểm tra judge nào "đúng hơn" bằng human anchor.
F12 (*) — "An toàn bề mặt, nông về can thiệp" (Safe but Shallow): Ethics cao nhất ở mọi dataset, mọi judge, mọi setting; Assessment và AIComm thấp nhất. Tức toàn bộ thế hệ dataset hiện tại (cả real lẫn synthetic) đạt chuẩn đạo đức nhưng yếu ở khả năng đánh giá vấn đề và can thiệp cụ thể. Đây là claim tổng quát về cả field, mạnh hơn việc xếp hạng từng dataset.
Trong số 12 findings, mình đánh giá F12, F9, F7, F4 là có giá trị paper Q1 cao nhất — F12 làm headline ("Safe but Shallow"), F9 là đóng góp phương pháp luận (LLM-as-judge divergence), F7 nối metrics với lý thuyết tâm lý (construct validity), F4 là guideline thực tiễn cho xây dataset đa ngôn ngữ. Kết hợp với F-C1 của Dim C (happy-ending gradient), bạn có 5 findings chính cho paper — đủ chất cho Q1.

