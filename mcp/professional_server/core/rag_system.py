"""
RAG System for DroneSphere Professional MCP Server
Indexes command schemas for intelligent retrieval and context
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import numpy as np
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SchemaDocument:
    """Represents a command schema document for RAG."""
    
    def __init__(self, schema_name: str, content: Dict[str, Any], file_path: str):
        self.schema_name = schema_name
        self.content = content
        self.file_path = file_path
        self.last_modified = datetime.now()
        
    def get_text_for_embedding(self) -> str:
        """Get text representation for embedding."""
        text_parts = []
        
        # Basic schema info
        text_parts.append(f"Command: {self.content.get('name', self.schema_name)}")
        text_parts.append(f"Description: {self.content.get('description', '')}")
        text_parts.append(f"Category: {self.content.get('category', 'general')}")
        
        # Parameters
        parameters = self.content.get('parameters', {})
        if parameters:
            text_parts.append("Parameters:")
            for param_name, param_info in parameters.items():
                if isinstance(param_info, dict):
                    desc = param_info.get('description', '')
                    param_type = param_info.get('type', '')
                    unit = param_info.get('unit', '')
                    text_parts.append(f"  - {param_name}: {desc} ({param_type}) {unit}")
        
        # AI guidelines
        ai_guidelines = self.content.get('ai_guidelines', {})
        if ai_guidelines:
            text_parts.append("AI Guidelines:")
            
            # Natural language patterns
            patterns = ai_guidelines.get('natural_language_patterns', {})
            for language, pattern_list in patterns.items():
                if isinstance(pattern_list, list):
                    text_parts.append(f"  {language} patterns: {', '.join(pattern_list[:3])}")
            
            # Safety considerations
            safety = ai_guidelines.get('safety_considerations', [])
            if safety:
                text_parts.append(f"  Safety: {', '.join(safety[:2])}")
        
        return "\n".join(text_parts)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata for the document."""
        return {
            "schema_name": self.schema_name,
            "file_path": self.file_path,
            "last_modified": self.last_modified.isoformat(),
            "category": self.content.get('category', 'general'),
            "command_name": self.content.get('name', self.schema_name)
        }


class RAGSystem:
    """RAG system for command schema indexing and retrieval."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize RAG system."""
        self.config = self._load_config(config_path)
        self.schemas_dir = Path(self.config.get("rag", {}).get("schemas", {}).get("source_directory", "../../shared/command_schemas"))
        self.index_file = Path(self.config.get("rag", {}).get("schemas", {}).get("index_file", "schemas_index.json"))
        self.update_interval = self.config.get("rag", {}).get("schemas", {}).get("update_interval", 300)
        
        # Initialize lightweight embedding model
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.similarity_threshold = self.config.get("rag", {}).get("similarity_threshold", 0.3)
        
        # Document storage
        self.documents: List[SchemaDocument] = []
        self.embeddings: Optional[np.ndarray] = None
        self.tfidf_matrix = None
        
        # Cache management
        self.last_update = None
        self.cache_valid = False
        
        logger.info(f"RAG System initialized with schemas directory: {self.schemas_dir}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "rag": {
                "schemas": {
                    "enabled": True,
                    "source_directory": "../../shared/command_schemas",
                    "index_file": "schemas_index.json",
                    "update_interval": 300
                },
                "similarity_threshold": 0.7
            }
        }
    
    def _should_update_index(self) -> bool:
        """Check if index should be updated."""
        if not self.last_update:
            return True
        
        if not self.cache_valid:
            return True
        
        time_since_update = datetime.now() - self.last_update
        return time_since_update.total_seconds() > self.update_interval
    
    def _load_schema_files(self) -> List[SchemaDocument]:
        """Load all schema files from the schemas directory."""
        documents = []
        
        if not self.schemas_dir.exists():
            logger.warning(f"Schemas directory not found: {self.schemas_dir}")
            return documents
        
        # Load all YAML files
        for yaml_file in self.schemas_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                
                schema_name = yaml_file.stem
                document = SchemaDocument(schema_name, content, str(yaml_file))
                documents.append(document)
                
                logger.debug(f"Loaded schema: {schema_name}")
                
            except Exception as e:
                logger.error(f"Failed to load schema {yaml_file}: {e}")
                continue
        
        logger.info(f"Loaded {len(documents)} schema documents")
        return documents
    
    def _create_embeddings(self, documents: List[SchemaDocument]) -> np.ndarray:
        """Create lightweight embeddings for documents."""
        texts = [doc.get_text_for_embedding() for doc in documents]
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        return self.tfidf_matrix.toarray()
    
    def _build_index(self, embeddings: np.ndarray) -> np.ndarray:
        """Build lightweight similarity index."""
        return embeddings
    
    def update_index(self, force: bool = False) -> bool:
        """Update the RAG index."""
        if not force and not self._should_update_index():
            logger.debug("Index is up to date, skipping update")
            return True
        
        try:
            logger.info("Updating RAG index...")
            
            # Load documents
            self.documents = self._load_schema_files()
            
            if not self.documents:
                logger.warning("No documents found for indexing")
                return False
            
            # Create embeddings
            self.embeddings = self._create_embeddings(self.documents)
            
            # Build index
            self.index = self._build_index(self.embeddings)
            
            # Update cache status
            self.last_update = datetime.now()
            self.cache_valid = True
            
            logger.info(f"RAG index updated successfully with {len(self.documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update RAG index: {e}")
            self.cache_valid = False
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[SchemaDocument, float]]:
        """Search for relevant schemas using lightweight TF-IDF."""
        if not self.index is not None or not self.documents:
            if not self.update_index():
                return []
        
        try:
            # Create query embedding
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top k results
            top_indices = similarities.argsort()[-min(top_k, len(self.documents)):][::-1]
            
            # Filter by similarity threshold
            results = []
            for idx in top_indices:
                score = similarities[idx]
                if score >= self.similarity_threshold:
                    document = self.documents[idx]
                    results.append((document, float(score)))
            
            logger.debug(f"RAG search returned {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    def get_schema_context(self, query: str, max_context_length: int = 4000) -> str:
        """Get relevant schema context for a query."""
        results = self.search(query, top_k=3)
        
        if not results:
            return "No relevant command schemas found."
        
        context_parts = ["Relevant Command Schemas:"]
        
        for document, score in results:
            context_parts.append(f"\n--- {document.schema_name} (relevance: {score:.2f}) ---")
            context_parts.append(document.get_text_for_embedding())
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > max_context_length:
            context = context[:max_context_length] + "..."
        
        return context
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get all available schemas with metadata."""
        if not self.documents:
            self.update_index()
        
        schemas = []
        for doc in self.documents:
            schemas.append({
                "name": doc.schema_name,
                "command_name": doc.content.get('name', doc.schema_name),
                "description": doc.content.get('description', ''),
                "category": doc.content.get('category', 'general'),
                "file_path": doc.file_path,
                "last_modified": doc.last_modified.isoformat()
            })
        
        return schemas
    
    def get_schema_by_name(self, schema_name: str) -> Optional[SchemaDocument]:
        """Get a specific schema by name."""
        if not self.documents:
            self.update_index()
        
        for doc in self.documents:
            if doc.schema_name == schema_name:
                return doc
        
        return None
    
    def get_schemas_by_category(self, category: str) -> List[SchemaDocument]:
        """Get schemas by category."""
        if not self.documents:
            self.update_index()
        
        return [doc for doc in self.documents if doc.content.get('category') == category]
    
    def get_index_status(self) -> Dict[str, Any]:
        """Get RAG index status."""
        return {
            "documents_count": len(self.documents),
            "index_built": self.index is not None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "cache_valid": self.cache_valid,
            "update_interval": self.update_interval,
            "similarity_threshold": self.similarity_threshold,
            "schemas_directory": str(self.schemas_dir),
            "embedding_type": "TF-IDF (lightweight)"
        } 