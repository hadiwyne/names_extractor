# Author Mention Extractor - Jupyter Notebook

This Jupyter notebook provides a solution for extracting and analyzing author mentions from literary works. Inspired by Maurice Blanchot's "The Space of Literature," this tool helps readers identify influential authors mentioned in books and analyze their relative importance based on mention frequency.

## Features

- **Text Extraction**: Supports PDF, EPUB, and TXT file formats
- **Natural Language Processing**: Uses spaCy's advanced NLP capabilities
- **Author Identification**: Detects author mentions through:
  - Named Entity Recognition (PERSON entities)
  - Contextual pattern matching
  - Stopword filtering
- **Analysis & Visualization**: 
  - Counts author mentions
  - Sorts authors by frequency
  - Filters out common false positives
- **Export Capabilities**: Generates Excel files with results

## How It Works

The notebook follows this workflow:
1. Loads a book file (PDF, EPUB, or TXT)
2. Cleans and preprocesses the text
3. Extracts author names using:
   - spaCy's named entity recognition
   - Contextual patterns (e.g., "according to [Author]")
4. Counts and sorts author mentions
5. Filters out common non-author terms
6. Exports results to an Excel file

## Requirements

To run this notebook, you'll need:

- Python 3.7+
- Required libraries:
  ```bash
  pip install spacy pandas tika matplotlib
  ```
- spaCy English model:
  ```bash
  python -m spacy download en_core_web_md
  ```
- Java Runtime Environment (for Tika PDF/EPUB processing)

## Usage

1. Upload your book file (PDF, EPUB, or TXT) to the same directory as the notebook
2. Update the `file_path` variable in the "Main Processing" section with your filename
3. Run all cells sequentially
4. Find results in the generated `authors.xlsx` file

## Sample Output

The Excel file contains two columns:
- `Author`: Name of the identified author
- `Mentions`: Number of times the author was mentioned

Example output:

| Author            | Mentions |
|-------------------|----------|
| Franz Kafka       | 115    |
| Rainer Maria Rilke| 8    |
| Maurice Blanchot  | 3     |

## Customization

You can modify:
- `common_non_authors` set: Add/remove terms to filter
- Mention threshold: Change `df['Mentions'] > 1` to adjust minimum mentions
- Patterns: Modify the regex patterns in `extract_authors()` for different contextual clues

## Limitations

- Primarily detects Western author names
- May miss authors mentioned with only first or last names
- Might include some false positives (always review results)
- Performance may vary with non-English texts

## Future Enhancements

Potential improvements:
- Add multi-language support
- Implement author alias mapping
- Include visualization of results
- Add fuzzy matching for name variations
- Create interactive web interface

## Inspiration

This project was inspired by reading Maurice Blanchot's "The Space of Literature," where the author references numerous influential writers whose names I wanted to systematically catalog and explore further.
