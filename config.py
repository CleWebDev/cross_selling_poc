import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

class Config:
    """Configuration class for environment variables."""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_ORG_ID = os.getenv('OPENAI_ORG_ID')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    @classmethod
    def validate_openai_config(cls):
        """Validate that required OpenAI configuration is present."""
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Set it in your environment or create a .env file with OPENAI_API_KEY=your_key_here"
            )
        return True