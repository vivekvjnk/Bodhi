// --- 1. Create constraints for node uniqueness (run this part once) ---
CREATE CONSTRAINT IF NOT EXISTS FOR (n:DATASET) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:GENERIC) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:METHOD) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:TASK) REQUIRE n.id IS UNIQUE;

// --- 2. Create nodes ---
MERGE (n:METHOD {id: "HIGH-THROUGHPUT SCREENING (HTS)"}) SET n += {description: "A traditional experimental approach for identifying molecules with desired bioactivity, often characterized by a low hit rate and labor-intensive processes.", source_index: [0]};
MERGE (n:METHOD {id: "GXVAES"}) SET n += {description: "A novel deep generative model for computer-aided drug discovery that generates 'hit-like' molecules from gene expression profiles by leveraging two joint variational autoencoders (VAEs). ; A novel deep generative model for computer-aided drug discovery that generates 'hit-like' molecules from gene expression profiles by leveraging two joint variational autoencoders (VAEs): ProfileVAE and MolVAE. ; A novel deep generative model for computer-aided drug discovery that generates 'hit-like' molecules from gene expression profiles by leveraging two joint variational autoencoders (ProfileVAE and MolVAE).", source_index: [0, 1, 2]};
MERGE (n:METHOD {id: "PROFILEVAE"}) SET n += {description: "The first variational autoencoder (VAE) in GxVAEs, responsible for extracting latent features from gene expression profiles. ; One of the two joint VAEs in GxVAEs, responsible for extracting latent features from gene expression data. ; A component of GxVAEs that extracts latent features from gene expression data.", source_index: [0, 1, 2]};
MERGE (n:METHOD {id: "MOLVAE"}) SET n += {description: "The second variational autoencoder (VAE) in GxVAEs, which uses latent features from ProfileVAE as conditions to generate molecules. ; The second joint VAE in GxVAEs, which uses features extracted by ProfileVAE as conditions to generate molecules. ; A component of GxVAEs that generates molecules conditioned on features extracted by ProfileVAE.", source_index: [0, 1, 2]};
MERGE (n:TASK {id: "COMPUTER-AIDED DRUG DISCOVERY"}) SET n += {description: "The field of study focused on using computational methods to discover new drugs, which GxVAEs contributes to.", source_index: [0]};
MERGE (n:METHOD {id: "VARIATIONAL AUTOENCODERS (VAES)"}) SET n += {description: "A class of deep generative models used in GxVAEs for feature extraction and molecule generation.", source_index: [0]};
MERGE (n:GENERIC {id: "CELLULAR ENVIRONMENT"}) SET n += {description: "The biological context of a cell, which GxVAEs aims to bridge with molecular generation to produce biologically meaningful molecules.", source_index: [0]};
MERGE (n:GENERIC {id: "BIOACTIVITY"}) SET n += {description: "The ability of a molecule to produce a biological effect, a desired characteristic of 'hit-like' molecules.", source_index: [0]};
MERGE (n:GENERIC {id: "DRUG-LIKENESS"}) SET n += {description: "The degree to which a molecule possesses properties that make it suitable as a drug, a desired characteristic of 'hit-like' molecules.", source_index: [0]};
MERGE (n:METHOD {id: "DEEP GENERATIVE MODELS"}) SET n += {description: "A category of AI models, including GANs and VAEs, used to generate new data, such as molecules with specific properties.", source_index: [0]};
MERGE (n:DATASET {id: "LINCS L1000 DATABASE"}) SET n += {description: "A database used to collect chemically induced gene expression profiles, specifically profiles of MCF7 cell line treated with molecules.", source_index: [1]};
MERGE (n:DATASET {id: "CREEDS DATABASE"}) SET n += {description: "A database used to collect disease-specific gene expression profiles.", source_index: [1]};
MERGE (n:METHOD {id: "EXPRESSIONGAN"}) SET n += {description: "A state-of-the-art deep generative model that bridges systems biology and molecular design, but has limitations in molecule validity and reproducing known ligands.", source_index: [1]};
MERGE (n:METHOD {id: "TRI-OMPHE"}) SET n += {description: "A state-of-the-art deep generative model that calculates ligand-target interaction correlations and uses a VAE for molecule generation, but its VAE is not involved in the generation process.", source_index: [1]};
MERGE (n:METHOD {id: "DRAGONET"}) SET n += {description: "A baseline model used for comparison with GxVAEs, demonstrating GxVAEs' ability to generate molecules with therapeutic potential. ; A state-of-the-art model compared against GxVAEs for generating therapeutic molecules from patient gene expression profiles.", source_index: [1, 2]};
MERGE (n:GENERIC {id: "NON-CANONICAL SMILES"}) SET n += {description: "Variant SMILES strings used by MolVAE, conditioned on gene expression profile features for molecule generation.", source_index: [1]};
MERGE (n:METHOD {id: "TRIOMPHE"}) SET n += {description: "A baseline model used for comparison with GxVAEs, particularly in generating ligand-like molecules from gene expression profiles.", source_index: [2]};
MERGE (n:GENERIC {id: "UNIQUENESS"}) SET n += {description: "A metric used to evaluate the proportion of generated molecules that are unique within a generated set.", source_index: [2]};
MERGE (n:GENERIC {id: "NOVELTY"}) SET n += {description: "A metric used to evaluate the proportion of generated molecules that are not present in the training dataset.", source_index: [2]};
MERGE (n:GENERIC {id: "ATOPIC DERMATITIS"}) SET n += {description: "A disease for which GxVAEs generated candidate therapeutic molecules, showing structural similarity to approved drugs.", source_index: [2]};
MERGE (n:GENERIC {id: "GASTRIC CANCER"}) SET n += {description: "A disease for which GxVAEs generated candidate therapeutic molecules with structural features similar to known approved drugs.", source_index: [2]};
MERGE (n:GENERIC {id: "ALZHEIMER'S DISEASE"}) SET n += {description: "A disease for which GxVAEs generated candidate therapeutic molecules with structural features similar to known approved drugs.", source_index: [2]};
MERGE (n:DATASET {id: "GENE EXPRESSION PROFILES"}) SET n += {description: "Data reflecting cellular activity, used as input for ProfileVAE to extract latent features. ; Data reflecting cellular activity, used as input for ProfileVAE to extract features. ; Data reflecting cellular activity, used as input for GxVAEs to generate molecules.", source_index: [0, 1, 2]};
MERGE (n:GENERIC {id: "HIT-LIKE MOLECULES"}) SET n += {description: "Molecules with potential bioactivity and drug-likeness, the target output of GxVAEs.", source_index: [0, 1, 2]};
MERGE (n:DATASET:GENERIC {id: "SMILES STRINGS"}) SET n += {description: "Simplified Molecular Input Line Entry System strings, a common representation for molecules used in de novo molecular generation. ; A linear notation for describing the structure of chemical molecules, used by MolVAE for molecular generation. ; A string-based representation of molecular structures used in the GxVAEs model.", source_index: [0, 1, 2]};
MERGE (n:GENERIC {id: "VALIDITY"}) SET n += {description: "A metric evaluating the ratio of chemically valid molecules generated, verifiable using tools like RDKit. ; A metric used to evaluate the proportion of generated molecules that are chemically valid.", source_index: [1, 2]};
MERGE (n:GENERIC {id: "TANIMOTO COEFFICIENTS"}) SET n += {description: "Metrics used to measure structural similarity between generated molecules and known molecules. ; A measure of structural similarity used to evaluate the quality of generated molecules, comparing GxVAEs to baseline models.", source_index: [1, 2]};

// --- 3. Create relationships ---
MATCH (a:METHOD {id: "HIGH-THROUGHPUT SCREENING (HTS)"}), (b:GENERIC {id: "BIOACTIVITY"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "High-throughput screening (HTS) is used for identifying molecules with desired bioactivity.", source_index: [0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:TASK {id: "COMPUTER-AIDED DRUG DISCOVERY"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.25, description: "GxVAEs is a novel deep generative model for computer-aided drug discovery. ; GxVAEs is a novel deep generative model for computer-aided drug discovery. ; The study demonstrates that GxVAEs outperforms current state-of-the-art baselines for computer-aided drug discovery objectives. ; GxVAEs outperforms current state-of-the-art baselines for computer-aided drug discovery objectives.", source_index: [0, 0, 0, 0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "HIT-LIKE MOLECULES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 16.5, description: "GxVAEs generates hit-like molecules that show potential bioactivity and drug-likeness. ; GxVAEs is designed to generate 'hit-like' molecules. ; GxVAEs are designed to generate 'hit-like' molecules. ; GxVAEs is designed to generate hit-like molecules from gene expression profiles. ; GxVAEs is designed to generate hit-like molecules. ; GxVAEs generates hit-like molecules from gene expression profiles. ; GxVAEs is designed to generate 'hit-like' molecules from gene expression profiles. | The chemical structures of hit-like molecules generated by GxVAEs are similar to the structures of known ligands.", source_index: [0, 0, 0, 0, 1, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "GxVAEs generates 'hit-like' molecules from gene expression profiles. ; GxVAEs generate molecules that are biologically meaningful in the context of specific diseases using gene expression profiles. ; GxVAEs generates molecules from gene expression profiles for therapeutic generation. ; GxVAEs generates molecules from gene expression profiles. ; GxVAEs generate molecules from gene expression profiles. ; GxVAEs generates molecules from disease reversal profiles for therapeutic generation. ; GxVAEs generates hit-like molecules from gene expression profiles.", source_index: [0, 0, 1, 1, 2, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:METHOD {id: "VARIATIONAL AUTOENCODERS (VAES)"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.5, description: "GxVAEs leverages two joint variational autoencoders (VAEs). ; GxVAEs leverages two joint variational autoencoders (VAEs).", source_index: [0, 0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "CELLULAR ENVIRONMENT"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.0, description: "GxVAEs bridges the gap between molecular generation and the cellular environment. ; GxVAEs bridges the gap between molecular generation and the cellular environment, making produced molecules biologically meaningful.", source_index: [0, 0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:DATASET:GENERIC {id: "SMILES STRINGS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.333333333333333, description: "The text explicitly states that GxVAEs uses SMILES strings for de novo molecular generation. ; GxVAEs uses SMILES strings for de novo molecular generation. ; GxVAEs uses SMILES strings for molecular representation. ; GxVAEs uses SMILES strings as a data structure for de novo molecular generation.", source_index: [0, 0, 0, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:METHOD {id: "DEEP GENERATIVE MODELS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 10.0, description: "The text describes GxVAEs as a novel deep generative model. ; GxVAEs is described as a novel deep generative model.", source_index: [0, 0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "BIOACTIVITY"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.5, description: "GxVAEs generates hit-like molecules with potential bioactivity. ; GxVAEs generates hit-like molecules with potential bioactivity.", source_index: [0, 0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "DRUG-LIKENESS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.5, description: "GxVAEs generates hit-like molecules with potential drug-like properties. ; GxVAEs generates hit-like molecules with potential drug-likeness.", source_index: [0, 0]};
MATCH (a:METHOD {id: "GXVAES"}), (b:METHOD {id: "PROFILEVAE"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.5, description: "GxVAEs consist of two joint VAEs, including ProfileVAE. ; GxVAEs consists of two joint VAEs, including ProfileVAE.", source_index: [1, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:METHOD {id: "MOLVAE"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.5, description: "GxVAEs consist of two joint VAEs, including MolVAE. ; GxVAEs consists of two joint VAEs, including MolVAE.", source_index: [1, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:METHOD {id: "DRAGONET"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.25, description: "GxVAEs are compared against DRAGONET. ; GxVAEs is compared with DRAGONET for therapeutic molecular generation. ; The Tanimoto coefficients of molecules generated by GxVAEs are compared with those of DRAGONET. ; The Tanimoto coefficients of molecules generated by GxVAEs are compared with those of DRAGONET.", source_index: [1, 2, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "VALIDITY"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "The validity of GxVAEs is evaluated and compared to baselines. ; GxVAEs' performance is evaluated using metrics like Validity. ; The validity of GxVAEs is higher than TRIOMPHE.", source_index: [1, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "TANIMOTO COEFFICIENTS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.5, description: "GxVAEs' performance is evaluated using metrics like Tanimoto Coefficients. ; The Tanimoto coefficients of molecules generated by GxVAEs are evaluated and compared to baselines. ; The Tanimoto coefficients of molecules generated by GxVAEs are higher than those of baseline models. ; Tanimoto coefficients are calculated for molecules generated by GxVAEs relative to known approved drugs.", source_index: [1, 2, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:METHOD {id: "TRIOMPHE"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "GxVAEs is compared to the TRIOMPHE baseline for generating molecules.", source_index: [2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "UNIQUENESS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "The uniqueness of GxVAEs exceeds that of TRIOMPHE for most cases. ; The uniqueness of GxVAEs is evaluated and compared to baselines.", source_index: [2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "NOVELTY"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 6.5, description: "The novelty of GxVAEs is close to that of TRIOMPHE. ; The novelty of GxVAEs is evaluated and compared to baselines.", source_index: [2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "ATOPIC DERMATITIS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.25, description: "GxVAEs generates candidate therapeutic molecules for atopic dermatitis. ; GxVAEs generates therapeutic molecules from disease reversal profiles. ; GxVAEs generates therapeutic molecules from disease reversal profiles for specific diseases. ; GxVAEs generates molecules for treating atopic dermatitis.", source_index: [2, 2, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "GASTRIC CANCER"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.25, description: "GxVAEs generates candidate therapeutic molecules for gastric cancer. ; GxVAEs generates therapeutic molecules from disease reversal profiles. ; GxVAEs generates therapeutic molecules from disease reversal profiles for specific diseases. ; GxVAEs generates molecules for treating gastric cancer.", source_index: [2, 2, 2, 2]};
MATCH (a:METHOD {id: "GXVAES"}), (b:GENERIC {id: "ALZHEIMER'S DISEASE"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.25, description: "GxVAEs generates candidate therapeutic molecules for Alzheimer's disease. ; GxVAEs generates therapeutic molecules from disease reversal profiles. ; GxVAEs generates therapeutic molecules from disease reversal profiles for specific diseases. ; GxVAEs generates molecules for treating Alzheimer's disease.", source_index: [2, 2, 2, 2]};
MATCH (a:METHOD {id: "PROFILEVAE"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.5, description: "ProfileVAE extracts features from gene expression profiles. ; ProfileVAE extracts latent features from gene expression profiles.", source_index: [0, 0, 1, 2, 2]};
MATCH (a:METHOD {id: "PROFILEVAE"}), (b:METHOD {id: "VARIATIONAL AUTOENCODERS (VAES)"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "ProfileVAE is a variational autoencoder (VAE) within GxVAEs.", source_index: [0]};
MATCH (a:METHOD {id: "PROFILEVAE"}), (b:METHOD {id: "MOLVAE"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 17.0, description: "ProfileVAE extracts features that serve as conditions for MolVAE. | MolVAE uses latent features extracted by ProfileVAE as conditions. ; MolVAE uses the features extracted by ProfileVAE as conditions to generate molecules. ; MolVAE uses features from ProfileVAE to generate hit-like molecules.", source_index: [0]};
MATCH (a:METHOD {id: "MOLVAE"}), (b:GENERIC {id: "HIT-LIKE MOLECULES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "MolVAE generates hit-like molecules using features extracted from gene expression profiles as conditions. ; MolVAE uses features extracted from gene expression profiles to generate hit-like molecules. ; MolVAE generates hit-like molecules using features from ProfileVAE. ; MolVAE, guided by features from ProfileVAE, generates hit-like molecules. ; MolVAE generates hit-like molecules using latent features from ProfileVAE as conditions. ; MolVAE is guided to produce hit-like molecules using features from ProfileVAE.", source_index: [0, 0, 0, 2, 2, 2]};
MATCH (a:METHOD {id: "MOLVAE"}), (b:METHOD {id: "VARIATIONAL AUTOENCODERS (VAES)"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "MolVAE is a variational autoencoder (VAE) within GxVAEs.", source_index: [0]};
MATCH (a:METHOD {id: "MOLVAE"}), (b:DATASET:GENERIC {id: "SMILES STRINGS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "MolVAE generates molecules using SMILES strings.", source_index: [1]};
MATCH (a:METHOD {id: "MOLVAE"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "MolVAE is conditioned on features of gene expression profiles.", source_index: [1]};
MATCH (a:METHOD {id: "MOLVAE"}), (b:GENERIC {id: "NON-CANONICAL SMILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 9.0, description: "MolVAE uses non-canonical SMILES strings conditioned on gene expression profile features. ; MolVAE uses non-canonical SMILES strings conditioned on gene expression profile features for molecule generation.", source_index: [1, 1]};
MATCH (a:TASK {id: "COMPUTER-AIDED DRUG DISCOVERY"}), (b:METHOD {id: "DEEP GENERATIVE MODELS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "Deep generative models are used in computer-aided drug discovery.", source_index: [0]};
MATCH (a:METHOD {id: "VARIATIONAL AUTOENCODERS (VAES)"}), (b:METHOD {id: "DEEP GENERATIVE MODELS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 18.5, description: "Variational Autoencoders (VAEs) are a type of deep generative model. | Variational Autoencoders (VAEs) are a type of deep generative model. ; Variational Autoencoders (VAEs) are a type of deep generative model used in molecular generation.", source_index: [0]};
MATCH (a:GENERIC {id: "CELLULAR ENVIRONMENT"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "Gene expression profiles reflect the cellular environment.", source_index: [0]};
MATCH (a:GENERIC {id: "BIOACTIVITY"}), (b:GENERIC {id: "HIT-LIKE MOLECULES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.0, description: "Hit-like molecules are characterized by potential bioactivity.", source_index: [0]};
MATCH (a:GENERIC {id: "DRUG-LIKENESS"}), (b:GENERIC {id: "HIT-LIKE MOLECULES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.0, description: "Hit-like molecules are characterized by potential drug-likeness.", source_index: [0]};
MATCH (a:DATASET {id: "LINCS L1000 DATABASE"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.0, description: "Chemically induced gene expression profiles were collected from the LINCS L1000 database.", source_index: [1]};
MATCH (a:DATASET {id: "CREEDS DATABASE"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.0, description: "Disease-specific gene expression profiles were collected from the CREEDS database.", source_index: [1]};
MATCH (a:METHOD {id: "EXPRESSIONGAN"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 8.0, description: "ExpressionGAN produces molecules from gene expression profiles.", source_index: [1]};
MATCH (a:METHOD {id: "TRI-OMPHE"}), (b:DATASET {id: "GENE EXPRESSION PROFILES"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 7.0, description: "TRI-OMPHE uses gene expression profiles in correlation calculations.", source_index: [1]};
MATCH (a:METHOD {id: "DRAGONET"}), (b:GENERIC {id: "TANIMOTO COEFFICIENTS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 13.0, description: "Tanimoto coefficients are calculated for molecules generated by DRAGONET relative to known approved drugs. | The Tanimoto coefficients of molecules generated by GxVAEs are compared with those of DRAGONET.", source_index: [2]};
MATCH (a:GENERIC {id: "HIT-LIKE MOLECULES"}), (b:DATASET:GENERIC {id: "SMILES STRINGS"})
MERGE (a)-[r:RELATED_TO]->(b) SET r += {weight: 11.0, description: "SMILES strings are used for de novo molecular generation, aiming for hit-like molecules. | The chemical structures of hit-like molecules generated by GxVAEs are represented and compared.", source_index: [0]};