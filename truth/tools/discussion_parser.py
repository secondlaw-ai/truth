from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
from mistralai import Mistral
from loguru import logger
import dotenv

dotenv.load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")


class DiscussionParser:
    def __init__(
        self,
        api_key: str = MISTRAL_API_KEY,
        model: str = "mistral-small-latest",
    ):
        self.api_key = api_key
        self.model = model
        self.content = None
        self.parsed = None
        self.metrics = None
        self.filepath = None
        logger.info(f"DiscussionParser initialized with model: {model}")

    def parse_from_file(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File {filepath} does not exist")
        with open(filepath, "r", encoding="utf-8") as file:
            self.content = file.read()
        self.filepath = filepath
        return self.parse()

    def parse_from_str(self, content):
        self.content = content
        return self.parse()

    def parse(self):
        if not self.content:
            raise ValueError(
                "No content to parse. Use parse_from_file or parse_from_str first."
            )

        client = Mistral(api_key=self.api_key)
        prompt = f"""
        You are an AI assistant tasked with analyzing a Discord discussion about a prediction market smart contract. 
        A prediction market smart contract allows individuals to make predictions and place bets on the likelihood of different outcomes for a future event. These types of contracts can be used for any kind of events such as: Sports games, Cryptocurrency price predictions, Product launches, Political policy decisions.
        This smart contract enables the creation of prediction markets based on any off-chain event with three possible outcomes, two of which are chosen by the market creator and the third reflecting the remaining outcomes (i.e. tie or a draw in a sporting event).
        
        The discussion contains a description of the contract and several messages from users. Your job is to extract and structure the following information:

        1. Market Description:
           - Extract the full description of the market, which starts after "Description:" and continues until the next message.

        2. Messages:
           For each message in the discussion, extract:
           - user: The name of the user who posted the message.
           - timestamp: The date and time when the message was posted.
           - P value: If present, extract the P value (P1, P2, P3, or P4) and its associated result (Yes, No, Unknown, Too Early).
           - evidence: Any factual information or links provided to support the user's position.
           - sources: Any URLs or links provided as evidence.
           - rationale: Any reasoning or explanation given by the user for their position.

        3. Structure the extracted information as follows:
           {{
             "description": "Full market description here",
             "messages": [
               {{
                 "user": "Username",
                 "timestamp": "YYYY-MM-DD, HH:MM AM/PM",
                 "P": "Px",
                 "evidence": "Any evidence provided",
                 "sources": ["URL1", "URL2", ...],
                 "rationale": "Any rationale given"
               }},
               // More messages...
             ]
           }}

        Important notes:
        - If any field is not present in a message, use an empty string for that field.
        - The P value should be in the format "Px" or "Px - Result", e.g., "P2", "P2 - Yes", "P4", or "P4 - Too Early". Accept both formats, but in the final JSON output, use only the "Px" format.
        - Exclude any system messages or irrelevant text (like "Discord user avatar").
        - If a message doesn't contain a clear P value, Evidence, or Rationale, leave those fields empty.
        - The evidence field should contain direct quotes or links that support the user's position.
        - The sources field should contain a list of all URLs mentioned in the message.
        - The rationale field should contain any explanations or reasoning provided by the user.

        Here's the Discord discussion to analyze:

        {self.content}

        Please provide the structured JSON output based on this discussion.
        """

        chat_response = client.chat.complete(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={"type": "json_object"},
        )

        self.parsed = json.loads(chat_response.choices[0].message.content)
        return self.parsed

    def calculate_metrics(self):
        messages = self.parsed["messages"]
        total_messages = len(messages)

        p_values = Counter({"P1": 0, "P2": 0, "P3": 0, "P4": 0})
        evidence_count = 0
        rationale_count = 0
        users = set()
        timestamps = []
        evidence_with_links_count = 0
        total_links = 0
        resolution_status = "Unresolved"

        for message in messages:
            if message["user"] == "bruna.uma":
                if "resolved" in message.get("content", "").lower():
                    resolution_status = "Resolved"
                continue

            users.add(message["user"])
            if message["P"]:
                p_values[message["P"]] += 1
            if message["evidence"]:
                evidence_count += 1
                if message["sources"]:
                    evidence_with_links_count += 1
                    total_links += len(message["sources"])
            if message["rationale"]:
                rationale_count += 1
            if message["timestamp"]:
                timestamps.append(
                    datetime.strptime(message["timestamp"], "%Y-%m-%d, %I:%M %p")
                )

        time_span = max(timestamps) - min(timestamps) if timestamps else None
        self.metrics = {
            "total_messages": total_messages,
            "unique_users": len(users),
            "p_value_distribution": dict(p_values),
            "evidence_count": evidence_count,
            "evidence_percentage": (
                (evidence_count / total_messages) * 100 if total_messages > 0 else 0
            ),
            "evidence_with_links_count": evidence_with_links_count,
            "evidence_with_links_percentage": (
                (evidence_with_links_count / evidence_count) * 100
                if evidence_count > 0
                else 0
            ),
            "total_links": total_links,
            "rationale_count": rationale_count,
            "rationale_percentage": (
                (rationale_count / total_messages) * 100 if total_messages > 0 else 0
            ),
            "time_span": str(time_span) if time_span else "N/A",
            "most_common_p_value": p_values.most_common(1)[0] if p_values else None,
            "resolution_status": resolution_status,
        }
        return self.metrics

    def write(
        self,
        output_dir=None,
        parsed_filename="parsed_discussions.json",
        metrics_filename="metrics.json",
    ):
        if not self.parsed or not self.metrics:
            raise ValueError("Analysis not performed. Run parse() first.")

        # Determine the output directory
        if self.filepath:
            # If content was read from a file, use its directory
            output_dir = Path(self.filepath).parent
        elif output_dir is not None:
            output_dir = Path(output_dir)
        else:
            output_dir = Path.cwd()

        parsed_filepath = output_dir / parsed_filename
        metrics_filepath = output_dir / metrics_filename

        # Write discussion to a separate file
        with open(parsed_filepath, "w", encoding="utf-8") as f:
            json.dump(self.parsed, f, indent=4, ensure_ascii=False)

        # Write metrics to a separate file
        with open(metrics_filepath, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=4, ensure_ascii=False)

        logger.info(f"Parsed discussion written to: {parsed_filepath}")
        logger.info(f"Metrics written to: {metrics_filepath}")

    def print_metrics(self):
        if not self.metrics:
            print("Metrics not calculated. Run analyze() first.")
            return

        print("Response Metrics:")
        print(f"Total Messages: {self.metrics['total_messages']}")
        print(f"Unique Users: {self.metrics['unique_users']}")
        print(f"P-Value Distribution: {self.metrics['p_value_distribution']}")
        print(f"Evidence Count: {self.metrics['evidence_count']}")
        print(f"Evidence Percentage: {self.metrics['evidence_percentage']:.2f}%")
        print(f"Evidence with Links Count: {self.metrics['evidence_with_links_count']}")
        print(
            f"Evidence with Links Percentage: {self.metrics['evidence_with_links_percentage']:.2f}%"
        )
        print(f"Total Links: {self.metrics['total_links']}")
        print(f"Rationale Count: {self.metrics['rationale_count']}")
        print(f"Rationale Percentage: {self.metrics['rationale_percentage']:.2f}%")
        print(f"Time Span of Discussion: {self.metrics['time_span']}")
        print(f"Most Common P-Value: {self.metrics['most_common_p_value']}")
        print(f"Resolution Status: {self.metrics['resolution_status']}")


# Example usage
if __name__ == "__main__":
    parser = DiscussionParser()

    # Example using parse_from_file
    # parser.parse_from_file("/path/to/discussions.txt")

    # Example using parse_from_str
    content = """
    Description: Will the US economy enter a recession in 2023?

    User1 (2023-03-15, 10:00 AM): I think it's likely. P2
    User2 (2023-03-15, 10:05 AM): I disagree, the economy seems stable. P1
    """
    parser.parse_from_str(content)

    parser.print_metrics()
    parser.write()
