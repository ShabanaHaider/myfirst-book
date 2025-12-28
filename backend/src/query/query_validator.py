"""
Query validation module for input validation.
"""
from typing import Dict, List, Any
from pydantic import BaseModel, Field, validator
import re
from src.config.settings import settings
from src.utils.text_utils import clean_text


class QueryValidationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=settings.MAX_QUERY_LENGTH)
    top_k: int = Field(default=settings.TOP_K_RETRIEVAL, ge=1, le=20)
    similarity_threshold: float = Field(default=settings.SIMILARITY_THRESHOLD, ge=0.0, le=1.0)


class QueryValidator:
    """
    Module for validating query inputs before processing.
    """

    @staticmethod
    def validate_query_text(query: str) -> Dict[str, Any]:
        """
        Validate the query text itself.

        Args:
            query: The query text to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "query_length": len(query),
            "word_count": len(query.split())
        }

        # Check if query is empty or just whitespace
        if not query or not query.strip():
            result["is_valid"] = False
            result["issues"].append("Query cannot be empty")
            result["suggestions"].append("Provide a non-empty query")
            return result

        # Check query length
        if len(query) > settings.MAX_QUERY_LENGTH:
            result["is_valid"] = False
            result["issues"].append(f"Query exceeds maximum length of {settings.MAX_QUERY_LENGTH} characters")
            result["suggestions"].append(f"Shorten your query to under {settings.MAX_QUERY_LENGTH} characters")

        # Check for minimum length
        if len(query.strip()) < 3:
            result["issues"].append("Query is very short - may not yield good results")
            result["suggestions"].append("Try making your query more specific")

        # Check if query contains only special characters
        if query.strip() and not any(c.isalnum() for c in query):
            result["is_valid"] = False
            result["issues"].append("Query contains no alphanumeric characters")
            result["suggestions"].append("Include meaningful words in your query")

        # Check for potentially problematic content
        cleaned_query = clean_text(query.lower())
        if any(prohibited in cleaned_query for prohibited in ["password", "token", "secret", "key"]):
            result["issues"].append("Query may contain sensitive information")
            result["suggestions"].append("Avoid including sensitive information in your query")

        return result

    @staticmethod
    def validate_top_k(top_k: int) -> Dict[str, Any]:
        """
        Validate the top_k parameter.

        Args:
            top_k: The number of results to retrieve

        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "value": top_k
        }

        if top_k < 1:
            result["is_valid"] = False
            result["issues"].append("top_k must be at least 1")
            result["suggestions"].append("Set top_k to a value between 1 and 20")
        elif top_k > 20:
            result["is_valid"] = False
            result["issues"].append("top_k exceeds maximum of 20")
            result["suggestions"].append("Set top_k to a value between 1 and 20")

        return result

    @staticmethod
    def validate_similarity_threshold(similarity_threshold: float) -> Dict[str, Any]:
        """
        Validate the similarity threshold parameter.

        Args:
            similarity_threshold: The minimum similarity score threshold

        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "value": similarity_threshold
        }

        if similarity_threshold < 0.0 or similarity_threshold > 1.0:
            result["is_valid"] = False
            result["issues"].append("similarity_threshold must be between 0.0 and 1.0")
            result["suggestions"].append("Set similarity_threshold to a value between 0.0 and 1.0")

        return result

    @staticmethod
    def validate_full_query_request(query: str, top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """
        Validate the complete query request.

        Args:
            query: The query text
            top_k: Number of results to retrieve
            similarity_threshold: Minimum similarity score threshold

        Returns:
            Dictionary with comprehensive validation results
        """
        query_validation = QueryValidator.validate_query_text(query)
        top_k_validation = QueryValidator.validate_top_k(top_k)
        threshold_validation = QueryValidator.validate_similarity_threshold(similarity_threshold)

        # Combine all validations
        result = {
            "is_valid": all([
                query_validation["is_valid"],
                top_k_validation["is_valid"],
                threshold_validation["is_valid"]
            ]),
            "query_validation": query_validation,
            "top_k_validation": top_k_validation,
            "threshold_validation": threshold_validation,
            "overall_issues": [],
            "overall_suggestions": []
        }

        # Combine issues and suggestions from all validations
        if not query_validation["is_valid"]:
            result["overall_issues"].extend(query_validation["issues"])
            result["overall_suggestions"].extend(query_validation["suggestions"])

        if not top_k_validation["is_valid"]:
            result["overall_issues"].extend(top_k_validation["issues"])
            result["overall_suggestions"].extend(top_k_validation["suggestions"])

        if not threshold_validation["is_valid"]:
            result["overall_issues"].extend(threshold_validation["issues"])
            result["overall_suggestions"].extend(threshold_validation["suggestions"])

        # Add warnings for values that are valid but might not be optimal
        if top_k > 10:
            result["overall_issues"].append("Using a high top_k value may impact performance")
            result["overall_suggestions"].append("Consider using a lower top_k value for better performance")

        if similarity_threshold < 0.3:
            result["overall_issues"].append("Low similarity threshold may return irrelevant results")
            result["overall_suggestions"].append("Consider using a higher similarity threshold for more relevant results")

        if similarity_threshold > 0.9:
            result["overall_issues"].append("High similarity threshold may return no results")
            result["overall_suggestions"].append("Consider using a lower similarity threshold to get more results")

        return result

    @staticmethod
    def suggest_query_improvements(query: str) -> Dict[str, Any]:
        """
        Suggest improvements for a query.

        Args:
            query: The query to analyze

        Returns:
            Dictionary with improvement suggestions
        """
        suggestions = {
            "original_query": query,
            "improvements": [],
            "spelling_suggestions": [],
            "clarity_suggestions": []
        }

        # Check for common issues and suggest improvements
        words = query.split()

        # Check if query is too short
        if len(words) < 3:
            suggestions["improvements"].append("Add more specific terms to your query")
            suggestions["clarity_suggestions"].append("Include more context or details in your query")

        # Check for potential spelling issues (very basic)
        common_misspellings = {
            "recieve": "receive",
            "seperate": "separate",
            "definately": "definitely",
            "occured": "occurred"
        }

        for misspelled, correct in common_misspellings.items():
            if misspelled in query.lower():
                suggestions["spelling_suggestions"].append(f"Consider using '{correct}' instead of '{misspelled}'")

        # Suggest using more specific terms if using very general ones
        general_terms = ["thing", "stuff", "make", "do", "way", "how", "what"]
        general_found = [word for word in words if word.lower() in general_terms]
        if general_found:
            suggestions["improvements"].append(f"Avoid overly general terms like: {', '.join(general_found)}")
            suggestions["clarity_suggestions"].append("Use more specific terminology related to your documentation")

        return suggestions

    @staticmethod
    def validate_and_enhance_query(query: str) -> Dict[str, Any]:
        """
        Perform comprehensive validation and enhancement of a query.

        Args:
            query: The query to validate and enhance

        Returns:
            Dictionary with validation results and enhancement suggestions
        """
        validation_result = QueryValidator.validate_query_text(query)
        improvement_suggestions = QueryValidator.suggest_query_improvements(query)

        return {
            "validation": validation_result,
            "improvements": improvement_suggestions,
            "is_processable": validation_result["is_valid"]
        }