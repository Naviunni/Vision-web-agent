import openai
import os

class ConversationalEngine:
    def __init__(self, api_key):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo" # Using gpt-3.5-turbo for conversational responses.

    def get_response(self, conversation_history):
        print("🗣️ Generating conversational response with GPT...")
        
        system_prompt = """
        You are a helpful and friendly web assistant. Your goal is to provide concise and encouraging responses to the user, summarizing what you have done or are about to do.
        Keep your responses brief and to the point.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *conversation_history # Unpack the conversation history
                ],
                temperature=0.7,
                max_tokens=100
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error while getting response from conversational engine: {e}")
            return "I'm sorry, I'm having trouble generating a conversational response."
