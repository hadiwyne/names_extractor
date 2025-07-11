import streamlit as st
import os
os.environ['JAVA_HOME'] = '/usr/lib/jvm/java-11-openjdk-amd64'
import re
import spacy
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from tika import parser
from spacy.lang.en.stop_words import STOP_WORDS

# Initialize NLP model
@st.cache_resource
def load_nlp_model():
    try:
        return spacy.load('en_core_web_sm')
    except OSError:
        import spacy.cli
        spacy.cli.download('en_core_web_sm')
        return spacy.load('en_core_web_sm'))

def load_text(file_path):
    ext = os.path.splitext(file_path.name)[1].lower()
    
    if ext == ".pdf":
        return parser.from_buffer(file_path.read())['content']
    elif ext == ".txt":
        return file_path.read().decode("utf-8")
    elif ext == ".epub":
        # Use in-memory processing for EPUB
        return parser.from_buffer(file_path.read())['content']  # Changed this line
    else:
        raise ValueError("Unsupported file format")

def clean_text(text):
    """Clean and normalize text"""
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_authors(text, nlp):
    """Extract author names from text"""
    doc = nlp(text)
    authors = []
    
    # 1. Extract PERSON entities
    for ent in doc.ents:
        if ent.label_ == 'PERSON' and ent.text.istitle():
            if len(ent.text.split()) == 1:
                if ent.text.lower() not in STOP_WORDS:
                    authors.append(ent.text)
            else:
                authors.append(ent.text)
    
    # 2. Contextual patterns
    patterns = [
        r'(?:according to|by|writes|stated by|argued by|noted by|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\'s (?:work|book|essay|theory))'
    ]
    for pattern in patterns:
        authors += re.findall(pattern, text)
    
    return authors

# Streamlit app
st.title("📚 Author Names Extractor")
st.markdown("Upload a book (PDF, EPUB, TXT) to extract mentioned authors")

# File upload
uploaded_file = st.file_uploader("Choose a file", type=["pdf", "epub", "txt"])
min_mentions = st.slider("Minimum mentions threshold", 1, 20, 3)

if uploaded_file is not None:
    with st.spinner("Processing your document..."):
        # Load NLP model
        nlp = load_nlp_model()
        
        # Process file
        try:
            raw_text = load_text(uploaded_file)
            cleaned_text = clean_text(raw_text)
            
            # Extract authors
            author_list = extract_authors(cleaned_text, nlp)
            author_counts = Counter(author_list)
            
            if author_counts:
                # Create DataFrame
                df = pd.DataFrame(author_counts.items(), columns=['Author', 'Mentions'])
                df = df[df['Mentions'] >= min_mentions]
                df.sort_values('Mentions', ascending=False, inplace=True)
                
                # Filter common non-authors
                common_non_authors = {"The", "This", "But", "And", "What", "For", 
                                     "That", "When", "One", "Thus", "They", "Here"}
                df = df[~df['Author'].isin(common_non_authors)]
                
                if not df.empty:
                    st.success(f"Found {len(df)} authors meeting the threshold")
                    
                    # Show top authors
                    st.subheader("Top Mentioned Authors")
                    st.dataframe(df.head(10))
                    
                    # Show bar chart
                    st.subheader("Author Mentions Visualization")
                    top_authors = df.head(10)
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.barh(top_authors['Author'][::-1], top_authors['Mentions'][::-1], color='skyblue')
                    ax.set_xlabel("Mentions")
                    ax.set_title("Top 10 Most Mentioned Authors")
                    st.pyplot(fig)
                    
                    # Download button
                    st.download_button(
                        label="Download Results as Excel",
                        data=df.to_csv(index=False).encode('utf-8'),
                        file_name='author_mentions.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("No authors found meeting the minimum mentions threshold")
                    
            else:
                st.warning("No authors found in the document")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
else:
    st.info("Please upload a document to get started")

# App info
st.markdown("---")
st.markdown("### How it works:")
st.markdown("1. Upload a PDF, EPUB, or TXT file containing literary content")
st.markdown("2. The app extracts author names using NLP and contextual patterns")
st.markdown("3. Results are filtered to remove common false positives")
st.markdown("4. Adjust the slider to control the minimum mentions threshold")
