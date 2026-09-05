from nodes import GraphState


def format_response(state: GraphState) -> str:
  """
  Formats the response taking information from the final state.
  """
  if state['execution_error'] is not None:
    return "Sorry, I couldn't get an aswer for that."
  if len(state["execution_result"]) == 1:
    response = state["execution_result"][0]
    if len(response) == 1:
      response = response[0]
  else:
    response = "\n".join([
      str(x[0])
      if len(x) == 1
      else str(x)
      for x in state["execution_result"][:10]
    ])
    if (remain := len(state["execution_result"]) - 10) > 0:
      response += f"\n... {remain} more rows."
  label = "Response:" if isinstance(
    response, str) and "\n" not in response else "Response:\n"
  return (
    f"{label} {str(response)}\n"
    f"\nUsing the query:\n{state['current_sql']}\n"
    f"\nAfter {state['attempt_count']} attempt(s).\n"
  )


def format_attempts(attempt_history: dict) -> str:
  """
  Formats the dictionary of an attempt into a string. Stores the full content in a separate file and returns a version with 'critique' truncated to 150 chars.
  """
  critique = attempt_history["critique"]

  # For the file
  full_formatted = (
    "=" * 40 + "\n"
    f"----- Attempt {attempt_history['attempt']} -----\n"
    f"Query:\n{attempt_history['sql']}\n"
    f"Error: {attempt_history['error']}\n"
    f"Critique: {critique}\n"
    + "=" * 40
  )

  # Saves the full version
  with open("attempt_history.txt", "w", encoding="utf-8") as file:
    file.write(full_formatted)

  # Truncated version
  formatted = (
    "=" * 40 + "\n"
    f"----- Attempt {attempt_history['attempt']} -----\n"
    f"Query:\n{attempt_history['sql']}\n"
    f"Error: {attempt_history['error']}\n"
    f"Critique: {critique[:150]}\n"
    + "=" * 40
  )

  return formatted
