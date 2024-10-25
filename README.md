# ClaudeComputerUseBeta-Win64

Beta trial code for the **Claude 3.5 Sonnet Computer Use (Beta) on __Win64__**.

As noted in the [Anthropic Computer Use (Beta) Documentation](https://docs.anthropic.com/en/docs/build-with-claude/computer-use), it is recommended that the Computer Use to be ran in Virtual Machines. 

For Docker based Computer Use (Beta), please visit [Anthropic Computer Use (Beta)](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo).

Participation is welcomed. Currently facing many issues with calibration of the awaiting time for the actions to complete and the accuracy of the goal recognition. 

## Installation and Setup

1. Clone the repository:
   ```
   git clone https://github.com/MinjaeKIM753/ClaudeComputerUseBeta-Win64.git
   cd ClaudeComputerUseBeta-Win64
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

5. Set up your Anthropic API key:
   - Create a `.env` file in the project root directory
   - Add your API key to the file:
     ```
     ANTHROPIC_API_KEY=your_api_key_here
     ```

6. Run the application:
   ```
   python main.py
   ```

Note: Make sure you have Python 3.7 or higher installed on your system.

## Usage

### Step 1. Initialize with API Key

Insert your Claude API Key in the main window, and press Initialize.

![Before_initialize](./img/CCMP1.png)
![After_initialize](./img/CCMP1-1.png)

### Step 2. Submit Your Prompt

Write your prompt in the input box and press Submit.

![Processing](./img/CCMP2.png)

## Current Status

- Errors in correctly locating the cursor. This may be due to image downscaling (due to token length limit)
- Errors in identifying whether the goal has been achieved.
- Currently taking two screenshots at the beginning of the task. 
- Need calibration of the awaiting time for the actions to complete. 

## Known Errors

```
Error: Client initialization failed: Failed to validate API key: 'Beta' object has no attribute 'messages'
```
Solution: Update the anthropic library by running:
```
pip install --upgrade anthropic
```