from openai import OpenAI


class LocalLLMClient:
    def __init__(self) -> None:
        # Point to the local server
        self.open_ai = OpenAI(
            base_url='http://localhost:1234/v1', api_key='lm-studio'
        )

    async def req_str(self, prompt_text: str, message_text: str) -> str:
        completion = self.open_ai.chat.completions.create(
            model='lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF',
            messages=[
                {
                    'role': 'system',
                    'content': prompt_text,
                },
                {
                    'role': 'user',
                    'content': message_text,
                },
            ],
            temperature=0.0,
        )
        print('\n')
        print('-' * 10)
        print('prompt_text:', prompt_text)
        print('message_text:', message_text)
        print('completion:', completion.choices[0].message.content)
        print('-' * 10)
        return completion.choices[0].message.content or ''
