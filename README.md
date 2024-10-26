# ClaudeComputerUseBeta-Win64

Beta trial code for the **Claude 3.5 Sonnet Computer Use (Beta) on __Win64__**.

⚠️ **WARNING**: It is HIGHLY RECOMMENDED to run this application in a virtual machine environment for security and isolation purposes. Running this on your local machine directly carries potential security risks.

As noted in the [Anthropic Computer Use (Beta) Documentation](https://docs.anthropic.com/en/docs/build-with-claude/computer-use), it is recommended that the Computer Use be run in Virtual Machines. 

For Docker based Computer Use (Beta), please visit [Anthropic Computer Use (Beta)](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo).

Participation is welcomed. Currently facing many issues with calibration of the awaiting time for the actions to complete and the accuracy of the goal recognition. 

## Installation and Setup

### Recommended: Using a Virtual Machine

1. Set up a virtual machine using software like VMware or VirtualBox.

2. Clone the repository in your virtual machine:
   ```
   git clone https://github.com/MinjaeKIM753/ClaudeComputerUseBeta-Win64.git
   cd ClaudeComputerUseBeta-Win64
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Anthropic API key:
   - Create a `.env` file in the project root directory
   - Add your API key to the file:
     ```
     ANTHROPIC_API_KEY=your_api_key_here
     ```
   - Alternatively, you can set it as an environment variable in your virtual machine for ease of use:
     ```
     export ANTHROPIC_API_KEY=your_api_key_here
     ```

### Alternative: Local Machine (Not Recommended)

If you choose to run on your local machine despite the risks:

1. Follow steps 2-4 from the virtual machine setup.

2. It's strongly advised to use a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

Note: Ensure you have Python 3.7 or higher installed on your system.

## Running the Application

After completing the setup, run the application: