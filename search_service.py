import os
import shutil
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, ID, TEXT, STORED
from whoosh.qparser import QueryParser # <-- We import it from Whoosh here
from whoosh.highlight import Formatter, ContextFragmenter
from config import INDEX_DIR # Import from config

# --- Schema Definition (from your code) ---

def get_search_schema():
    """Defines the schema for the search index."""
    return Schema(
        course_id=ID(stored=True), 
        course_name=TEXT(stored=True),
        file_name=ID(stored=True), 
        file_type=STORED(),
        content=TEXT(stored=True, phrase=True) # Text content of the file
    )

# --- Index Management ---

def get_index():
    """
    Opens the existing Whoosh index or creates a new one if it doesn't exist.
    """
    if not exists_in(INDEX_DIR):
        print(f" 🌀 [Search] Index not found at {INDEX_DIR}. Creating new index...")
        os.makedirs(INDEX_DIR, exist_ok=True)
        ix = create_in(INDEX_DIR, get_search_schema())
    else:
        # print(f" 🔍 [Search] Opening existing index at {INDEX_DIR}...")
        ix = open_dir(INDEX_DIR)
    return ix

def clear_search_index():
    """
    Completely removes the existing index directory and creates a new, empty one.
    """
    print(f" 🗑️ [Search] Clearing existing index at {INDEX_DIR}...")
    try:
        if os.path.exists(INDEX_DIR):
            shutil.rmtree(INDEX_DIR) # Remove the entire directory
        
        # Ensure the directory exists for the new index
        os.makedirs(INDEX_DIR, exist_ok=True) 
        
        schema = get_search_schema()
        ix = create_in(INDEX_DIR, schema)
        print(" ❇️ [Search] Index cleared and re-created.")
        return ix
    except Exception as e:
        print(f" ⚠️ [Search] Failed to clear/create index: {e}")
        raise

def add_document_to_index(ix, course_id, course_name, file_name, file_type, content):
    """
    Adds a single document to the search index.
    """
    try:
        writer = ix.writer()
        writer.add_document(
            course_id=str(course_id),
            course_name=str(course_name),
            file_name=str(file_name),
            file_type=str(file_type),
            content=str(content)
        )
        writer.commit()
    except Exception as e:
        print(f" ⚠️ [Search] Failed to add document {file_name}: {e}")

# --- Custom Formatter (from your code) ---

class SimpleFormatter(Formatter):
    """Wraps highlighted terms in <strong> tags."""
    def format_token(self, text, token, replace=False):
        # The 'text' param is the original text of the token
        return f"<strong>{text}</strong>"

# --- Search Function ---

def search_index(search_query: str):
    """
    Searches the index for the given query string.
    Returns a list of result dictionaries, including highlighted snippets.
    """
    results_list = []
    try:
        ix = get_index()
        
        # We use Whoosh's QueryParser *inside* this function
        # It parses queries for the 'content' field
        parser = QueryParser("content", schema=ix.schema)
        
        # Parse the user's search query
        query = parser.parse(search_query)

        with ix.searcher() as searcher:
            results = searcher.search(query, limit=10)
            
            # Configure highlighting
            results.formatter = SimpleFormatter() # Use our custom formatter
            results.fragmenter = ContextFragmenter(maxchars=200, surround=50)

            for hit in results:
                # Get the highlighted snippet from the 'content' field
                highlighted_content = hit.highlights("content")
                
                # Fallback if no highlight (e.g., searching by ID)
                if not highlighted_content:
                    highlighted_content = (hit['content'][:150] + '...') if len(hit['content']) > 150 else hit['content']

                results_list.append({
                    "score": hit.score,
                    "course_id": hit.get("course_id"),
                    "course_name": hit.get("course_name"),
                    "file_name": hit.get("file_name"),
                    "file_type": hit.get("file_type"),
                    "content": highlighted_content
                })
                
    except Exception as e:
        print(f" ⚠️ [Search] Error during search for '{search_query}': {e}")
        return [] # Return empty list on error

    return results_list