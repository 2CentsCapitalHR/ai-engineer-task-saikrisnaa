import os
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LLMInterface:
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        
        if self.provider == 'openai':
            self._init_openai()
        elif self.provider == 'anthropic':
            self._init_anthropic()
        elif self.provider == 'gemini':
            self._init_gemini()
        else:
            logger.error(f"Unsupported LLM provider: {self.provider}")
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            self.client = openai.OpenAI(api_key=api_key)
            self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            logger.info("Initialized OpenAI client")
            
        except ImportError:
            logger.error("OpenAI package not installed")
            raise ImportError("Install openai package: pip install openai")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise
    
    def _init_anthropic(self):
        """Initialize Anthropic client"""
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20240620')
            logger.info("Initialized Anthropic client")
            
        except ImportError:
            logger.error("Anthropic package not installed")
            raise ImportError("Install anthropic package: pip install anthropic")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic: {e}")
            raise
    
    def _init_gemini(self):
        """Initialize Google Gemini client"""
        try:
            import google.generativeai as genai
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            
            genai.configure(api_key=api_key)
            self.model = os.getenv('GEMINI_MODEL', 'models/gemini-1.5-pro')
            self.client = genai.GenerativeModel(self.model)
            logger.info("Initialized Gemini client")
            
        except ImportError:
            logger.error("Google AI package not installed")
            raise ImportError("Install google-generativeai package: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def query(self, prompt: str, max_tokens: int = 2000) -> str:
        """Query the LLM with a prompt"""
        
        try:
            if self.provider == 'openai':
                return self._query_openai(prompt, max_tokens)
            elif self.provider == 'anthropic':
                return self._query_anthropic(prompt, max_tokens)
            elif self.provider == 'gemini':
                return self._query_gemini(prompt, max_tokens)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            return f"Error: Could not process query - {str(e)}"
    
    def _query_openai(self, prompt: str, max_tokens: int) -> str:
        """Query OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert ADGM legal compliance assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.1
        )
        return response.choices[0].message.content
    
    def _query_anthropic(self, prompt: str, max_tokens: int) -> str:
        """Query Anthropic API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.1,
            messages=[
                {"role": "user", "content": f"You are an expert ADGM legal compliance assistant.\n\n{prompt}"}
            ]
        )
        return response.content[0].text
    
    def _query_gemini(self, prompt: str, max_tokens: int) -> str:
        """Query Google Gemini API"""
        full_prompt = f"You are an expert ADGM legal compliance assistant.\n\n{prompt}"
        response = self.client.generate_content(
            full_prompt,
            generation_config={
                'max_output_tokens': max_tokens,
                'temperature': 0.1
            }
        )
        return response.text
