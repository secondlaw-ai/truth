# Truth

Truth is an open-source library designed to solve oracle problems using LLMs, Brave Search, and UMA (Universal Market Access). It employs LLM agents to verify the authenticity of uploaded data.

## About UMA Protocol

UMA (Universal Market Access) is a decentralized financial contracts platform built to enable Universal Market Access. It allows anyone to create synthetic assets, financial contracts, and prediction markets on Ethereum. UMA's design focuses on economic guarantees as opposed to cryptographic ones, making it highly flexible and scalable.

## Importance of Data Verification

In the world of decentralized finance and blockchain technology, the accuracy and reliability of data are paramount. Verified data is crucial for:

1. **Smart Contract Execution**: Many DeFi applications rely on external data to trigger contract executions. Inaccurate data can lead to incorrect contract outcomes.

2. **Market Integrity**: In prediction markets and synthetic assets, the underlying data determines the value and settlement of contracts. Verified data ensures fair and accurate market operations.

3. **Risk Management**: Accurate data is essential for proper risk assessment and management in decentralized systems.

4. **Trust and Adoption**: Reliable data verification mechanisms increase user trust and promote wider adoption of decentralized applications.

5. **Preventing Manipulation**: Robust verification helps prevent malicious actors from manipulating markets or contracts through false data inputs.

The Truth library aims to address these concerns by providing a powerful, LLM-based verification system that can be integrated into UMA and other blockchain-based applications.

## Setup

### Setting up the environment

1. Clone the repository:
   ```
   git clone https://github.com/secondlaw-ai/truth.git
   cd truth
   ```

2. Run the setup script:
   ```
   chmod +x setup_environment.sh
   ./setup_environment.sh
   ```

3. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

### Configuration

Create a `.env` file in the project root with the following content:

```
MISTRAL_API_KEY=your_mistral_api_key_here
BRAVE_API_KEY=your_brave_api_key_here
```

Replace the placeholder values with your actual API keys.

## Usage

Here's a basic example of how to use Truth:

```python
from truth import VerifierAgent

verifier = VerifierAgent()
output = verifier.verify_statement("The Earth is flat.")
print(
    f"Result: {output['result']}\nConfidence: {output['confidence']}\nSources: {output['sources']}\nExplanation: {output['explanation']}\n\n"
)
```
```
>>>
Result: No
Confidence: High
Sources: ['https://en.wikipedia.org/wiki/Flat_Earth', 'https://askanearthspacescientist.asu.edu/top-question/flat-earth', 'https://answersingenesis.org/astronomy/earth/is-the-earth-flat/']
Explanation: Both the Wikipedia entry and the article from Answers in Genesis provide extensive evidence that the Earth is spherical. This includes historical records dating back to the ancient Greeks, empirical observations such as the curvature of the Earth visible in ship observations and lunar eclipses, as well as modern scientific evidence such as satellite imagery and astronomical measurements.

```

## Running Tests

To run the tests, make sure you're in the project root directory and the virtual environment is activated, then run:

```
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

