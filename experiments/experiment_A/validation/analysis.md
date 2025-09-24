# Coverage output analysis across samples 
Total of 48 experiments were carried out 
Experiment : One complete run of Bodhi pipeline
Variables : Token limit, Allowance for Generic type, Allowance of priming summary
- Token limit : 
    - 4 ablations, 250 tokens, 500 tokens, 750 tokens and 1000 tokens
    - Token limit applies to the source text unit size. Text units are built from the source document with the token limit
    - As token limit decrease, granularity of each extraction would increase
    - As token limit decrease, capturing long distance relationships would become hard
    - Each experiment is classified at top level based on token limit. This parameter is changed by changing `token_limit` in config.yml
    - Complete downstream bodhi pipeline uses the text units for graph extraction. Hence ablations in token limit is applied at top level
- Generic type and priming summary
    - Generic types
        - Bodhi allows to extract entities which doesn't belong to any of the defined entity types. They will be allocated with "generic" type
    - Priming summary
        - Before starting the graph extraction pipeline, first 2000 tokens of the source document is passed to an LLM for summarization. Instruction is to prepare priming summary for a knowledge graph extraction system.
        - Priming summary is used during entity extraction, relationship extraction etc. 
        - This helps the system to align well with the domain of interest 
        - Reduces generic entity extractions
    - Dedicated versions of prompts and Bodhi module are prepared for these ablations <br>
Total of 4 ablation experiments were planned<br>

|                | With Priming Summary | Without Priming Summary |
|----------------|-------------------------|-------------------------|
| **Without Generic Type**   |  experiment A1                       |       experiment A2                  |
| **With Generic Type**  |   experiment A3                      |       experiment A4                  |

- Each experiment is repeated 3 times. Since Bodhi relies on LLM for entity/relationship extraction, outcomes are not deterministic. Hence we repeat experiments 3 times to see the variance in system behaviour
    - Each sample represent experiment repetitions

## Token 250
### Sample 1 
A1: {'total_gold': 53, 'direct': 9, 'fuzzy_candidates': 12, 'missed': 32, 'coverage_pct': 39.62264150943396}
- Number of nodes: 46, edges: 83

A2: {'total_gold': 53, 'direct': 25, 'fuzzy_candidates': 10, 'missed': 18, 'coverage_pct': 66.0377358490566}
- Number of nodes: 76, edges: 135

A3: {'total_gold': 53, 'direct': 17, 'fuzzy_candidates': 16, 'missed': 20, 'coverage_pct': 62.264150943396224}
- Number of nodes: 69, edges: 131

A4: {'total_gold': 53, 'direct': 28, 'fuzzy_candidates': 11, 'missed': 14, 'coverage_pct': 73.58490566037736}
- Number of nodes: 131, edges: 171

### Sample 2 
A1: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 14, 'missed': 21, 'coverage_pct': 60.37735849056604}
- Number of nodes: 63, edges: 118

A2: {'total_gold': 53, 'direct': 24, 'fuzzy_candidates': 9, 'missed': 20, 'coverage_pct': 62.264150943396224}
- Number of nodes: 93, edges: 133

A3: {'total_gold': 53, 'direct': 25, 'fuzzy_candidates': 13, 'missed': 15, 'coverage_pct': 71.69811320754717}
- Number of nodes: 110, edges: 157

A4: {'total_gold': 53, 'direct': 35, 'fuzzy_candidates': 10, 'missed': 8, 'coverage_pct': 84.90566037735849}
- Number of nodes: 133, edges: 195

### Sample 3
A1: {'total_gold': 53, 'direct': 21, 'fuzzy_candidates': 13, 'missed': 19, 'coverage_pct': 64.15094339622641}
- Number of nodes: 65, edges: 95

A2: {'total_gold': 53, 'direct': 22, 'fuzzy_candidates': 12, 'missed': 19, 'coverage_pct': 64.15094339622641}
- Number of nodes: 92, edges: 123

A3: {'total_gold': 53, 'direct': 23, 'fuzzy_candidates': 14, 'missed': 16, 'coverage_pct': 69.81132075471697}
- Number of nodes: 105, edges: 161

A4: {'total_gold': 53, 'direct': 30, 'fuzzy_candidates': 13, 'missed': 10, 'coverage_pct': 81.13207547169812}
- Number of nodes: 150, edges: 191

## Token 500
### Sample 1 
A1: {'total_gold': 53, 'direct': 15, 'fuzzy_candidates': 13, 'missed': 25, 'coverage_pct': 52.83018867924528} 
- Number of nodes: 37, edges: 60

A2: {'total_gold': 53, 'direct': 23, 'fuzzy_candidates': 13, 'missed': 17, 'coverage_pct': 67.9245283018868}
- Number of nodes: 75, edges: 99

A3: {'total_gold': 53, 'direct': 14, 'fuzzy_candidates': 16, 'missed': 23, 'coverage_pct': 56.60377358490566}
- Number of nodes: 53, edges: 77

A4: {'total_gold': 53, 'direct': 21, 'fuzzy_candidates': 14, 'missed': 18, 'coverage_pct': 66.0377358490566}
- Number of nodes: 82, edges: 101

### Sample 2 
A1: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 11, 'missed': 24, 'coverage_pct': 54.71698113207547}
- Number of nodes: 51, edges: 73

A2: {'total_gold': 53, 'direct': 15, 'fuzzy_candidates': 14, 'missed': 24, 'coverage_pct': 54.71698113207547}
- Number of nodes: 52, edges: 76

A3: {'total_gold': 53, 'direct': 16, 'fuzzy_candidates': 10, 'missed': 27, 'coverage_pct': 49.056603773584904}
- Number of nodes: 55, edges: 74

A4: {'total_gold': 53, 'direct': 23, 'fuzzy_candidates': 14, 'missed': 16, 'coverage_pct': 69.81132075471697}
- Number of nodes: 80, edges: 103

### Sample 3
A1: {'total_gold': 53, 'direct': 15, 'fuzzy_candidates': 13, 'missed': 25, 'coverage_pct': 52.83018867924528}
- Number of nodes: 34, edges: 51

A2: {'total_gold': 53, 'direct': 20, 'fuzzy_candidates': 14, 'missed': 19, 'coverage_pct': 64.15094339622641}
- Number of nodes: 78, edges: 107

A3: {'total_gold': 53, 'direct': 19, 'fuzzy_candidates': 11, 'missed': 23, 'coverage_pct': 56.60377358490566}
- Number of nodes: 54, edges: 86

A4: {'total_gold': 53, 'direct': 22, 'fuzzy_candidates': 13, 'missed': 18, 'coverage_pct': 66.0377358490566}
- Number of nodes: 77, edges: 110

## Token 750
### Sample 1 
A1: {'total_gold': 53, 'direct': 10, 'fuzzy_candidates': 10, 'missed': 33, 'coverage_pct': 37.735849056603776}
- Number of nodes: 26, edges: 60

A2: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 13, 'missed': 22, 'coverage_pct': 58.490566037735846}
- Number of nodes: 61, edges: 87

A3: {'total_gold': 53, 'direct': 15, 'fuzzy_candidates': 11, 'missed': 27, 'coverage_pct': 49.056603773584904}
- Number of nodes: 48, edges: 79

A4: {'total_gold': 53, 'direct': 22, 'fuzzy_candidates': 14, 'missed': 17, 'coverage_pct': 67.9245283018868}
- Number of nodes: 62, edges: 103

### Sample 2 
A1: {'total_gold': 53, 'direct': 7, 'fuzzy_candidates': 12, 'missed': 34, 'coverage_pct': 35.84905660377358}
- Number of nodes: 17, edges: 26

A2: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 13, 'missed': 22, 'coverage_pct': 58.490566037735846}
- Number of nodes: 60, edges: 81

A3: {'total_gold': 53, 'direct': 14, 'fuzzy_candidates': 10, 'missed': 29, 'coverage_pct': 45.28301886792453}
- Number of nodes: 53, edges: 57

A4: {'total_gold': 53, 'direct': 19, 'fuzzy_candidates': 16, 'missed': 18, 'coverage_pct': 66.0377358490566}
- Number of nodes: 64, edges: 88

### Sample 3
A1: {'total_gold': 53, 'direct': 14, 'fuzzy_candidates': 13, 'missed': 26, 'coverage_pct': 50.943396226415096}
- Number of nodes: 38, edges: 72

A2: {'total_gold': 53, 'direct': 17, 'fuzzy_candidates': 16, 'missed': 20, 'coverage_pct': 62.264150943396224}
- Number of nodes: 58, edges: 84

A3: {'total_gold': 53, 'direct': 15, 'fuzzy_candidates': 13, 'missed': 25, 'coverage_pct': 52.83018867924528}
- Number of nodes: 61, edges: 81

A4: {'total_gold': 53, 'direct': 21, 'fuzzy_candidates': 15, 'missed': 17, 'coverage_pct': 67.9245283018868}
- Number of nodes: 75, edges: 77

## Token 1000
### Sample 1 
A1: {'total_gold': 53, 'direct': 13, 'fuzzy_candidates': 9, 'missed': 31, 'coverage_pct': 41.509433962264154}
- Number of nodes: 38, edges: 58

A2: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 14, 'missed': 21, 'coverage_pct': 60.37735849056604}
- Number of nodes: 31, edges: 51

A3: {'total_gold': 53, 'direct': 12, 'fuzzy_candidates': 15, 'missed': 26, 'coverage_pct': 50.943396226415096}
- Number of nodes: 32, edges: 52

A4: {'total_gold': 53, 'direct': 17, 'fuzzy_candidates': 14, 'missed': 22, 'coverage_pct': 58.490566037735846}
- Number of nodes: 52, edges: 72

### Sample 2 
A1: {'total_gold': 53, 'direct': 14, 'fuzzy_candidates': 13, 'missed': 26, 'coverage_pct': 50.943396226415096}
- Number of nodes: 28, edges: 59

A2: {'total_gold': 53, 'direct': 15, 'fuzzy_candidates': 15, 'missed': 23, 'coverage_pct': 56.60377358490566}
- Number of nodes: 48, edges: 64

A3: {'total_gold': 53, 'direct': 8, 'fuzzy_candidates': 12, 'missed': 33, 'coverage_pct': 37.735849056603776}
- Number of nodes: 42, edges: 59

A4: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 13, 'missed': 22, 'coverage_pct': 58.490566037735846}
- Number of nodes: 63, edges: 70

### Sample 3
A1: {'total_gold': 53, 'direct': 16, 'fuzzy_candidates': 12, 'missed': 25, 'coverage_pct': 52.83018867924528} 
- Number of nodes: 41, edges: 48

A2: {'total_gold': 53, 'direct': 18, 'fuzzy_candidates': 13, 'missed': 22, 'coverage_pct': 58.490566037735846}
- Number of nodes: 50, edges: 97

A3: {'total_gold': 53, 'direct': 14, 'fuzzy_candidates': 13, 'missed': 26, 'coverage_pct': 50.943396226415096}
- Number of nodes: 44, edges: 61

A4: {'total_gold': 53, 'direct': 19, 'fuzzy_candidates': 13, 'missed': 21, 'coverage_pct': 60.37735849056604}
- Number of nodes: 60, edges: 80

