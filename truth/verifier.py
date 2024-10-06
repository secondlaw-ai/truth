import os
import requests
import time
from typing import List, Dict
from loguru import logger
from dotenv import load_dotenv
from mistralai import Mistral
import json
from .actions import AVAILABLE_ACTIONS

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")


class VerifierAgent:
    def __init__(
        self,
        mistral_api_key=MISTRAL_API_KEY,
        brave_api_key=BRAVE_API_KEY,
        model="mistral-small-latest",
    ):
        self.mistral_client = Mistral(api_key=mistral_api_key)
        self.brave_api_key = brave_api_key
        self.model = model
        self.available_actions = AVAILABLE_ACTIONS
        self.action_plan = []
        self.context = {}
        # Initialize total time and cost tracking
        self.total_time = 0.0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost = 0.0
        logger.success(f"Verifier Agent initialized with model: {model}")

    def log_event(
        self, event, input_data, output_data, verbose=True, max_output_length=200
    ):
        def truncate(data):
            if isinstance(data, str) and len(data) > max_output_length:
                return data[:max_output_length] + "... [truncated]"
            elif isinstance(data, dict):
                return {k: truncate(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [truncate(item) for item in data]
            else:
                return data

        if not verbose:
            output_preview = truncate(output_data)
        else:
            output_preview = output_data

        logger.info(
            f"Event: {event}\nInput: {input_data}\nOutput: {output_preview}\n---"
        )

    def formulate_question(self, statement: str):
        prompt = f"Convert the following statement into a clear and concise yes/no question:\n\n{statement}"
        start_time = time.time()
        response = self.mistral_client.chat.complete(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        elapsed_time = time.time() - start_time
        self.total_time += elapsed_time

        # Extract token usage and calculate cost
        self.update_usage_and_cost(response)

        question = response.choices[0].message.content.strip()
        self.log_event("Formulate Question", statement, question)
        return question

    def perform_web_search(self, question: str, num_results: int = 3):
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": self.brave_api_key}
        params = {"q": question}
        start_time = time.time()
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            results = response.json()
            links = [
                result["url"] for result in results.get("web", {}).get("results", [])
            ][:num_results]
            self.log_event("Web Search", question, links)
            return links
        except requests.exceptions.RequestException as e:
            logger.error(f"Web search failed: {str(e)}")
            return []
        finally:
            elapsed_time = time.time() - start_time
            self.total_time += elapsed_time

    def plan_actions(self, query: str, links: List[str]) -> List[Dict]:
        # Prepare action descriptions
        action_descriptions = "\n".join(
            [
                f"- {name}: {info['description']}"
                for name, info in self.available_actions.items()
            ]
        )
        logger.debug(f"Action descriptions: {action_descriptions}")

        prompt = f"""As an AI agent, plan a sequence of actions to verify the following query based on the provided links.
You have the following actions available:
{action_descriptions}

Each action should be applicable to a link, and you can determine the appropriate action based on the link type.

Query:
{query}

Links:
{chr(10).join(links)}

Return your plan as a JSON object with an "action_plan" key containing a list of actions.
Each action should have "action_name", "params", and "reason" fields.

Example:
{{
    "action_plan": [
        {{"action_name": "read_wiki_entry", "params": {{"url": "link1"}}, "reason": "Reason for choosing this action for link1"}},
        {{"action_name": "read_webpage_content", "params": {{"url": "link2"}}, "reason": "Reason for choosing this action for link2"}},
        ...
    ]
}}
"""
        start_time = time.time()
        response = self.mistral_client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        elapsed_time = time.time() - start_time
        self.total_time += elapsed_time

        # Extract token usage and calculate cost
        self.update_usage_and_cost(response)

        try:
            plan_data = json.loads(response.choices[0].message.content)
            self.action_plan = plan_data.get("action_plan", [])
            self.log_event(
                "Plan Actions", {"question": query, "links": links}, self.action_plan
            )
            return self.action_plan
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse action plan: {str(e)}")
            self.log_event(
                "Plan Actions",
                {"question": query, "links": links},
                "Failed to parse action plan",
            )
            return []

    def take_action(self, action_meta):
        action_name = action_meta["action_name"]
        params = action_meta["params"]
        logger.info(f"Taking action: {action_name} with params: {params}")
        if action_name not in self.available_actions:
            logger.warning(f"Action {action_name} not available")
            return None

        action_function = self.available_actions[action_name]["function"]
        start_time = time.time()
        try:
            observation = action_function(**params)
            elapsed_time = time.time() - start_time
            self.total_time += elapsed_time

            self.context[action_name] = self.context.get(action_name, []) + [
                observation
            ]
            self.log_event(f"Action Taken: {action_name}", params, observation, False)
            return observation
        except Exception as e:
            logger.warning(f"Error during action {action_name}: {str(e)}")
            return None

    def update_usage_and_cost(self, response):
        # Extract token usage and calculate cost
        usage = response.usage
        if usage:
            self.total_prompt_tokens += usage.prompt_tokens
            self.total_completion_tokens += usage.completion_tokens
            cost = self.calculate_cost(response)
            self.total_cost += cost
        else:
            logger.warning("No usage data available in the response.")

    def calculate_cost(self, response):
        usage = response.usage
        if not usage:
            return 0.0

        # Pricing per million tokens
        pricing = {
            "mistral-large-2407": {"input": 2.0, "output": 6.0},
            "mistral-small-2409": {"input": 0.2, "output": 0.6},
            "mistral-small-latest": {"input": 0.2, "output": 0.6},
            "mistral-large-latest": {"input": 2.0, "output": 6.0},
        }

        model_pricing = pricing.get(self.model, {"input": 0.0, "output": 0.0})
        input_cost_per_token = model_pricing["input"] / 1_000_000
        output_cost_per_token = model_pricing["output"] / 1_000_000

        cost = (
            usage.prompt_tokens * input_cost_per_token
            + usage.completion_tokens * output_cost_per_token
        )
        return cost

    def verify_statement(self, statement: str):
        total_start_time = time.time()
        # Formulate the question from the statement
        question = self.formulate_question(statement)

        # Perform web search based on the question
        links = self.perform_web_search(question)
        # Proceed even if no links are found
        if not links:
            logger.warning("No search results found.")
            links = []

        # Plan actions using the search results
        action_plan = self.plan_actions(question, links)
        # Proceed even if no action plan is found
        if not action_plan:
            logger.warning("No action plan determined for verification.")
            action_plan = []

        # Execute the planned actions and collect observations
        for action in action_plan:
            self.take_action(action)

        # Prepare the context information for the prompt
        context_info = json.dumps(self.context, indent=2)

        # Updated prompt with more descriptive information
        prompt = f"""
As an AI verifier, you are given a statement to verify. The statement has been reformulated into a question to help gather relevant information. Use the context gathered based on this question to verify the original statement.

Statement:
{statement}

Reformulated Question:
{question}

Context (information gathered from actions based on the question):
{context_info}

Note: If the context is insufficient or empty, consider that there may not be enough information to verify the statement. In such cases, you should return "Unknown" as the result.

Based on the context, provide a verification result as a JSON object with the following fields:

{{
    "statement": "{statement}",
    "result": "Yes/No/Unknown/Too Early",
    "confidence": "Low/Medium/High",
    "explanation": "Provide a concise explanation for your conclusion",
    "sources": ["List of URLs used to gather the context (can be empty if none)"]
}}
"""
        start_time = time.time()
        response = self.mistral_client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        elapsed_time = time.time() - start_time
        self.total_time += elapsed_time

        # Extract token usage and calculate cost
        self.update_usage_and_cost(response)

        verification_result = response.choices[0].message.content.strip()

        try:
            verification_data = json.loads(verification_result)
            # Ensure 'sources' is a list of strings
            if not isinstance(verification_data.get("sources", []), list):
                verification_data["sources"] = links
            self.log_event(
                "Verify Statement",
                {
                    "statement": statement,
                    "context": "[context data omitted for brevity]",
                },
                verification_data,
                verbose=False,
            )
            # Clear the context after verification

            total_elapsed_time = time.time() - total_start_time

            # Include time and cost information in the result
            verification_data["total_time"] = round(self.total_time, 2)  # in seconds
            verification_data["total_prompt_tokens"] = self.total_prompt_tokens
            verification_data["total_completion_tokens"] = self.total_completion_tokens
            verification_data["total_cost"] = round(self.total_cost, 4)  # in dollars

            return verification_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification result: {str(e)}")
            self.log_event(
                "Verify Statement",
                {
                    "statement": statement,
                    "context": "[context data omitted for brevity]",
                },
                "Failed to parse verification result",
                verbose=False,
            )
            # Even if parsing fails, return unknown result
            return {
                "statement": statement,
                "result": "Unknown",
                "confidence": "Low",
                "explanation": "Failed to parse verification result.",
                "sources": links,
                "usage": {
                    "total_time": round(self.total_time, 2),
                    "total_prompt_tokens": self.total_prompt_tokens,
                    "total_completion_tokens": self.total_completion_tokens,
                    "total_cost": round(self.total_cost, 4),
                },
            }

    def verify_uma_vote(self, contract_description: str, message: Dict[str, str]):
        # if there are links provided, use them to verify the statement

        if message["sources"]:
            self.action_plan = self.plan_actions(
                query="Fetch more context from the sources", links=message["sources"]
            )
            for action in self.action_plan:
                self.take_action(action)  # this will add the sources to the context

        # Prepare the context information for the prompt
        context_info = json.dumps(self.context, indent=2)
        logger.debug(f"Context: {context_info}")
        # Prepare the prompt for the language model
        prompt = f"""
You are an AI agent tasked with verifying whether the P value provided in a UMA vote is correct based on the contract description and the evidence provided.

Contract Description:
{contract_description}

Vote Message:
user: {message.get('user', 'Unknown')}
timestamp: {message.get('timestamp', 'Unknown')}
P value submitted: {message.get('P', '')}
evidence: {message.get('Evidence', '')}
rationale: {message.get('Rationale', '')}

Context (information gathered from the sources):
{context_info}

Instructions:
- Analyze the contract description and understand the criteria for each P value (P1, P2, P3, P4).
- Evaluate the evidence, context from sources, and rationale provided in the vote message.
- Determine if the submitted P value is correct based on the contract description, evidence, and rationale.
- If the P value is correct, state that it is correct.
- If there is insufficient information to verify, state that the verification is not possible.
- Provide confidence level based on the analysis.
Provide your response in the following JSON format:

{{
    "voted_P": "{message.get('P', '')}",
    "is_correct": true/false,
    "confidence": "Low"/"Medium"/"High",
    "explanation": "Your explanation here."
}}
"""
        # Call the language model
        start_time = time.time()
        response = self.mistral_client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        elapsed_time = time.time() - start_time
        self.total_time += elapsed_time

        # Extract token usage and calculate cost
        self.update_usage_and_cost(response)

        # Parse the response
        try:
            verification_result = json.loads(response.choices[0].message.content)
            self.log_event(
                "Verify UMA Vote",
                {
                    "message": message,
                    "contract_description": "[omitted for brevity]",
                },
                verification_result,
                verbose=False,
            )
            # self.context.clear()
            return verification_result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification result: {str(e)}")
            self.log_event(
                "Verify UMA Vote",
                {
                    "message": message,
                    "contract_description": "[omitted for brevity]",
                },
                "Failed to parse verification result",
                verbose=False,
            )
            # Clear the context after verification
            self.context.clear()
            # Return a default result indicating the failure
            return {
                "voted_P": message.get("P", ""),
                "is_correct": False,
                "confidence": "Low",
                "explanation": "Failed to parse verification result.",
            }


if __name__ == "__main__":
    verifier_agent = VerifierAgent()
    statement = "The Earth is flat."
    result = verifier_agent.verify_statement(statement)
    print("Final Verification Result:")
    print(json.dumps(result, indent=2))
    print(f"Total Time: {result['usage'].get('total_time', 0)} seconds")
    print(f"Total Cost: ${result['usage'].get('total_cost', 0)}")
