---
license: cc-by-nc-nd-4.0
task_categories:
- text-generation
- text-classification
language:
- ja
tags:
  - nlp
  - dialogue
  - dialogue-corpus
  - dialogue-system
size_categories:
- 100M<n<1B
---
<div align="center">
  <img src="./kokorochat_logo_.png" alt="KokoroChat Logo" width="500"/>
</div>


<!-- [![Conference](https://img.shields.io/badge/Conference-ACL-blueviolet)](https://drive.google.com/file/d/1T6XgvZii8rZ1kKLgOUGqm3BMvqQAvxEM/view?usp=sharing) -->
[![CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![Model](https://img.shields.io/badge/🤗_Hugging_Face-Model-ffcc66.svg)](https://huggingface.co/UEC-InabaLab/Llama-3.1-KokoroChat-High)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-121013?logo=github&logoColor=white)](https://github.com/UEC-InabaLab/KokoroChat)
[![ACL 2025](https://img.shields.io/badge/ACL--2025-Paper-4b6ea9)](https://aclanthology.org/2025.acl-long.608/)



# KokoroChat: A Japanese Psychological Counseling Dialogue Dataset Collected via Role-Playing by Trained Counselors

**KokoroChat** is the largest human-collected Japanese psychological counseling dialogue dataset to date (as of June 2025). It was created through role-playing between trained counselors and includes rich, long-form dialogues and detailed client feedback on counseling quality. The dataset supports research on empathetic response generation, dialogue evaluation, and mental health-oriented language modeling.

This work has been **accepted to the main conference of ACL 2025**.
📄 [View Paper](https://aclanthology.org/2025.acl-long.608/)

---

## 🌟 Key Features

- 6,589 dialogues, collected between 2020 and 2024
- Avg. 91.2 utterances per dialogue
- 480 trained counselors simulating online text-based counseling sessions
- 20-dimension Likert-scale client feedback for every session
- Broad topic coverage: mental health, school, family, workplace, romantic issues, etc.

---

## 📊 Dataset Statistics

| Category                    | Total     | Counselor | Client    |
|----------------------------|-----------|-----------|-----------|
| **# Dialogues**            | 6,589     | -         | -         |
| **# Speakers**             | 480       | 424       | 463       |
| **# Utterances**           | 600,939   | 306,495   | 294,444   |
| **Avg. utterances/dialogue** | 91.20     | 46.52     | 44.69     |
| **Avg. length/utterance**  | 28.39     | 35.84     | 20.63     |

---

## 📁 Dataset Structure

Each sample contains:
- A full counseling dialogue with role labels (counselor / client) and message timestamps
- Structured client feedback on 20 dimensions (0–5 Likert scale)
- Flags for ethical concern checks (optional)
- Predicted topic label (automatically annotated by GPT-4o-mini)

👉 See the `kokorochat_dialogues` folder for the complete dataset.

---

## 🤖 Models Trained on KokoroChat

The following models were fine-tuned on subsets of the KokoroChat dataset with different feedback score ranges:

- [**Llama-3.1-KokoroChat-Low**](https://huggingface.co/UEC-InabaLab/Llama-3.1-KokoroChat-Low):  
  Fine-tuned on **3,870 dialogues** with client feedback scores **< 70**

- [**Llama-3.1-KokoroChat-High**](https://huggingface.co/UEC-InabaLab/Llama-3.1-KokoroChat-High):  
  Fine-tuned on **2,601 dialogues** with scores between **70 and 98**

- [**Llama-3.1-KokoroChat-Full**](https://huggingface.co/UEC-InabaLab/Llama-3.1-KokoroChat-Full):  
  Fine-tuned on **6,471 dialogues** (excluding 118 test samples with score ≥ 99), with scores **≤ 98**

- 🤖 **Score Prediction Model**:
  - [Llama-3.1-KokoroChat-ScorePrediction](https://huggingface.co/UEC-InabaLab/Llama-3.1-KokoroChat-ScorePrediction): fine-tuned to **predict client feedback scores** based on the full counseling dialogue history.


---

## 📄 Citation

If you use this dataset, please cite the following paper:

```bibtex
@inproceedings{qi2025kokorochat,
  title     = {KokoroChat: A Japanese Psychological Counseling Dialogue Dataset Collected via Role-Playing by Trained Counselors},
  author    = {Zhiyang Qi and Takumasa Kaneko and Keiko Takamizo and Mariko Ukiyo and Michimasa Inaba},
  booktitle = {Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics},
  year      = {2025},
  url       = {https://github.com/UEC-InabaLab/KokoroChat}
}
```

---

## ⚖️ License

KokoroChat is released under the [**Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)**](https://creativecommons.org/licenses/by-nc-nd/4.0/) license.

[![CC BY-NC-ND 4.0][cc-by-nc-nd-image]][cc-by-nc-nd]

[cc-by-nc-nd]: http://creativecommons.org/licenses/by-nc-nd/4.0/
[cc-by-nc-nd-image]: https://licensebuttons.net/l/by-nc-nd/4.0/88x31.png
[cc-by-nc-nd-shield]: https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg