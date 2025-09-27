"""Test script to validate AI integration."""

import asyncio
import os
from agents.code_analysis_agent import CodeAnalysisAgent


async def test_ai_integration():
    """Test AI integration with sample commit data."""
    print("🧪 Testing AI Integration...")
    
    # Check if API key is configured
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not found in environment")
        print("Please set the GEMINI_API_KEY environment variable")
        return False
    
    try:
        # Initialize AI agent
        print("🤖 Initializing AI agent...")
        agent = CodeAnalysisAgent()
        print("✅ AI agent initialized successfully")
        
        # Test commit message analysis
        print("\n📝 Testing commit message analysis...")
        message_analysis = await agent.analyze_commit_message(
            "feat(auth): add JWT token refresh functionality",
            {"files_changed": 3, "additions": 150, "deletions": 20}
        )
        print(f"✅ Message analysis score: {message_analysis.get('score', 0)}/100")
        
        # Test code analysis
        print("\n🔍 Testing code analysis...")
        sample_files = [{
            "filename": "auth.py",
            "additions": 50,
            "deletions": 10,
            "changes": 60,
            "patch": """
@@ -1,10 +1,15 @@
 def authenticate_user(token: str) -> User:
+    if not token:
+        raise ValueError("Token is required")
+    
     try:
         payload = jwt.decode(token, SECRET_KEY)
         user_id = payload.get("user_id")
+        if not user_id:
+            raise ValueError("Invalid token payload")
         return get_user_by_id(user_id)
     except jwt.ExpiredSignatureError:
         raise AuthenticationError("Token expired")
+    except Exception as e:
+        raise AuthenticationError(f"Authentication failed: {e}")
""",
            "status": "modified"
        }]
        
        code_analysis = await agent.analyze_code_changes(sample_files, "Python")
        print(f"✅ Code analysis score: {code_analysis.get('quality_score', 0)}/100")
        
        # Test full commit analysis
        print("\n📊 Testing full commit analysis...")
        sample_commit = {
            "commit": {
                "message": "feat(auth): add JWT token refresh functionality\n\nImplemented token refresh endpoint with proper validation\nand error handling. Added tests for edge cases.",
                "author": {"name": "Developer", "email": "dev@example.com"}
            },
            "stats": {"additions": 150, "deletions": 20, "total": 170},
            "files": sample_files
        }
        
        repository_context = {
            "name": "tamagitto/backend",
            "language": "Python",
            "type": "repository"
        }
        
        full_analysis = await agent.analyze_commit_quality(sample_commit, repository_context)
        quality_score = full_analysis.get("overall_quality_score", 0)
        print(f"✅ Overall quality score: {quality_score}/100")
        
        # Test health impact calculation
        print("\n❤️ Testing health impact calculation...")
        health_impact = await agent.suggest_health_impact(
            full_analysis,
            {"commit_metrics": {"total_changes": 170}, "repository": repository_context}
        )
        print(f"✅ Suggested health impact: {health_impact} (-20 to +20)")
        
        print(f"\n🎉 AI Integration Test Completed Successfully!")
        print(f"📈 Final Results:")
        print(f"   • Message Quality: {message_analysis.get('score', 0)}/100")
        print(f"   • Code Quality: {code_analysis.get('quality_score', 0)}/100")
        print(f"   • Overall Quality: {quality_score}/100")
        print(f"   • Health Impact: {health_impact}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ai_integration())
    exit(0 if success else 1)