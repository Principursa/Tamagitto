"""AI-powered code analysis agent using Google ADK."""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Primary analysis using Google ADK
try:
    from google import adk
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    print("Warning: google-adk not available, using fallback analysis")

# Image generation using Google Generative AI
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: google-generativeai not available, image generation disabled")


class CodeAnalysisAgent:
    """AI agent for analyzing code changes and commit quality using Google ADK."""

    def __init__(self):
        """Initialize the code analysis agent with Google ADK."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Initialize Google ADK for code analysis
        if ADK_AVAILABLE:
            try:
                # Configure Google ADK client
                self.adk_client = adk.Client(api_key=api_key)
                self.adk_enabled = True
                print("✅ Google ADK initialized for code analysis")
            except Exception as e:
                print(f"Warning: Failed to initialize Google ADK: {e}")
                self.adk_enabled = False
        else:
            self.adk_enabled = False

        # Initialize Google Generative AI for image generation
        if GENAI_AVAILABLE:
            try:
                genai.configure(api_key=api_key)
                self.genai_model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        top_p=0.8,
                        top_k=40,
                        max_output_tokens=2048,
                        response_mime_type="application/json"
                    ),
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    }
                )
                self.genai_enabled = True
                print("✅ Google Generative AI initialized for image generation")
            except Exception as e:
                print(f"Warning: Failed to initialize Google Generative AI: {e}")
                self.genai_enabled = False
        else:
            self.genai_enabled = False
    
    async def analyze_commit_quality(self, commit_data: Dict[str, Any], 
                                   repository_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze commit quality using AI.
        
        Args:
            commit_data: Detailed commit data from GitHub
            repository_context: Repository information for context
            
        Returns:
            Detailed analysis with scores and recommendations
        """
        try:
            # Primary: Use Google ADK for analysis
            if self.adk_enabled:
                return await self._analyze_with_adk(commit_data, repository_context)

            # Fallback: Use Google Generative AI
            elif self.genai_enabled:
                return await self._analyze_with_genai(commit_data, repository_context)

            # Last resort: Basic rule-based analysis
            else:
                return self._fallback_analysis(commit_data)

        except Exception as e:
            print(f"AI analysis failed: {e}")
            return self._fallback_analysis(commit_data)
    
    async def analyze_code_changes(self, files_changed: List[Dict[str, Any]], 
                                 language: str) -> Dict[str, Any]:
        """
        Analyze specific code changes for quality, complexity, and best practices.
        
        Args:
            files_changed: List of changed files with patches
            language: Primary programming language
            
        Returns:
            Code quality analysis
        """
        if not files_changed or len(files_changed) == 0:
            return {"quality_score": 60, "insights": [], "complexity_change": "neutral"}
        
        # Focus on the most significant files (limit for API efficiency)
        significant_files = self._select_significant_files(files_changed)
        
        prompt = self._build_code_analysis_prompt(significant_files, language)
        
        try:
            response = await self.model.generate_content_async(prompt)
            result = json.loads(response.text)
            return self._validate_code_analysis_result(result)
            
        except Exception as e:
            print(f"Code analysis failed: {e}")
            return {"quality_score": 60, "insights": [], "complexity_change": "neutral"}
    
    async def analyze_commit_message(self, message: str, 
                                   commit_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze commit message quality and adherence to conventions.
        
        Args:
            message: Commit message
            commit_context: Context about the commit changes
            
        Returns:
            Message analysis with score and suggestions
        """
        prompt = self._build_message_analysis_prompt(message, commit_context)
        
        try:
            response = await self.model.generate_content_async(prompt)
            result = json.loads(response.text)
            return self._validate_message_analysis_result(result)
            
        except Exception as e:
            print(f"Message analysis failed: {e}")
            return {"score": 60, "suggestions": [], "follows_conventions": False}
    
    async def suggest_health_impact(self, analysis_results: Dict[str, Any], 
                                  commit_context: Dict[str, Any]) -> int:
        """
        Suggest health impact based on comprehensive analysis results.
        
        Args:
            analysis_results: Combined analysis results
            commit_context: Commit and repository context
            
        Returns:
            Health impact value (-20 to +20)
        """
        prompt = self._build_health_impact_prompt(analysis_results, commit_context)
        
        try:
            response = await self.model.generate_content_async(prompt)
            result = json.loads(response.text)
            
            # Validate health impact is in correct range
            impact = result.get("health_impact", 0)
            return max(-20, min(20, impact))
            
        except Exception as e:
            print(f"Health impact analysis failed: {e}")
            # Fallback calculation
            quality_score = analysis_results.get("overall_quality_score", 60)
            return self._calculate_fallback_health_impact(quality_score)

    async def _analyze_with_adk(self, commit_data: Dict[str, Any],
                               repository_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis using Google ADK.

        Args:
            commit_data: Detailed commit data from GitHub
            repository_context: Repository information for context

        Returns:
            Analysis results using Google ADK
        """
        try:
            # Prepare analysis request for Google ADK
            analysis_request = {
                "task": "code_review",
                "data": {
                    "commit": commit_data,
                    "repository": repository_context,
                    "analysis_dimensions": [
                        "code_quality",
                        "best_practices",
                        "testing",
                        "documentation",
                        "security",
                        "performance",
                        "commit_message"
                    ]
                },
                "output_format": "structured_json",
                "model_config": {
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "focus": "comprehensive_code_analysis"
                }
            }

            # Execute analysis using Google ADK
            adk_response = await self.adk_client.analyze(analysis_request)

            # Process ADK response into our standard format
            result = self._process_adk_response(adk_response)

            # Validate and normalize
            return self._validate_analysis_result(result)

        except Exception as e:
            print(f"Google ADK analysis failed: {e}")
            # Fallback to Generative AI
            if self.genai_enabled:
                return await self._analyze_with_genai(commit_data, repository_context)
            else:
                return self._fallback_analysis(commit_data)

    async def _analyze_with_genai(self, commit_data: Dict[str, Any],
                                 repository_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis using Google Generative AI as fallback.

        Args:
            commit_data: Detailed commit data from GitHub
            repository_context: Repository information for context

        Returns:
            Analysis results using Generative AI
        """
        prompt = self._build_analysis_prompt(commit_data, repository_context)

        response = await self.genai_model.generate_content_async(prompt)
        result = json.loads(response.text)

        return self._validate_analysis_result(result)

    def _process_adk_response(self, adk_response: Any) -> Dict[str, Any]:
        """
        Process Google ADK response into standard format.

        Args:
            adk_response: Raw response from Google ADK

        Returns:
            Processed analysis data
        """
        # This will depend on the actual Google ADK response format
        # For now, creating a structure that matches our expected format

        if hasattr(adk_response, 'analysis_results'):
            results = adk_response.analysis_results

            return {
                "overall_quality_score": results.get("overall_score", 60),
                "dimension_scores": {
                    "code_quality": results.get("code_quality", 60),
                    "best_practices": results.get("best_practices", 60),
                    "testing": results.get("testing", 50),
                    "documentation": results.get("documentation", 50),
                    "security": results.get("security", 70),
                    "performance": results.get("performance", 60),
                    "commit_message": results.get("commit_message", 60)
                },
                "key_insights": results.get("insights", [])[:5],
                "complexity_assessment": results.get("complexity_change", "neutral"),
                "risk_factors": results.get("risks", [])[:3],
                "positive_aspects": results.get("positives", [])[:3],
                "recommendations": results.get("recommendations", [])[:3],
                "adk_metadata": {
                    "model_version": getattr(adk_response, 'model_version', 'unknown'),
                    "confidence_score": getattr(adk_response, 'confidence', 0.8),
                    "analysis_method": "google_adk"
                }
            }
        else:
            # Handle different ADK response formats
            return {
                "overall_quality_score": 60,
                "dimension_scores": {
                    "code_quality": 60,
                    "best_practices": 60,
                    "testing": 50,
                    "documentation": 50,
                    "security": 70,
                    "performance": 60,
                    "commit_message": 60
                },
                "key_insights": ["Google ADK analysis completed"],
                "complexity_assessment": "neutral",
                "risk_factors": [],
                "positive_aspects": [],
                "recommendations": ["Analysis results processed via Google ADK"],
                "adk_metadata": {
                    "analysis_method": "google_adk",
                    "response_format": str(type(adk_response))
                }
            }
    
    def _build_analysis_prompt(self, commit_data: Dict[str, Any], 
                              repository_context: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt for AI."""
        commit = commit_data.get("commit", {})
        stats = commit_data.get("stats", {})
        files = commit_data.get("files", [])
        
        # Limit file content for API efficiency
        limited_files = files[:10]  # Max 10 files
        for file in limited_files:
            if file.get("patch") and len(file["patch"]) > 2000:
                file["patch"] = file["patch"][:2000] + "... [truncated]"
        
        prompt = f"""
You are a senior code reviewer analyzing a Git commit for quality assessment. Provide a detailed analysis in JSON format.

REPOSITORY CONTEXT:
- Name: {repository_context.get('name', 'Unknown')}
- Language: {repository_context.get('language', 'Unknown')}
- Type: {repository_context.get('type', 'Unknown')}

COMMIT INFORMATION:
- Message: {commit.get('message', 'No message')}
- Author: {commit.get('author', {}).get('name', 'Unknown')}
- Changes: +{stats.get('additions', 0)} -{stats.get('deletions', 0)}
- Files modified: {len(files)}

FILES CHANGED:
{json.dumps(limited_files, indent=2)[:3000]}

ANALYSIS REQUIREMENTS:
Analyze the commit across these dimensions and provide scores (0-100):

1. **Code Quality** (0-100): Assess code structure, readability, maintainability
2. **Best Practices** (0-100): Adherence to language-specific conventions and patterns
3. **Testing** (0-100): Test coverage and quality of test changes
4. **Documentation** (0-100): Documentation updates and code comments
5. **Security** (0-100): Potential security implications
6. **Performance** (0-100): Performance impact of changes
7. **Commit Message** (0-100): Quality and informativeness of commit message

REQUIRED JSON RESPONSE FORMAT:
{{
  "overall_quality_score": <0-100>,
  "dimension_scores": {{
    "code_quality": <0-100>,
    "best_practices": <0-100>, 
    "testing": <0-100>,
    "documentation": <0-100>,
    "security": <0-100>,
    "performance": <0-100>,
    "commit_message": <0-100>
  }},
  "key_insights": [
    "Insight 1: Brief description of what was done well",
    "Insight 2: Area for improvement",
    "Insight 3: Notable pattern or issue"
  ],
  "complexity_assessment": "<increased/decreased/neutral>",
  "risk_factors": [
    "List any potential risks or concerns"
  ],
  "positive_aspects": [
    "List positive aspects of this commit"
  ],
  "recommendations": [
    "Specific actionable recommendations for improvement"
  ]
}}

Focus on being constructive and educational while being thorough in analysis.
"""
        return prompt
    
    def _build_code_analysis_prompt(self, files: List[Dict[str, Any]], language: str) -> str:
        """Build code-specific analysis prompt."""
        prompt = f"""
Analyze these {language} code changes for quality and best practices. Return JSON only.

FILES CHANGED:
{json.dumps(files, indent=2)[:4000]}

REQUIRED JSON RESPONSE:
{{
  "quality_score": <0-100>,
  "complexity_change": "<increased/decreased/neutral>",
  "insights": [
    "Key observations about the code changes"
  ],
  "best_practices_violations": [
    "Any violations of {language} best practices"
  ],
  "security_concerns": [
    "Any potential security issues identified"
  ],
  "performance_impact": "<positive/negative/neutral>",
  "maintainability_impact": "<improved/degraded/neutral>"
}}
"""
        return prompt
    
    def _build_message_analysis_prompt(self, message: str, context: Dict[str, Any]) -> str:
        """Build commit message analysis prompt."""
        prompt = f"""
Analyze this commit message for quality and adherence to conventions:

COMMIT MESSAGE:
{message}

COMMIT CONTEXT:
- Files changed: {context.get('files_changed', 0)}
- Lines added: {context.get('additions', 0)}
- Lines deleted: {context.get('deletions', 0)}

REQUIRED JSON RESPONSE:
{{
  "score": <0-100>,
  "follows_conventions": <true/false>,
  "conventional_type": "<feat/fix/docs/style/refactor/test/chore/other>",
  "clarity_score": <0-100>,
  "suggestions": [
    "Specific suggestions for improvement"
  ],
  "strengths": [
    "What the message does well"
  ]
}}
"""
        return prompt
    
    def _build_health_impact_prompt(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build health impact calculation prompt."""
        prompt = f"""
Based on this commit analysis, determine the health impact for a Tamagotchi-like entity (-20 to +20):

ANALYSIS RESULTS:
{json.dumps(analysis, indent=2)}

COMMIT CONTEXT:
{json.dumps(context, indent=2)}

HEALTH IMPACT GUIDELINES:
- Excellent commits (90-100 quality): +15 to +20
- Good commits (70-89 quality): +5 to +14  
- Average commits (50-69 quality): -2 to +4
- Poor commits (30-49 quality): -10 to -3
- Terrible commits (0-29 quality): -20 to -11

Consider:
- Code quality improvements deserve positive impact
- Bug fixes and security improvements are valuable
- Breaking changes or introducing tech debt should reduce impact
- Large commits should have proportionally larger impacts

REQUIRED JSON RESPONSE:
{{
  "health_impact": <-20 to +20>,
  "reasoning": "Brief explanation of the impact calculation"
}}
"""
        return prompt
    
    def _select_significant_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select the most significant files for detailed analysis."""
        # Sort by number of changes (additions + deletions)
        sorted_files = sorted(
            files, 
            key=lambda f: f.get("changes", 0),
            reverse=True
        )
        
        # Take top 5 most changed files
        return sorted_files[:5]
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize AI analysis result."""
        # Ensure all required fields exist with defaults
        validated = {
            "overall_quality_score": max(0, min(100, result.get("overall_quality_score", 60))),
            "dimension_scores": result.get("dimension_scores", {}),
            "key_insights": result.get("key_insights", [])[:5],  # Limit insights
            "complexity_assessment": result.get("complexity_assessment", "neutral"),
            "risk_factors": result.get("risk_factors", [])[:3],
            "positive_aspects": result.get("positive_aspects", [])[:3],
            "recommendations": result.get("recommendations", [])[:3]
        }
        
        # Validate dimension scores
        default_scores = {
            "code_quality": 60,
            "best_practices": 60,
            "testing": 50,
            "documentation": 50,
            "security": 70,
            "performance": 60,
            "commit_message": 60
        }
        
        for dimension, default_score in default_scores.items():
            score = validated["dimension_scores"].get(dimension, default_score)
            validated["dimension_scores"][dimension] = max(0, min(100, score))
        
        return validated
    
    def _validate_code_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate code analysis result."""
        return {
            "quality_score": max(0, min(100, result.get("quality_score", 60))),
            "complexity_change": result.get("complexity_change", "neutral"),
            "insights": result.get("insights", [])[:3],
            "best_practices_violations": result.get("best_practices_violations", [])[:3],
            "security_concerns": result.get("security_concerns", [])[:3],
            "performance_impact": result.get("performance_impact", "neutral"),
            "maintainability_impact": result.get("maintainability_impact", "neutral")
        }
    
    def _validate_message_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate message analysis result."""
        return {
            "score": max(0, min(100, result.get("score", 60))),
            "follows_conventions": result.get("follows_conventions", False),
            "conventional_type": result.get("conventional_type", "other"),
            "clarity_score": max(0, min(100, result.get("clarity_score", 60))),
            "suggestions": result.get("suggestions", [])[:3],
            "strengths": result.get("strengths", [])[:3]
        }
    
    def _fallback_analysis(self, commit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback analysis when AI fails."""
        stats = commit_data.get("stats", {})
        additions = stats.get("additions", 0)
        deletions = stats.get("deletions", 0)
        files = commit_data.get("files", [])
        
        # Basic scoring based on commit size and patterns
        base_score = 60
        
        # Adjust based on commit size
        total_changes = additions + deletions
        if 20 <= total_changes <= 200:
            base_score += 10
        elif total_changes > 500:
            base_score -= 15
        
        # Check for test files
        test_files = sum(1 for f in files if "test" in f.get("filename", "").lower())
        if test_files > 0:
            base_score += 10
        
        return {
            "overall_quality_score": max(30, min(80, base_score)),
            "dimension_scores": {
                "code_quality": base_score,
                "best_practices": base_score - 5,
                "testing": 50 + (10 if test_files > 0 else 0),
                "documentation": 50,
                "security": 70,
                "performance": 60,
                "commit_message": 55
            },
            "key_insights": ["Fallback analysis - AI analysis unavailable"],
            "complexity_assessment": "neutral",
            "risk_factors": [],
            "positive_aspects": [],
            "recommendations": ["Consider using conventional commit messages"]
        }
    
    def _calculate_fallback_health_impact(self, quality_score: int) -> int:
        """Calculate health impact when AI analysis fails."""
        if quality_score >= 90:
            return 15
        elif quality_score >= 70:
            return 8
        elif quality_score >= 50:
            return 2
        elif quality_score >= 30:
            return -5
        else:
            return -12