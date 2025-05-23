
# APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets  
**Zuxin Liu, Thai Hoang, Jianguo Zhang, Ming Zhu, Tian Lan, Shirley Kokane, Juntao Tan, Weiran Yao, Zhiwei Liu, Yihao Feng, Rithesh Murthy, Liangwei Yang, Silvio Savarese, Juan Carlos Niebles, Huan Wang, Shelby Heinecke, Caiming Xiong**  
Salesforce AI Research, USA  
{zuxin.liu, thai.hoang, jianguozhang}@salesforce.com  

---

## Abstract  
APIGen is an automated pipeline for generating high-quality, verified function-calling datasets. It leverages **3,673 executable APIs** (3,539 REST APIs from ToolBench and 134 Python functions) across **21 categories**, ensuring diversity through structured JSON formatting, **multi-stage verification** (format, execution, semantic checks), and randomized sampling. Models trained with APIGen’s **60,000-entry dataset** achieve state-of-the-art performance: the **7B-parameter model** ranks 3rd (88.24% accuracy) on the Berkeley Function-Calling Leaderboard (BFCL), while the **1B model** surpasses GPT-3.5-Turbo. The dataset is publicly available on [Huggingface](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) and the [project homepage](https://apigen-pipeline.github.io/).

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

## 2. APIGen Framework  
### 2.1 Data Generation  
1. **Sampling**: APIs and seed QA pairs are sampled from libraries.  
2. **Prompt Templates**: Steer LLMs to generate query-answer pairs in JSON format.  
3. **Multi-Stage Verification**:  
   - **Stage 1 (Format Checker)**: Validates JSON structure and required fields.  
   - **Stage 2 (Execution Checker)**: Executes function calls and checks for errors.  
   - **Stage 3 (Semantic Checker)**: LLM evaluates alignment between query intent and execution results.  

**JSON Advantages**:  
- Structural verification of fields.  
- Scalable integration of REST APIs/Python functions.  

### 2.2 Dataset Diversity  
- **Query Styles**: Simple, Multiple, Parallel, Parallel-Multiple.  
- **Sampling Strategies**: API Sampler, Example Sampler, Prompt Sampler.  
- **API Sources**: 21 consolidated categories (e.g., Technology, Finance).  

---

## 3. Dataset Preparation  
### 3.1 API Sources  
- **ToolBench**: 16,464 REST APIs filtered to **3,539** executable APIs.  
- **Python Functions**: 134 functions (math, finance, data management).  

**Filtering Steps**:  
- Remove APIs with poor documentation or no parameters.  
- Test API accessibility via endpoint requests.  
- Regenerate noisy docstrings.  

### 3.2 Collection Setup  
| **Model**                | Verified Data | Pass Rate |  
|--------------------------|---------------|-----------|  
| DeepSeek-V2-Chat (236B)  | 33,659        | 84.15%    |  
| Mixtral-8x22B-Inst       | 26,384        | 65.96%    |  
| Mixtral-8x7B-Inst        | 15,385        | 38.46%    |  

---

## 4. Experiments  
### 4.1 Benchmark Results (BFCL)  
| **Model**            | Overall Accuracy | Rank |  
|----------------------|------------------|------|  
| xLAM-7B (FC)         | 88.68%           | 6th  |  
| GPT-4-0125-Preview   | 88.26%           | 1st  |  
| xLAM-1B (FC)         | 74.41%           | 24th |  
| GPT-3.5-Turbo-0125   | 63.88%           | 33rd |  

**Key Findings**:  
- APIGen-trained models excel in **parallel/multiple function calls**.  
- Smaller models (1B) outperform larger ones (e.g., Claude-3 Haiku).  

### 4.2 Ablation Study  
Including low-quality data (filtered by Stage 2/3) degrades performance:  
- xLAM-1B accuracy drops by **12%**.  

---

## 5. Conclusion  
APIGen enables **small models** to rival larger ones in function-calling tasks through high-quality data. Future work includes support for multi-turn interactions and additional API types.  

---

## Appendix  
### A. Dataset Examples  
**Simple Query**:  
```json  
{  
  "query": "What is the weather in Palo Alto?",  
  "tools": [{  
    "name": "weather_api.get_current_weather",  
    "parameters": {"location": "string"}  
  }],  
  "answers": [{  
    "name": "weather_api.get_current_weather",  
    "arguments": {"location": "Palo Alto"}  
  }]  
}  
```  

**Parallel Query**:  
```json  
{  
  "query": "Sum multiples of 3 and 5 below 1000. Product of first 5 primes.",  
  "tools": ["math_toolkit.sum_of_multiples", "math_toolkit.product_of_primes"],  
  "answers": [  
    {"name": "sum_of_multiples", "arguments": {"multiples": [3,5]}},  
    {"name": "product_of_primes", "arguments": {"count": 5}}  
  ]  
}  
```  

### B. Training Details  
- **Hyperparameters**: Learning rate = 5e-6, 4 epochs, AdamW optimizer.  
- **Hardware**: 8× NVIDIA A100 40GB GPUs.  
- **Prompt Template**: Combines task instructions, available tools, and format constraints.  

---  
**License**: CC BY 4.0.  
**Dataset Link**: [Huggingface](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k)  
```