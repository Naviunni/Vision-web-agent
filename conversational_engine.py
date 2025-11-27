import openai
import os

class ConversationalEngine:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"


    def get_response(self, conversation_history):
        # For now, just a placeholder.
        # In the future, this will call the GPT API.
        print("🤖 Getting response from GPT...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=conversation_history,
                temperature=0.7,
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error while getting response from conversational engine: {e}")
            return "I'm sorry, I'm having trouble connecting to the conversational engine."