Replicate the paper to generate verifiable and diverse function-calling datasets

# APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets  
**Zuxin Liu, Thai Hoang, Jianguo Zhang, Ming Zhu, Tian Lan, Shirley Kokane, Juntao Tan, Weiran Yao, Zhiwei Liu, Yihao Feng, Rithesh Murthy, Liangwei Yang, Silvio Savarese, Juan Carlos Niebles, Huan Wang, Shelby Heinecke, Caiming Xiong**  
Salesforce AI Research, USA  
{zuxin.liu, thai.hoang, jianguozhang}@salesforce.com  

## Abstract  
APIGen is an automated pipeline for generating high-quality, verified function-calling datasets. It leverages **3,673 executable APIs** (3,539 REST APIs from ToolBench and 134 Python functions) across **21 categories**, ensuring diversity through structured JSON formatting, **multi-stage verification** (format, execution, semantic checks), and randomized sampling. Models trained with APIGen's **60,000-entry dataset** achieve state-of-the-art performance: the **7B-parameter model** ranks 3rd (88.24% accuracy) on the Berkeley Function-Calling Leaderboard (BFCL), while the **1B model** surpasses GPT-3.5-Turbo. The dataset is publicly available on [Huggingface](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) and the [project homepage](https://apigen-pipeline.github.io/).

---

## 1. Introduction  
Function-calling agents enable LLMs to execute API calls based on natural language instructions (e.g., `get_weather("Palo Alto")`). However, existing datasets are static and lack verification. APIGen addresses this by:  
- Generating **diverse, verified datasets** through LLM-driven synthesis.  
- Implementing **three-stage verification** to ensure data quality.  
- Supporting **parallel/multiple function calls** and complex scenarios.  

**Key Contributions**:  
- APIGen framework for scalable, verifiable dataset generation.  
- Two trained models: **xLAM-7B (FC)** (6th on BFCL) and **xLAM-1B (FC)** (outperforms GPT-3.5-Turbo).  
- Public release of **60,000 high-quality entries**.  

---