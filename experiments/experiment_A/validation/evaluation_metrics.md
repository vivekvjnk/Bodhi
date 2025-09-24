# **A Novel Approach to Evaluating Generative Knowledge Graph Systems**

Traditional evaluation metrics for information extraction, such as precision, recall, and F1 score, are based on a fundamental assumption: the ground truth dataset is a **complete and exhaustive** representation of all relevant facts. This assumption is invalidated when using a generative system like a Large Language Model (LLM) for tasks like Named Entity Recognition (NER), as these models can produce valid, factually correct entities that are not present in the original dataset's annotations. We call these **"valid novelties."**

To address this, we propose an adjusted evaluation framework that **dynamically expands the ground truth** to include these valid novelties. This approach reframes the evaluation from a strict comparison to a static benchmark to a more realistic assessment of the system's ability to **discover new knowledge**. By acknowledging that the universe of "correct" entities is larger than the original annotated dataset, our framework provides a fairer and more comprehensive measure of a generative model's true performance.

***

### **Adjusted Evaluation Metrics**

Our proposed evaluation framework redefines the core components of the F1 score to account for valid novelties.

#### **1. Adjusted Precision**

Precision measures the proportion of a system's positive predictions that are actually correct. In our framework, we consider both entities that perfectly match the original ground truth ($TP_{Strict}$) and those that are novel but factually correct ($TP_{Novel}$).

$Adjusted\ Precision = \frac{TP_{Strict} + TP_{Novel}}{TP_{Strict} + TP_{Novel} + FP_{False}}$

* $TP_{Strict}$: Entities correctly extracted that match the ground truth.
* $TP_{Novel}$: Entities extracted that are factually correct but are not in the ground truth.
* $FP_{False}$: Entities extracted that are incorrect (hallucinations or mistakes).

***

#### **2. Adjusted Recall**

Recall measures the proportion of all actual positive items that were correctly identified. In the traditional paradigm, the total set of actual positives is fixed and defined by the ground truth ($TP_{Strict} + FN$). Our framework expands this universe to include valid novel entities identified by the generative model.

$Adjusted\ Recall = \frac{TP_{Strict} + TP_{Novel}}{(TP_{Strict} + FN) + TP_{Novel}}$

* $TP_{Strict}$: Entities correctly extracted that match the ground truth.
* $TP_{Novel}$: Valid novel entities.
* $FN$: Entities in the ground truth that the system failed to extract.

The term **$(TP_{Strict} + FN)$** represents the original gold standard, while the addition of **$TP_{Novel}$** to the denominator creates a new, more comprehensive universe of "actual positives" for the purpose of evaluation. This ensures that recall will not exceed 1 and accurately reflects the generative system's knowledge discovery capabilities.

***

#### **3. Adjusted F1 Score**

The Adjusted F1 score is the harmonic mean of the adjusted precision and recall, providing a single, balanced metric that rewards both the accuracy of the system and its ability to discover novel, correct knowledge.

$Adjusted\ F1 = 2 \cdot \frac{Adjusted\ Precision \cdot Adjusted\ Recall}{Adjusted\ Precision + Adjusted\ Recall}$

***

### **LLM-as-a-Judge Methodology**

To implement this framework without relying on manual human annotation, we propose using a separate, powerful LLM as a "judge" to verify the factual correctness of "novel" entities. The judge LLM, guided by a robust scoring rubric, will analyze each entity extracted by the generative system that did not match the ground truth. This process allows us to programmatically classify entities as $TP_{Novel}$ or $FP_{False}$, thereby enabling the calculation of our adjusted metrics. 