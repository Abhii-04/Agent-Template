import asyncio
from email import message
from sre_parse import SUCCESS
from typing import Annotated
from langgraph import graph
from openai import conversations
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field
from tools import playwright_tools, other_tools
import uuid
from datetime import datetime
import os


load_dotenv(override=True)


llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
)


class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    success_criteria: str
    feedback_on_work: Optional[str]
    success_criteria_met: bool
    user_input_needed: bool


class EvaluatorOutput(BaseModel):
    feedback: str = Field(description="Feedback on the assistant`s response")
    success_criteria_met: bool = Field(
        description="whether the success criteria have been met"
    )
    user_input_needed: bool = Field(
        description="true if more input is needed from the user, or clarification, or the assistant is stuck"
    )


class Sidekick:
    def __init__(self):
        self.worker_llm_with_tools = None
        self.evaluator_llm_with_output = None
        self.tools = None
        self.graph = None
        self.sidekick_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.browser = None
        self.playwright = None

    async def setup(self):
        self.tools, self.browser, self.playwright = await playwright_tools()
        self.tools += await other_tools()
        worker_llm = llm
        self.worker_llm_with_tools = worker_llm.bind_tools(self.tools)
        evaluator_llm = llm
        self.evaluator_llm_with_output = evaluator_llm
        await self.build_graph()

    def worker(self, state: State) -> Dict[str, Any]:
        system_message = f"""You are a helpful assistant that can use tools to complete tasks.
    You keep working on a task until either you have a question or clarification for the user, or the success criteria is met.
    You have many tools to help you, including tools to browse the internet, navigating and retrieving web pages.
    You have a tool to run python code, but note that you would need to include a print() statement if you wanted to receive output.
    The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    This is the success criteria:
    {state["success_criteria"]}
    You should reply either with a question for the user about this assignment, or with your final response.
    If you have a question for the user, you need to reply by clearly stating your question. An example might be:

    Question: please clarify whether you want a summary or a detailed answer

    If you've finished, reply with the final answer, and don't ask a question; simply reply with the answer.
    """

        if state.get("feedback_on_work"):
            system_message += f"""
    Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
    Here is the feedback on why this was rejected:
    {state["feedback_on_work"]}
    With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""

        found_system_message = False
        messages = state["messages"]

        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True

        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        response = self.worker_llm_with_tools.invoke(messages)

        return {
            "messages": [response],
        }

    def worker_router(self, state: State) -> str:
        last_message = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        else:
            return "evaluator"

    def format_conversation(self, messages: List[Any]) -> str:
        conversation = "Conversation History: \n\n"

        for message in messages:
            if isinstance(message, HumanMessage):
                conversation += f"User: {message.content}\n"

            elif isinstance(message, AIMessage):
                text = message.content or "[Tools use]"
                conversation += f"Assistant: {text}\n"

        return conversation

    def evaluator(self, state: State) -> State:
        last_response = state["messages"][-1].content

        system_message = """You are an evaluator that determines if a task has been completed successfully by an Assistant.

Return your response in this exact format:

FEEDBACK: <your feedback>

SUCCESS: true or false

USER_INPUT_NEEDED: true or false
"""

        user_message = f"""The conversation is:

{self.format_conversation(state["messages"])}

Success criteria:
{state["success_criteria"]}

Assistant final response:
{last_response}
"""

        evaluator_messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        eval_result = self.evaluator_llm_with_output.invoke(
            evaluator_messages
        )

        content = eval_result.content

        lower_content = content.lower()

        success_criteria_met = "success: true" in lower_content

        user_input_needed = (
            "user_input_needed: true" in lower_content
        )

        new_state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"evaluator feedback on this answer: {content}",
                }
            ],
            "feedback_on_work": content,
            "success_criteria_met": success_criteria_met,
            "user_input_needed": user_input_needed,
        }

        return new_state

    def route_based_on_evaluation(self, state: State) -> str:
        if state["success_criteria_met"] or state["user_input_needed"]:
            return "END"
        else:
            return "worker"

    async def build_graph(self):
        graph_builder = StateGraph(State)

        graph_builder.add_node("worker", self.worker)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_node("evaluator", self.evaluator)

        graph_builder.add_conditional_edges(
            "worker",
            self.worker_router,
            {"tools": "tools", "evaluator": "evaluator"},
        )

        graph_builder.add_edge("tools", "worker")

        graph_builder.add_conditional_edges(
            "evaluator",
            self.route_based_on_evaluation,
            {"worker": "worker", "END": END},
        )

        graph_builder.add_edge(START, "worker")

        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, success_criteria, history):
        config = {"configurable": {"thread_id": self.sidekick_id}}

        state = {
            "messages": [HumanMessage(content=message)],
            "success_criteria": success_criteria
            or "The answer should be clear and accurate",
            "feedback_on_work": None,
            "success_criteria_met": False,
            "user_input_needed": False,
        }

        result = await self.graph.ainvoke(state, config=config)

        user = {"role": "user", "content": message}

        reply = {
            "role": "assistant",
            "content": result["messages"][-2].content,
        }

        feedback = {
            "role": "assistant",
            "content": result["messages"][-1].content,
        }

        return history + [user, reply, feedback]

    def cleanup(self):
        if self.browser:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.browser.close())

                if self.playwright:
                    loop.create_task(self.playwright.stop())

            except RuntimeError:
                asyncio.run(self.browser.close())

                if self.playwright:
                    asyncio.run(self.playwright.stop())