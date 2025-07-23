import os
import json
from typing import List, Dict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class SemanticPromptSelector:
    """
    Uses semantic similarity with FAISS to intelligently select relevant prompts
    based on user queries.
    """

    def __init__(
        self,
        index_path="backend/assistant_app/memory/prompt_vector_store/prompt_selector_index.bin",
        mapping_path="backend/assistant_app/memory/prompt_vector_store/prompt_selector_mapping.json",
        model_name: str = "all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # FAISS index and mapping paths
        self.index_path = index_path
        self.mapping_path = mapping_path

        # FAISS index and document mapping
        self.index = None
        self.prompt_mapping = {}  # Maps index ID to prompt name
        self.prompt_descriptions = {}

        self._initialize_prompt_embeddings()

    def _initialize_prompt_embeddings(self):
        """Initialize FAISS index with prompt embeddings."""
        # Define descriptions for each prompt type
        self.prompt_descriptions = {
            "email_assistant":
                "Email management, Gmail operations, searching emails, sending emails, "
                "replying to emails, inbox organization",
            "task_management":
                "Task creation, todo lists, priority management, deadlines, task "
                "organization, project management",
            "productivity_coach":
                "Time management, workflow optimization, efficiency tips, scheduling, "
                "productivity advice",
            "error_handling":
                "Error recovery, troubleshooting, problem solving, graceful failure handling",
            "conversation_context":
                "Maintaining conversation flow, context awareness, continuity in dialogue",
            "web_search_system":
                "Web research, news search, information gathering, content fetching, "
                "source attribution, multiple URL fetching, current events, real-time information",
            "calendar_assistant":
                "Calendar management, scheduling events, meeting coordination, appointment "
                "booking, time management, event creation, calendar organization, schedule planning"
        }
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing FAISS index or create a new one."""
        if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
            # Load existing index
            self.index = faiss.read_index(self.index_path)
            with open(self.mapping_path, 'r') as f:
                self.prompt_mapping = {
                    int(k): v for k, v in json.load(f).items()
                }
            print(
                f"Loaded existing prompt selector index with {self.index.ntotal} prompts"
            )
        else:
            # Create new index
            self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index with prompt embeddings."""
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.prompt_mapping = {}

        # Generate embeddings for all prompt descriptions
        descriptions = list(self.prompt_descriptions.values())
        prompt_names = list(self.prompt_descriptions.keys())

        if descriptions:
            embeddings = self.model.encode(descriptions, convert_to_tensor=False)
            self.index.add(np.array(embeddings, dtype='float32'))

            # Create mapping from index ID to prompt name
            for i, prompt_name in enumerate(prompt_names):
                self.prompt_mapping[i] = prompt_name

            # Save the index and mapping
            self._save_index()
            print(
                f"Created new prompt selector index with {len(prompt_names)} prompts"
            )

    def _save_index(self):
        """Save FAISS index and mapping."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.mapping_path, 'w') as f:
            json.dump(self.prompt_mapping, f)

    def select_relevant_prompts(
        self,
        user_query: str,
        threshold: float = 0.3,
        max_prompts: int = 2
    ) -> List[str]:
        """
        Select relevant prompts based on semantic similarity using FAISS.

        Args:
            user_query: The user's input query
            threshold: Maximum distance threshold (lower = more similar)
            max_prompts: Maximum number of prompts to return

        Returns:
            List of prompt names to include
        """
        if not user_query.strip() or self.index.ntotal == 0:
            return []

        # Encode the user query
        query_embedding = self.model.encode([user_query], convert_to_tensor=False)

        # Search FAISS index
        distances, indices = self.index.search(
            np.array(query_embedding, dtype='float32'), max_prompts
        )

        selected_prompts = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx not in self.prompt_mapping:
                continue

            # Convert distance to similarity score (1 - normalized distance)
            # FAISS uses L2 distance, so we need to convert it
            max_possible_distance = np.sqrt(self.embedding_dim * 2)
            similarity = 1 - (dist / max_possible_distance)

            if similarity >= threshold:
                prompt_name = self.prompt_mapping[idx]
                selected_prompts.append(prompt_name)
                print(
                    f"Selected prompt '{prompt_name}' with similarity: "
                    f"{similarity:.3f} (distance: {dist:.3f})"
                )

        return selected_prompts

    def get_prompt_similarity_scores(self, user_query: str) -> Dict[str, float]:
        """Get similarity scores for all prompts with a given query."""
        if not user_query.strip() or self.index.ntotal == 0:
            return {}

        query_embedding = self.model.encode([user_query], convert_to_tensor=False)
        distances, indices = self.index.search(
            np.array(query_embedding, dtype='float32'), self.index.ntotal
        )

        scores = {}
        max_possible_distance = np.sqrt(self.embedding_dim * 2)

        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx in self.prompt_mapping:
                prompt_name = self.prompt_mapping[idx]
                similarity = 1 - (dist / max_possible_distance)
                scores[prompt_name] = similarity

        return scores

    def add_prompt(self, prompt_name: str, description: str):
        """Add a new prompt to the FAISS index."""
        embedding = self.model.encode([description], convert_to_tensor=False)
        self.index.add(np.array(embedding, dtype='float32'))

        # Add to mappings
        new_idx = self.index.ntotal - 1
        self.prompt_mapping[new_idx] = prompt_name
        self.prompt_descriptions[prompt_name] = description

        # Save updated index
        self._save_index()
        print(f"Added prompt '{prompt_name}' to index")

class HybridPromptSelector:
    """
    Combines multiple strategies for prompt selection.
    """

    def __init__(self):
        self.semantic_selector = SemanticPromptSelector()
        self.keyword_patterns = {
            "email_assistant": [
                "email", "gmail", "search", "send", "reply", "inbox", "message", "mail"
            ],
            "task_management": [
                "task", "todo", "priority", "due", "deadline", "create", "add", "list",
                "update", "delete", "project"
            ],
            "productivity_coach": [
                "productivity", "time", "schedule", "organize", "efficient", "workflow",
                "optimize", "improve"
            ],
            "error_handling": [
                "error", "problem", "issue", "fix", "troubleshoot", "debug", "help"
            ],
            "conversation_context": [
                "remember", "context", "previous", "earlier", "before"
            ],
            "calendar_assistant": [
                "calendar", "schedule", "meeting", "appointment", "event", "booking",
                "agenda", "time slot", "availability", "reservation", "conference",
                "call", "interview"
            ],
            "web_search_system": [
                # Core web search terms
                "news", "weather", "temperature", "current", "latest", "today", "recent",
                "search", "find", "information", "research", "look up", "check", "verify",
                # Question words that indicate information seeking
                "what is", "how to", "where", "when", "who", "why",
                # Content types
                "article", "report", "update", "forecast", "prediction", "trend",
                "statistics", "data", "facts", "truth", "real", "actual",
                # Time-sensitive content
                "live", "breaking", "developing", "happening", "occurring", "going on",
                # Information categories
                "situation", "condition", "status", "state", "circumstance",
                "event", "incident", "story", "coverage", "analysis", "investigation",
                # Research and data gathering
                "study", "survey", "poll", "election", "market", "stock", "price",
                "value", "cost", "rate", "percentage", "score", "rating", "review",
                # Perspectives and opinions
                "opinion", "view", "perspective", "outlook", "prospect",
                # Time and scheduling
                "future", "plan", "schedule", "calendar", "date", "time",
                "day", "week", "month", "year", "season", "period",
                # Location and geography
                "location", "place", "area", "region", "country", "city", "town",
                "address", "map", "direction", "route", "path", "way",
                # Sports and events
                "world cup", "championship", "tournament", "competition", "match",
                "game", "sport", "athletics", "olympics", "league", "team", "player",
                "athlete",
                # Business and finance
                "business", "company", "corporate", "financial", "economic", "market",
                "investment", "stock", "trading", "economy", "finance", "money",
                # Technology and science
                "technology", "science", "research", "study", "discovery", "innovation",
                "development", "advancement", "breakthrough", "invention", "patent",
                # Entertainment and culture
                "entertainment", "movie", "film", "music", "art", "culture",
                "celebrity", "actor", "actress", "director", "artist", "musician",
                "performer",
                # Politics and government
                "politics", "government", "election", "vote", "campaign", "policy",
                "law", "legislation", "regulation", "official", "minister",
                "president",
                # Health and medicine
                "health", "medical", "medicine", "doctor", "hospital", "treatment",
                "disease", "illness", "symptom", "diagnosis", "cure", "vaccine"
            ]
        }

    def select_prompts(
        self,
        user_query: str,
        use_semantic: bool = True,
        use_keywords: bool = True
    ) -> List[str]:
        """
        Select prompts using multiple strategies.

        Args:
            user_query: The user's input query
            use_semantic: Whether to use semantic similarity
            use_keywords: Whether to use keyword matching

        Returns:
            List of prompt names to include
        """
        selected_prompts = set()

        # Semantic selection
        if use_semantic:
            semantic_prompts = self.semantic_selector.select_relevant_prompts(
                user_query
            )
            selected_prompts.update(semantic_prompts)

        # Keyword selection
        if use_keywords:
            keyword_prompts = self._keyword_selection(user_query)
            selected_prompts.update(keyword_prompts)

        return list(selected_prompts)

    def _keyword_selection(self, user_query: str) -> List[str]:
        """Select prompts based on keyword matching."""
        query_lower = user_query.lower()
        selected = []

        for prompt_name, keywords in self.keyword_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                selected.append(prompt_name)

        return selected

    def get_selection_debug_info(self, user_query: str) -> Dict:
        """Get debug information about prompt selection."""
        semantic_scores = self.semantic_selector.get_prompt_similarity_scores(
            user_query
        )
        keyword_matches = self._keyword_selection(user_query)

        return {
            "semantic_scores": semantic_scores,
            "keyword_matches": keyword_matches,
            "final_selection": self.select_prompts(user_query)
        }
