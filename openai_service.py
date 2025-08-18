import openai
from config import Config
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIService:
    """Service class for OpenAI integration."""
    
    def __init__(self):
        """Initialize OpenAI client with API key from config."""
        try:
            Config.validate_openai_config()
            # Set the API key and organization globally for the older openai library
            openai.api_key = Config.OPENAI_API_KEY
            if Config.OPENAI_ORG_ID:
                openai.organization = Config.OPENAI_ORG_ID
                logger.info(f"OpenAI organization ID set: {Config.OPENAI_ORG_ID}")
            self.model = Config.OPENAI_MODEL
            self.client = True  # Flag to indicate initialization success
            logger.info(f"OpenAI service initialized with model: {self.model}")
        except ValueError as e:
            logger.warning(f"OpenAI not configured: {e}")
            self.client = None
            self.model = None
        except Exception as client_error:
            logger.warning(f"Failed to initialize OpenAI client: {client_error}")
            self.client = None
            self.model = None
    
    def is_available(self):
        """Check if OpenAI service is available."""
        return self.client is not None
    
    def generate_customer_insights(self, customer_data, purchase_history, recent_invoices):
        """
        Generate customer insights using OpenAI.
        
        Args:
            customer_data: Dict containing customer information
            purchase_history: List of historical purchases
            recent_invoices: List of recent invoice data
            
        Returns:
            Dict containing AI-generated insights
        """
        if not self.is_available():
            return {"error": "OpenAI service not available"}
        
        try:
            # Prepare data for the prompt
            context = {
                "customer": customer_data,
                "history": purchase_history[-10:] if purchase_history else [],  # Last 10 items
                "recent_invoices": recent_invoices
            }
            
            prompt = self._build_customer_insights_prompt(context)
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a retail analytics expert specializing in home improvement products. Provide concise, actionable insights about customer behavior and preferences."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            insight_text = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "insights": insight_text,
                "model_used": self.model
            }
            
        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg or "exceeded your current quota" in error_msg:
                logger.error(f"OpenAI quota exceeded: {e}")
                return {
                    "error": "OpenAI quota exceeded. Please check your billing and plan details."
                }
            elif "invalid_api_key" in error_msg:
                logger.error(f"Invalid OpenAI API key: {e}")
                return {
                    "error": "Invalid OpenAI API key. Please check your configuration."
                }
            else:
                logger.error(f"Error generating customer insights: {e}")
                return {
                    "error": f"Failed to generate insights: {str(e)}"
                }
    
    def generate_product_recommendations_explanation(self, selected_products, recommendations):
        """
        Generate explanations for product recommendations using OpenAI.
        
        Args:
            selected_products: List of products customer is buying
            recommendations: List of recommended products with scores
            
        Returns:
            Dict containing AI-generated explanations
        """
        if not self.is_available():
            return {"error": "OpenAI service not available"}
        
        try:
            prompt = self._build_recommendations_prompt(selected_products, recommendations)
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful home improvement retail assistant. Explain why certain products complement each other in a friendly, informative way."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            explanation = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "explanation": explanation,
                "model_used": self.model
            }
            
        except Exception as e:
            error_msg = str(e)
            if "insufficient_quota" in error_msg or "exceeded your current quota" in error_msg:
                logger.error(f"OpenAI quota exceeded: {e}")
                return {
                    "error": "OpenAI quota exceeded. Please check your billing and plan details."
                }
            elif "invalid_api_key" in error_msg:
                logger.error(f"Invalid OpenAI API key: {e}")
                return {
                    "error": "Invalid OpenAI API key. Please check your configuration."
                }
            else:
                logger.error(f"Error generating recommendation explanation: {e}")
                return {
                    "error": f"Failed to generate explanation: {str(e)}"
                }
    
    def _build_customer_insights_prompt(self, context):
        """Build prompt for customer insights."""
        customer = context["customer"]
        history = context["history"]
        invoices = context["recent_invoices"]
        
        prompt = f"""Analyze this customer for sales staff. Be BRIEF and ACTIONABLE:

Customer: {customer.get('name', 'Unknown')}
Purchase History: {[item['item'] for item in history[-8:]] if history else 'No history'}
Recent Invoices: {[{'items': inv['items'], 'total': inv['total']} for inv in invoices] if invoices else 'No recent invoices'}

Provide EXACTLY 3 brief insights (1-2 sentences each):
1. **Product Preferences:** What types/categories does this customer buy?
2. **Potential Needs:** What accessories, maintenance, or complementary products might they need?
3. **Buying Patterns:** Any seasonal trends or project-based buying behavior?

Format: Keep each point to 1-2 sentences. Focus on what sales staff can ACT on."""
        
        return prompt
    
    def _build_recommendations_prompt(self, selected_products, recommendations):
        """Build prompt for recommendation explanations."""
        top_recs = recommendations[:3] if recommendations else []
        
        prompt = f"""You're a sales assistant explaining add-on value to customers buying: {', '.join(selected_products)}

Top recommendations:
{chr(10).join([f"- {rec.get('item', 'Unknown')}" for rec in top_recs])}

Write 2-3 compelling reasons why customers should buy these add-ons. Focus ONLY on:
- Financial benefits (savings, warranties, protection)  
- Concrete value (prevents damage, extends life, reduces costs)
- Practical necessities (required for operation, maintenance)

Avoid vague terms like "enhances experience." Use specific financial motivators like "Saves $200 in repairs" or "Free replacement for life."

Keep each reason to 1 sentence. Be direct and sales-focused."""
        
        return prompt

# Global instance
openai_service = OpenAIService()