import yaml
import re


def isolate_references_section(text: str):
    """
    Isolates the references section from a text document based on Markdown-style
    bolded headings.

    Args:
        text: The input text document as a single string.

    Returns:
        A tuple containing two strings:
        - The text document without the references section.
        - The isolated references section, including its title.
        If no references section is found, the first string is the original text
        and the second is an empty string.
    """
    # references_pattern = re.compile(
    #                                 r'(?:'
    #                                 r'\*\*(?:References|Bibliography|Works Cited)\*\*'        # **References**
    #                                 r'|#+\s*(?:References|Bibliography|Works Cited)'          # # References
    #                                 r'|\bR[\s\\]+EFERENCES\*\*\s*$'                                # R EFERENCES
    #                                 r'|\bR[\s\\]*E[\s\\]*F[\s\\]*E[\s\\]*R[\s\\]*E[\s\\]*N[\s\\]*C[\s\\]*E[\s\\]*S\b'  # R E F E R E N C E S (with spaces, \, newlines)
    #                                 r'|\n\s*\*\*(?:References|Bibliography|Works Cited)\*\*\s*(?=\n|$)'             # plain form
    #                                 r'|\*\*R\*\*[\s\\]*\*\*EFERENCES\*\*'                      # **R** **EFERENCES** (with spaces, \, or newlines)
    #                                 r')',
    #                                 re.IGNORECASE | re.MULTILINE
    #                             )
    # references_pattern = re.compile(
    # r'(?:'
    # r'(?:^|\n)\s*\*\*(?:References|Bibliography|Works Cited)\*\*\s*(?:\n|$)'                # **References**
    # r'|(?:^|\n)\s*#+\s*(?:References|Bibliography|Works Cited)\s*(?:\n|$)'                  # # References
    # r'|(?:^|\n)\s*R[\s\\]+EFERENCES\*\*\s*(?:\n|$)'                                         # R EFERENCES
    # r'|(?:^|\n)\s*R[\s\\]*E[\s\\]*F[\s\\]*E[\s\\]*R[\s\\]*E[\s\\]*N[\s\\]*C[\s\\]*E[\s\\]*S\s*(?:\n|$)'  # R E F E R E N C E S
    # r'|(?:^|\n)\s*\*\*(?:References|Bibliography|Works Cited)\*\*\s*(?=\n|$)'               # plain form
    # r'|(?:^|\n)\s*\*\*R\*\*[\s\\]*\*\*EFERENCES\*\*\s*(?:\n|$)'                             # **R** **EFERENCES**
    # r')',
    # re.IGNORECASE | re.MULTILINE
    # )
    references_pattern = re.compile(
    r'(?:'
    r'(?:^|\n\s*)\*\*(?:References|Bibliography|Works Cited)\*\*(?:\s*\n|$)'                # **References**
    r'|(?:^|\n\s*)#+\s*\**\s*(?:References|Bibliography|Works Cited)\**\s*(?:\s*\n|$)'      # ### **References**
    r'|(?:^|\n\s*)R[\s\\]+EFERENCES\*\*(?:\s*\n|$)'                                         # R EFERENCES
    r'|(?:^|\n\s*)R[\s\\]*E[\s\\]*F[\s\\]*E[\s\\]*R[\s\\]*E[\s\\]*N[\s\\]*C[\s\\]*E[\s\\]*S(?:\s*\n|$)'  # R E F E R E N C E S
    r'|(?:^|\n\s*)\*\*(?:References|Bibliography|Works Cited)\*\*(?=\s*\n|$)'               # plain form
    r'|(?:^|\n\s*)\*\*R\*\*[\s\\]*\*\*EFERENCES\*\*(?:\s*\n|$)'                             # **R** **EFERENCES**
    r')',
    re.IGNORECASE | re.MULTILINE
    )

    

    references_match = references_pattern.search(text)
    results = {"text": text,"references":""}
    if references_match:
        references_start = references_match.start()
        
        next_section_pattern = re.compile(r'\n\s*(?:#+\s+.*|\*\*.*\*\*)')
        # next_section_pattern = re.compile(r'\n\s*\*\*.*\*\*') 
        next_section_match = next_section_pattern.search(text, references_match.end())

        document_before_refs = text[:references_start]

        if next_section_match:
            references_end = next_section_match.start()
            document_after_refs = text[references_end:]
            
            # --- FIX START ---
            # Directly concatenate the parts before and after the references.
            # This is the most reliable way to remove the middle section.
            main_text = document_before_refs +"\n\n---References section begin---\n\n---References section end---\n\n"+ document_after_refs
            references_text = text[references_start:references_end]
            # --- FIX END ---

        else:
            # If no next section is found, the references run to the end of the document.
            main_text = document_before_refs
            references_text = text[references_start:]

        # Strip the final results for clean output.
        results = {"text": main_text.strip(),"references":references_text.strip()}
    
    return results


# Example Usage:

if __name__ == "__main__":
    # Sample text representing an extracted PDF document.
    sample_document = """
    # This is a Sample Research Paper

    **1. Introduction**
    This is the introduction section. It provides a brief overview of the research topic and its significance. We cite some important works here [1, 2].

    **2. Methods**
    Here we describe the methodology used in the study. We used a novel approach to gather data and analyze it. This section is quite detailed.

    **3. Results**
    Our key findings are presented here. This is a very important part of the paper.

    **4. Discussion**
    We discuss the implications of our results and suggest future research directions.

    **References**
    [1] Author, A. (2020). *Title of the First Paper*. Journal of Important Studies.
    [2] Baker, B. (2019). *Another Crucial Work*. Academic Review.
    [3] Chan, C. (2021). *A Recent Finding*. Journal of Discovery.
    [4] Davis, D. (2018). *Old but Gold*. Classic Articles.
    [5] Evans, E. (2020). *Breakthrough in Science*. Breakthroughs Journal.\n\
    ### **5.Appendix**
    This is an optional section with supplementary information.
    """

    # Call the function with the sample document.
    document_without_refs, extracted_refs = isolate_references_section(sample_document)

    # Print the results.
    print("--- Document Without References ---")
    print(document_without_refs)
    print("\n" + "="*50 + "\n")
    print("--- Extracted References Section ---")
    print(extracted_refs)