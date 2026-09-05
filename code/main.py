import readline  # improves interaction in the terminal
from langgraph.graph import StateGraph, END
from pathlib import Path
from nodes import (
  generator_node,
  sql_executor_node,
  evaluator_node,
  GraphState,
)
from utils import format_response, format_attempts

PROJECT_PATH = Path(__file__).parent.parent

# Nodes names
GENERATOR = "generator"
SQL_EXECUTOR = "sql_executor"
EVALUATOR = "evaluator"
MAX_ITERATIONS = 5

# Conditional edges


def route_after_execution(state: GraphState) -> str:
  """
  Reads whether the SQL output is successful or not. If it is, the next step is the END node. Otherwise, the output is directed to the evaluator node.
  """
  if state['execution_error'] is not None:
    return EVALUATOR
  return END


def route_after_evaluation(state: GraphState) -> str:
  """
  Reads whether the max number of iterations has been reach. If it's been reaches, the next step is the END node. Otherwhise, the output is directed to the generator node.
  """
  if state['attempt_count'] >= MAX_ITERATIONS:
    return END
  return GENERATOR


# Create the graph
flow = StateGraph(GraphState)
flow.add_node(GENERATOR, generator_node)
flow.add_node(SQL_EXECUTOR, sql_executor_node)
flow.add_node(EVALUATOR, evaluator_node)
flow.set_entry_point(GENERATOR)
flow.add_edge(GENERATOR, SQL_EXECUTOR)
flow.add_conditional_edges(
  SQL_EXECUTOR,
  route_after_execution,
  {END: END, EVALUATOR: EVALUATOR}
)
flow.add_conditional_edges(
  EVALUATOR,
  route_after_evaluation,
  {END: END, GENERATOR: GENERATOR}
)

graph = flow.compile()
# graph.get_graph().draw_mermaid_png(output_file_path=PROJECT_PATH/"assets/graph.png")

if __name__ == "__main__":
  # Simple loop for question-answering.
  # Observation: This agent has no **conversation** memory.
  while True:
    nl_query = input(">> ")
    if nl_query.lower().strip() in ["q", "quit", "exit"]:
      break
    initial_state = GraphState(
      question=nl_query,
      current_sql='',
      execution_error=None,
      execution_result=None,
      attempt_history=[],
      attempt_count=0
    )
    res = graph.invoke(initial_state)
    print(format_response(res))
    for attempt in res['attempt_history']:
      print(format_attempts(attempt))
