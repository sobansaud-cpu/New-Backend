from dataclasses import dataclass
from openai import AsyncOpenAI

@dataclass
class OpenAIChatCompletionsModel:
    model: str
    openai_client: AsyncOpenAI

    async def complete(self, messages):
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content

class Agent:
    def __init__(self, name, instructions, model):
        self.name = name
        self.instructions = instructions
        self.model = model

    async def run(self, prompt):
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": prompt}
        ]
        return await self.model.complete(messages)

class Runner:
    @staticmethod
    async def run_async(agent: Agent, prompt: str):
        class Result:
            def __init__(self, output): self.final_output = output
        out = await agent.run(prompt)
        return Result(out)
