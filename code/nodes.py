import sqlite3
import os

from dotenv import load_dotenv
from typing import TypedDict, Annotated
from pydantic import BaseModel
from operator import add
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

load_dotenv(override=True)

DB_PATH = Path(os.getenv("DB_PATH"))
PROJECT_PATH = Path(__file__).parent.parent


class GraphState(TypedDict):
  """
  Agent's state.

  question: Question provided by the user. Remains immutable.
  current_sql: Current SQL query for the execution node. Updated by the generator node.
  execution_error: Error returned by the execution node (if any). Updated by the executor node.
  execution_result: Result returned by the execution node (if no error). Updated  by the executor node.
  attempt_history: History of attempts. It's a list of dictionaries with keys: 'attempt', 'sql', 'error', and 'critique'. Updated by the evaluator node.
  attempt_count: Number of attempts. Updated by the generator.
  """
  question: str
  current_sql: str
  execution_error: str | None
  execution_result: list | None
  attempt_history: Annotated[list[dict], add]
  attempt_count: int


class SQLQuery(BaseModel):
  """
  Class for getting the structured output from the generator node.
  """
  query: str


llm = ChatOpenAI(model="gpt-4o-mini")

# LLM structure for the Generator
structured_llm = llm.with_structured_output(SQLQuery)
with open(PROJECT_PATH / "prompts/generator_system_prompt.txt", "r") as f:
  generation_system_prompt = f.read()
generation_prompt = ChatPromptTemplate.from_messages([
  ('system', generation_system_prompt),
  ('user', 'Question: {question}\n\nPrevious attempts:\n{formatted_history}')
])
llm_generator = generation_prompt | structured_llm

with open(PROJECT_PATH / "prompts/evaluator_system_prompt.txt", "r") as f:
  evaluation_system_prompt = f.read()
evaluation_prompt = ChatPromptTemplate.from_messages([
  ('system', evaluation_system_prompt),
  ('user',
   'For this question: {question}\nThis query:\n{query}\nProduced this error:\n{error}')
])
llm_evaluator = evaluation_prompt | llm


def format_attempt_history(attempt_history: list[dict]) -> str:
  """
  Transforms a list of previous attempts into a readable block of text to insert into the generator prompt.

  Args:
    attempt_history (list[dict]): list of dicts with keys: 'attempt', 'sql', 'error' / 'critique'

  Returns:
    str: formatted string (one per line) or an empty string if the list is empty.
  """
  if not attempt_history:
    return ""
  formatted_history = "Attempts History:\n"
  for id, attempt in enumerate(attempt_history):
    error = attempt['error'] if attempt['error'] is not None else 'None'
    critique = attempt['critique'] if attempt['critique'] is not None else 'None'

    formatted_history += f"""\n
Attempt : {attempt['attempt']}
SQL Query : {attempt['sql']}
Error : {error}
Critique : {critique}\n\n"""
  return formatted_history


def generator_node(state: GraphState) -> dict:
  """
    Generates a new SQL query by invoking the LLM with structured output using the question and formatted attempts history as a context.

  Args:
    state (GraphState): State of the agent.

  Returns:
    dict: Dictionary with 'current_sql' (from the structured output) and 'attempt_count' increased by 1.
  """
  question = state['question']
  attempt_history = state['attempt_history']
  formatted_attempt_history = format_attempt_history(attempt_history)

  res = llm_generator.invoke({
    'question': question,
    'formatted_history': formatted_attempt_history
  })

  return {
    'current_sql': res.query,  # string
    'attempt_count': state['attempt_count'] + 1,
  }


def sql_executor_node(state: GraphState) -> dict:
  """
  Executes the generator's SQL query response againts the actual Database.

  Args:
    state (GraphState): Agent's state.

  Returns:
    dict: Dictionary with 'execution_error' and 'execution_result'. Mutually exclusive (one must be None) based on the query result.
  """
  con = sqlite3.connect(DB_PATH)
  cur = con.cursor()
  try:
    cur.execute(state['current_sql'])
    result = cur.fetchall()
    error = None
    con.close()
  except sqlite3.Error as e:
    result = None
    error = str(e)
    con.close()
  return {
    'execution_error': error,
    'execution_result': result,
  }


def evaluator_node(state: GraphState) -> list[dict]:
  question = state['question']
  attempt = state['attempt_count']
  sql = state['current_sql']
  error = state['execution_error']
  res = llm_evaluator.invoke({
    'question': question,
    'query': sql,
    'error': error,
  })
  return {'attempt_history': [{
    'attempt': attempt,
    'sql': sql,
    'error': error,
    'critique': res.content
  }]}
