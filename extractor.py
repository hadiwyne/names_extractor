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
import PyPDF2
import io
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
from PIL import Image

st.set_page_config(page_title="Author Names Extractor", page_icon="📚")

# Initialize NLP model
@st.cache_resource
def load_nlp_model():
    try:
        return spacy.load('en_core_web_md')
    except:
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_md"])
        return spacy.load('en_core_web_md')

@st.cache_data
def get_epub_metadata(file_content, file_name):
    """Extract metadata from EPUB file with detailed error logging"""
    temp_file_path = None
    try:
        # Create a temporary file for ebooklib
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        # Verify temporary file exists and is readable
        if not os.path.exists(temp_file_path):
            raise FileNotFoundError(f"Temporary file {temp_file_path} was not created successfully")
        
        book = epub.read_epub(temp_file_path)
        
        metadata = {}
        
        # Get title
        try:
            metadata['title'] = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Unknown Title"
        except Exception as e:
            st.warning(f"Error extracting EPUB title: {str(e)}")
            metadata['title'] = "Unknown Title"
            
        # Get author
        try:
            metadata['author'] = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "Unknown Author"
        except Exception as e:
            st.warning(f"Error extracting EPUB author: {str(e)}")
            metadata['author'] = "Unknown Author"
            
        # Get language
        try:
            metadata['language'] = book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else "Unknown"
        except Exception as e:
            st.warning(f"Error extracting EPUB language: {str(e)}")
            metadata['language'] = "Unknown"
            
        # Get cover image
        try:
            cover_item = None
            # Check EPUB metadata for cover reference
            cover_id = None
            for meta in book.get_metadata('OPF', 'meta'):
                if meta.get('name') == 'cover':
                    cover_id = meta.get('content')
                    break
            
            # Search for cover item
            for item in book.get_items():
                item_name = item.get_name().lower()
                # Check if item is explicitly marked as cover or matches cover_id
                if (item.get_type() == ebooklib.ITEM_COVER or 
                    (cover_id and item.get_id() == cover_id) or 
                    'cover' in item_name):
                    # Validate file extension to ensure it's an image
                    if item_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        cover_item = item
                        break
            
            if cover_item:
                cover_data = cover_item.get_content()
                item_name = cover_item.get_name()
                st.info(f"Found cover item: {item_name} (size: {len(cover_data)} bytes)")
                # Validate image data
                try:
                    Image.open(io.BytesIO(cover_data)).verify()
                    metadata['cover'] = io.BytesIO(cover_data) 
                except Exception as e:
                    st.warning(f"Invalid cover image data for {item_name}: {str(e)}")
                    metadata['cover'] = None
            else:
                st.info("No valid cover image found in EPUB")
                metadata['cover'] = None
        except Exception as e:
            st.warning(f"Error extracting EPUB cover: {str(e)}")
            metadata['cover'] = None
            
        return metadata
    except Exception as e:
        st.error(f"Failed to parse EPUB metadata: {str(e)}")
        return {'title': 'Unknown Title', 'author': 'Unknown Author', 'language': 'Unknown', 'cover': None}
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                st.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")

@st.cache_data
def get_pdf_metadata(file_content, file_name):
    """Extract metadata from PDF file with detailed error logging"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        
        metadata = {}
        
        try:
            if pdf_reader.metadata:
                metadata['title'] = pdf_reader.metadata.get('/Title', 'Unknown Title') or 'Unknown Title'
                metadata['author'] = pdf_reader.metadata.get('/Author', 'Unknown Author') or 'Unknown Author'
                metadata['subject'] = pdf_reader.metadata.get('/Subject', 'Unknown Subject') or 'Unknown Subject'
                metadata['creator'] = pdf_reader.metadata.get('/Creator', 'Unknown Creator') or 'Unknown Creator'
            else:
                metadata['title'] = "Unknown Title"
                metadata['author'] = "Unknown Author"
                metadata['subject'] = "Unknown Subject"
                metadata['creator'] = "Unknown Creator"
        except Exception as e:
            st.warning(f"Error extracting PDF metadata: {str(e)}")
            metadata['title'] = "Unknown Title"
            metadata['author'] = "Unknown Author"
            metadata['subject'] = "Unknown Subject"
            metadata['creator'] = "Unknown Creator"
            
        try:
            metadata['pages'] = len(pdf_reader.pages)
        except Exception as e:
            st.warning(f"Error counting PDF pages: {str(e)}")
            metadata['pages'] = "Unknown"
            
        metadata['cover'] = None  
        
        return metadata
    except Exception as e:
        st.error(f"Failed to parse PDF metadata: {str(e)}")
        return {
            'title': 'Unknown Title',
            'author': 'Unknown Author',
            'subject': 'Unknown Subject',
            'creator': 'Unknown Creator',
            'pages': 'Unknown',
            'cover': None
        }

def load_text(file_content, file_name):
    """Load text from different file formats"""
    ext = os.path.splitext(file_name)[1].lower()
    
    if ext == ".pdf":
        with st.spinner("Parsing PDF..."):
            try:
                # Try Tika first
                result = parser.from_buffer(io.BytesIO(file_content))
                if isinstance(result, dict) and 'content' in result:
                    return result['content']
                elif isinstance(result, tuple) and len(result) > 1:
                    return result[1] if result[1] else ''
                else:
                    return str(result) if result else ''
            except Exception as e:
                st.warning(f"Tika failed: {str(e)}")
                try:
                    # Fallback to PyPDF2
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + " "
                    return text
                except Exception as e2:
                    st.error(f"Both Tika and PyPDF2 failed to parse PDF: {str(e2)}")
                    st.error("Please ensure the PDF is not password-protected and is readable")
                    st.stop()
    elif ext == ".txt":
        return file_content.decode("utf-8")
    elif ext == ".epub":
        with st.spinner("Parsing EPUB..."):
            temp_file_path = None
            try:
                # Create a temporary file for ebooklib
                with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                # Verify temporary file exists
                if not os.path.exists(temp_file_path):
                    raise FileNotFoundError(f"Temporary file {temp_file_path} was not created successfully")
                
                book = epub.read_epub(temp_file_path)
                text = ""
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        text += soup.get_text() + " "
                return text
            except Exception as e:
                st.warning(f"ebooklib failed: {str(e)}")
                try:
                    # Fallback to Tika
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
                        temp_file.write(file_content)
                        temp_file_path = temp_file.name
                        result = parser.from_file(temp_file_path)
                        if isinstance(result, dict) and 'content' in result:
                            return result['content']
                        elif isinstance(result, tuple) and len(result) > 1:
                            return result[1] if result[1] else ''
                        else:
                            return str(result) if result else ''
                except Exception as e2:
                    st.error(f"Both ebooklib and Tika failed to parse EPUB: {str(e2)}")
                    st.error("Please ensure the EPUB file is not corrupted")
                    st.stop()
                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except Exception as e:
                            st.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")
    else:
        st.error("Unsupported file format. Only PDF, EPUB, and TXT are supported.")
        st.stop()

def clean_text(text):
    """Clean and normalize text while preserving accented characters"""
    text = re.sub(r'[^a-zA-ZÀ-ÿ\s\-\'\.]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_authors(text, nlp):
    """Enhanced author extraction with better filtering"""
    doc = nlp(text)
    authors = []
    
    # Extract PERSON entities
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            if len(ent.text.split()) == 1:
                if ent.text.lower() not in STOP_WORDS and len(ent.text) > 2:
                    authors.append(ent.text)
            else:
                authors.append(ent.text)
    
    # Contextual patterns
    patterns = [
        r'(?:according to|by|writes|stated by|argued by|noted by|in|from)\s+([A-ZÀ-ÿ][a-zÀ-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zÀ-ÿ]+)+)',
        r'\b([A-ZÀ-ÿ][a-zÀ-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zÀ-ÿ]+)+)\'s (?:work|book|essay|theory|view|concept|idea)',
        r'(?:author|writer|poet|novelist|philosopher)\s+([A-ZÀ-ÿ][a-zÀ-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zÀ-ÿ]+)+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            if all(word[0].isupper() or word[0] in 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ' for word in match.split()):
                authors.append(match)
    
    return authors

# Streamlit app UI
st.title("📚 Author Names Extractor")
st.markdown("Upload a book (PDF, EPUB, TXT) to extract mentioned authors")

# File upload
uploaded_file = st.file_uploader("Choose a file", type=["pdf", "epub", "txt"])

# Settings section
if uploaded_file is not None:
    # Validate file size
    if uploaded_file.size == 0:
        st.error("Uploaded file is empty.")
        st.stop()
        
    st.markdown("---")
    st.header("Settings")
    min_mentions = st.slider("Minimum mentions threshold", 1, 20, 3)
    st.markdown("---")
    st.header("How it works")
    st.markdown("1. Upload a literary document (PDF/EPUB/TXT)")
    st.markdown("2. The app extracts author names using:")
    st.markdown("   - **spaCy's NER** for person detection")
    st.markdown("   - **Contextual patterns** for author mentions")
    st.markdown("3. Results are filtered to remove common false positives")
    st.markdown("---")

    # Read file content once
    uploaded_file.seek(0)
    file_content = uploaded_file.read()
    file_name = uploaded_file.name

    # Display metadata for supported files
    if file_name.lower().endswith('.epub'):
        st.markdown("---")
        st.subheader("📖 Book Information")
        
        metadata = get_epub_metadata(file_content, file_name)
        col1, col2 = st.columns([1, 2])
        with col1:
            if metadata.get('cover'):
                try:
                    st.image(metadata['cover'], caption="Book Cover", use_container_width=True)
                except Exception as e:
                    st.info(f"Cover image could not be displayed: {str(e)}")
            else:
                st.info("No cover image available")
        with col2:
            st.markdown(f"**Title:** {metadata.get('title', 'Unknown')}")
            st.markdown(f"**Author:** {metadata.get('author', 'Unknown')}")
            st.markdown(f"**Language:** {metadata.get('language', 'Unknown')}")
            
    elif file_name.lower().endswith('.pdf'):
        st.markdown("---")
        st.subheader("📄 Document Information")
        
        metadata = get_pdf_metadata(file_content, file_name)
        st.markdown(f"**Title:** {metadata.get('title', 'Unknown')}")
        st.markdown(f"**Author:** {metadata.get('author', 'Unknown')}")
        st.markdown(f"**Subject:** {metadata.get('subject', 'Unknown')}")
        st.markdown(f"**Creator:** {metadata.get('creator', 'Unknown')}")
        st.markdown(f"**Pages:** {metadata.get('pages', 'Unknown')}")
    
    with st.spinner("Processing your document..."):
        try:
            # Load NLP model
            nlp = load_nlp_model()
            
            # Process file
            raw_text = load_text(file_content, file_name)
            cleaned_text = clean_text(raw_text)
            
            # Extract authors
            author_list = extract_authors(cleaned_text, nlp)
            
            if author_list:
                author_counts = Counter(author_list)
                
                # Create DataFrame
                df = pd.DataFrame.from_records(list(author_counts.items()), columns=['Author', 'Mentions'])
                df = df[df['Mentions'] >= min_mentions]
                
                # Filter common non-authors
                common_non_authors = [
                    "The", "This", "But", "And", "What", "For", "That", "When",
                    "One", "Thus", "They", "Here", "Art", "Death", "Life", "Time",
                    "Man", "Men", "Way", "Part", "Two", "Three", "First", "Second",
                    "Last", "Every", "Such", "Each", "Which", "Even"
                ]
                df = df[~df['Author'].isin(common_non_authors)]
                
                # Additional filtering for non-name words
                df = df[df['Author'].apply(lambda x: len(x.split()) > 1 or (x[0].isupper() or x[0] in 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'))]
                df = df.sort_values('Mentions', ascending=False)
                
                if not df.empty:
                    st.success(f"Found {len(df)} authors with {min_mentions}+ mentions")
                    
                    # Show top authors
                    st.subheader("Top Mentioned Authors")
                    st.dataframe(df.head(15))
                    
                    # Show bar chart
                    st.subheader("Author Mentions Visualization")
                    top_authors = df.head(15)
                    
                    if not top_authors.empty:
                        fig, ax = plt.subplots(figsize=(10, 8))
                        top_authors_sorted = top_authors.sort_values('Mentions', ascending=True)
                        ax.barh(top_authors_sorted['Author'].tolist(),
                                top_authors_sorted['Mentions'].tolist(),
                                color='#1f77b4')
                        ax.set_xlabel("Mention Count")
                        ax.set_title("Most Mentioned Authors")
                        st.pyplot(fig)
                    
                    # Download button
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name='author_mentions.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("No authors found meeting the minimum mentions threshold after filtering")
            else:
                st.warning("No authors found in the document")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error("Please ensure you have Java installed for Tika PDF/EPUB processing")
else:
    st.info("Please upload a document to get started")

# App info
st.markdown("---")
st.markdown("### Tips for better results:")
st.markdown("- **Literary works** give best results (philosophy, criticism, etc.)")
st.markdown("- For **EPUB files**, ensure you have Java installed")
st.markdown("- Increase the **minimum mentions** threshold to focus on key authors")
st.markdown("- Results include both directly mentioned authors and those referenced in context")
